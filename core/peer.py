import socket
import threading
import time
import random

from core.protocol import criar_pacote, ler_pacote, bytes_para_texto, texto_para_bytes
from core.storage import PeerStorage
from core.logger import Logger

class Peer:
    """
    Nó P2P Simétrico:
    - Servidor: atende conexões e solicitações de chunks que já possui.
    - Cliente: conecta aos vizinhos e solicita os chunks faltantes.
    """
    def __init__(self, host: str, porta: int, vizinhos: list[tuple[str, int]], storage: PeerStorage, nome: str = None, pasta_reconstrucao: str = "reconstructed"):
        self.host = host
        self.porta = porta
        self.nome = nome if nome else f"Peer-{porta}"
        self.vizinhos = vizinhos
        self.storage = storage
        self.pasta_reconstrucao = pasta_reconstrucao
        self.log = Logger(self.nome)

        self.rodando = False
        self.socket_servidor = None

        # Conexões ativas: "ip:porta" -> socket
        self.conexoes = {}
        self.trava_conexoes = threading.Lock()

        # Rastreio de chunks dos vizinhos: "ip:porta" -> set de indices
        self.chunks_vizinhos = {}
        self.trava_chunks = threading.Lock()

        # Evento que sinaliza que o servidor está efetivamente ouvindo
        self.servidor_pronto = threading.Event()
        # Evento que sinaliza que o arquivo foi montado e validado em disco
        self.arquivo_montado = threading.Event()
        self.trava_montagem = threading.Lock()
        self.pedidos_em_andamento = set()
        self.trava_pedidos = threading.Lock()

    def iniciar(self):
        self.rodando = True
        self.log.info(f"Iniciando em {self.host}:{self.porta}")
        self.log.info(f"Arquivo: {self.storage.metadata.filename} ({self.storage.metadata.total_chunks} chunks de {self.storage.metadata.chunk_size} bytes)")
        self.log.progresso(self.storage.bitfield.count(), self.storage.metadata.total_chunks)

        # 1. Thread do Servidor
        t_servidor = threading.Thread(target=self._servidor, daemon=True)
        t_servidor.start()
        self.servidor_pronto.wait(timeout=3.0)

        # 2. Thread de conexão com vizinhos
        threading.Thread(target=self._conectar_vizinhos, daemon=True).start()

        # 3. Thread de download
        threading.Thread(target=self._gerenciador_downloads, daemon=True).start()

    def parar(self):
        self.rodando = False
        if self.socket_servidor:
            try:
                self.socket_servidor.close()
            except Exception:
                pass
        with self.trava_conexoes:
            for s in self.conexoes.values():
                try:
                    s.close()
                except Exception:
                    pass
        self.log.info("Peer encerrado.")

    # =========================================================================
    # SERVIDOR
    # =========================================================================

    def _servidor(self):
        tentativas = 0
        while self.rodando and tentativas < 5:
            try:
                self.socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.socket_servidor.bind((self.host, self.porta))
                self.socket_servidor.listen(10)
                self.log.info(f"Aguardando conexões na porta {self.porta}...")
                self.servidor_pronto.set()
                break
            except Exception as e:
                tentativas += 1
                if tentativas >= 5:
                    self.log.erro(f"Erro fatal no servidor ao vincular na porta {self.porta}: {e}")
                    return
                time.sleep(0.5)

        while self.rodando:
            try:
                sock_cliente, endereco = self.socket_servidor.accept()
                threading.Thread(target=self._atender_cliente, args=(sock_cliente, endereco), daemon=True).start()
            except OSError:
                break

    def _atender_cliente(self, conexao: socket.socket, endereco: tuple[str, int]):
        chave_vizinho = f"{endereco[0]}:{endereco[1]}"
        nome_vizinho = chave_vizinho

        try:
            msg = ler_pacote(conexao)
            if not msg or msg.get("tipo") != "HANDSHAKE":
                conexao.close()
                return

            nome_vizinho = msg.get("nome", chave_vizinho)
            porta_escuta = msg.get("porta_escuta", endereco[1])
            chave_vizinho = f"{endereco[0]}:{porta_escuta}"

            self.log.recebeu(nome_vizinho, "HANDSHAKE", f"Porta={porta_escuta}")

            with self.trava_conexoes:
                self.conexoes[chave_vizinho] = conexao

            # Responde Handshake
            resposta = {
                "tipo": "HANDSHAKE",
                "nome": self.nome,
                "porta_escuta": self.porta
            }
            conexao.sendall(criar_pacote(resposta))

            # Envia BitField inicial
            bitfield = {
                "tipo": "BITFIELD",
                "blocos": self.storage.lista_do_que_tenho()
            }
            conexao.sendall(criar_pacote(bitfield))
            self.log.enviou(nome_vizinho, "BITFIELD", f"{len(bitfield['blocos'])} chunks anunciados")

            self._loop_mensagens(conexao, chave_vizinho, nome_vizinho)

        except Exception as e:
            self.log.aviso(f"Conexão com {nome_vizinho} encerrada: {e}")
        finally:
            self._fechar_conexao(chave_vizinho, conexao)

    # =========================================================================
    # CLIENTE
    # =========================================================================

    def _conectar_vizinhos(self):
        while self.rodando:
            for ip, porta in self.vizinhos:
                chave = f"{ip}:{porta}"
                if ip == self.host and porta == self.porta:
                    continue

                with self.trava_conexoes:
                    ja_conectado = chave in self.conexoes

                if not ja_conectado:
                    threading.Thread(target=self._tentar_conectar, args=(ip, porta), daemon=True).start()

            time.sleep(2.0)

    def _tentar_conectar(self, ip: str, porta: int):
        chave = f"{ip}:{porta}"
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(4.0)
            sock.connect((ip, porta))
            sock.settimeout(None)

            nome_vizinho = f"Peer-{porta}"

            hs = {
                "tipo": "HANDSHAKE",
                "nome": self.nome,
                "porta_escuta": self.porta
            }
            sock.sendall(criar_pacote(hs))
            self.log.enviou(nome_vizinho, "HANDSHAKE", f"Conectou em {chave}")

            resp = ler_pacote(sock)
            if not resp or resp.get("tipo") != "HANDSHAKE":
                sock.close()
                return

            nome_vizinho = resp.get("nome", nome_vizinho)
            self.log.recebeu(nome_vizinho, "HANDSHAKE", "Aceito")

            # Envia nosso BitField
            bf = {
                "tipo": "BITFIELD",
                "blocos": self.storage.lista_do_que_tenho()
            }
            sock.sendall(criar_pacote(bf))
            self.log.enviou(nome_vizinho, "BITFIELD", f"{len(bf['blocos'])} chunks anunciados")

            with self.trava_conexoes:
                self.conexoes[chave] = sock

            self._loop_mensagens(sock, chave, nome_vizinho)

        except (ConnectionRefusedError, socket.timeout):
            pass
        except Exception as e:
            self.log.aviso(f"Falha na conexão com {chave}: {e}")

    # =========================================================================
    # TRATAMENTO DE MENSAGENS
    # =========================================================================

    def _loop_mensagens(self, conexao: socket.socket, chave_vizinho: str, nome_vizinho: str):
        while self.rodando:
            msg = ler_pacote(conexao)
            if msg is None:
                break

            tipo = msg.get("tipo")

            if tipo == "BITFIELD":
                blocos = set(msg.get("blocos", []))
                with self.trava_chunks:
                    self.chunks_vizinhos[chave_vizinho] = blocos
                self.log.recebeu(nome_vizinho, "BITFIELD", f"{len(blocos)} chunks disponíveis")

            elif tipo == "HAVE":
                indice = msg.get("bloco")
                if indice is not None:
                    with self.trava_chunks:
                        if chave_vizinho not in self.chunks_vizinhos:
                            self.chunks_vizinhos[chave_vizinho] = set()
                        self.chunks_vizinhos[chave_vizinho].add(indice)
                    self.log.recebeu(nome_vizinho, "HAVE", f"Adquiriu chunk #{indice}")

            elif tipo == "REQUEST":
                indice = msg.get("bloco")
                self.log.recebeu(nome_vizinho, "REQUEST", f"Pediu chunk #{indice}")
                self._responder_pedido_chunk(conexao, nome_vizinho, indice)

            elif tipo == "PIECE":
                indice = msg.get("bloco")
                dados_b64 = msg.get("dados", "")
                self.log.recebeu(nome_vizinho, "PIECE", f"Recebido chunk #{indice}")
                self._processar_chunk_recebido(indice, dados_b64)

    def _responder_pedido_chunk(self, conexao: socket.socket, nome_vizinho: str, indice: int):
        if self.storage.tem_chunk(indice):
            conteudo = self.storage.pegar_chunk(indice)
            if conteudo:
                resposta = {
                    "tipo": "PIECE",
                    "bloco": indice,
                    "dados": bytes_para_texto(conteudo)
                }
                try:
                    conexao.sendall(criar_pacote(resposta))
                    self.log.enviou(nome_vizinho, "PIECE", f"Chunk #{indice} ({len(conteudo)} bytes)")
                except Exception as e:
                    self.log.erro(f"Erro ao enviar chunk #{indice}: {e}")

    def _processar_chunk_recebido(self, indice: int, dados_b64: str):
        dados_chunk = texto_para_bytes(dados_b64)

        with self.trava_pedidos:
            self.pedidos_em_andamento.discard(indice)

        sucesso = self.storage.salvar_chunk(indice, dados_chunk)
        if sucesso:
            self.log.sucesso(f"Chunk #{indice} validado com SHA-256 e salvo!")
            self.log.progresso(self.storage.bitfield.count(), self.storage.metadata.total_chunks)

            # Torna-se Seeder parcial imediatamente
            self._anunciar_have_para_todos(indice)

            if self.storage.download_finalizado() and not self.arquivo_montado.is_set():
                with self.trava_montagem:
                    if not self.arquivo_montado.is_set():
                        self.log.sucesso("Download 100% concluído! Montando arquivo final...")
                        from pathlib import Path
                        Path(self.pasta_reconstrucao).mkdir(parents=True, exist_ok=True)
                        destino = str(Path(self.pasta_reconstrucao) / self.storage.metadata.filename)
                        
                        valido = self.storage.montar_arquivo(destino)
                        if valido:
                            self.log.sucesso(f"Arquivo reconstruído e validado com sucesso em '{destino}'!")
                        else:
                            self.log.erro("Falha na validação do hash global do arquivo reconstruído!")
                        self.arquivo_montado.set()
        else:
            self.log.erro(f"Falha na validação de hash do chunk #{indice}!")

    def _anunciar_have_para_todos(self, indice: int):
        msg_have = {
            "tipo": "HAVE",
            "bloco": indice
        }
        pacote = criar_pacote(msg_have)

        with self.trava_conexoes:
            for chave, s in list(self.conexoes.items()):
                try:
                    s.sendall(pacote)
                    self.log.enviou(chave, "HAVE", f"Anunciando posse do chunk #{indice}")
                except Exception:
                    pass

    # =========================================================================
    # DOWNLOADER
    # =========================================================================

    def _gerenciador_downloads(self):
        while self.rodando:
            if self.storage.download_finalizado():
                time.sleep(1.0)
                continue

            faltando = self.storage.lista_do_que_falta()
            if not faltando:
                time.sleep(0.5)
                continue

            # Se já há muitos pedidos em trânsito nesta conexão, espera as respostas
            with self.trava_pedidos:
                em_voo = len(self.pedidos_em_andamento)

            if em_voo >= 64:
                time.sleep(0.005)
                continue

            limite_novos = 64 - em_voo
            pedidos_nesta_rodada = 0
            for bloco in faltando:
                if pedidos_nesta_rodada >= limite_novos:
                    break

                with self.trava_pedidos:
                    if bloco in self.pedidos_em_andamento:
                        continue

                candidatos = []
                with self.trava_chunks:
                    for chave, blocos_dele in self.chunks_vizinhos.items():
                        if bloco in blocos_dele:
                            candidatos.append(chave)

                if candidatos:
                    escolhido = random.choice(candidatos)
                    self._pedir_chunk(escolhido, bloco)
                    pedidos_nesta_rodada += 1

            time.sleep(0.005)

    def _pedir_chunk(self, chave_vizinho: str, indice: int):
        with self.trava_conexoes:
            sock = self.conexoes.get(chave_vizinho)

        if not sock:
            return

        with self.trava_pedidos:
            self.pedidos_em_andamento.add(indice)

        pedido = {
            "tipo": "REQUEST",
            "bloco": indice
        }

        try:
            sock.sendall(criar_pacote(pedido))
            self.log.enviou(chave_vizinho, "REQUEST", f"Pedindo chunk #{indice}")
        except Exception:
            with self.trava_pedidos:
                self.pedidos_em_andamento.discard(indice)

    def _fechar_conexao(self, chave: str, s: socket.socket):
        with self.trava_conexoes:
            self.conexoes.pop(chave, None)
        with self.trava_chunks:
            self.chunks_vizinhos.pop(chave, None)
        try:
            s.close()
        except Exception:
            pass

