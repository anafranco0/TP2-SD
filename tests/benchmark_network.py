import os
import sys
import time
import shutil
import hashlib
from pathlib import Path

# Adiciona o diretório raiz de TP2-SD ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.metadata import Metadata
from core.file_manager import FileManager
from core.storage import PeerStorage
from core.peer import Peer

TEST_CASES = [
    # (Nome, Tamanho do Arquivo, Tamanho do Bloco, Qtd de Peers)
    # Arquivos Pequenos
    ("10KB.bin", 1024, 2),
    ("10KB.bin", 1024, 4),
    ("10KB.bin", 4096, 2),
    ("10KB.bin", 4096, 4),
    ("20KB.bin", 1024, 2),
    ("20KB.bin", 1024, 4),
    ("20KB.bin", 4096, 2),
    ("20KB.bin", 4096, 4),

    # Arquivos Médios
    ("1MB.bin", 1024, 2),
    ("1MB.bin", 1024, 4),
    ("1MB.bin", 4096, 2),
    ("1MB.bin", 4096, 4),
    ("5MB.bin", 1024, 2),
    ("5MB.bin", 1024, 4),
    ("5MB.bin", 4096, 2),
    ("5MB.bin", 4096, 4),

    # Arquivos Grandes
    ("10MB.bin", 1024, 2),
    ("10MB.bin", 1024, 4),
    ("10MB.bin", 4096, 2),
    ("10MB.bin", 4096, 4),
    ("20MB.bin", 1024, 2),
    ("20MB.bin", 1024, 4),
    ("20MB.bin", 4096, 2),
    ("20MB.bin", 4096, 4),
]

def limpar_pastas(pastas):
    for p in pastas:
        shutil.rmtree(p, ignore_errors=True)

def executar_caso(nome_arquivo, chunk_size, qtd_peers, base_port=6000):
    caminho_arquivo = Path("files") / nome_arquivo
    if not caminho_arquivo.exists():
        raise FileNotFoundError(f"Arquivo {caminho_arquivo} não encontrado!")

    # 1. Cria metadados
    fm = FileManager()
    metadata = fm.create_metadata(str(caminho_arquivo), chunk_size)
    meta_path = f"temp_meta_{chunk_size}_{nome_arquivo}.json"
    metadata.save(meta_path)

    # 2. Prepara pastas e portas
    pastas_chunks = []
    pastas_rec = []
    peers = []

    for i in range(qtd_peers):
        p_nome = f"Peer-{chr(65+i)}"
        pastas_chunks.append(f"temp_chunks_{p_nome}")
        pastas_rec.append(f"temp_rec_{p_nome}")
    
    limpar_pastas(pastas_chunks + pastas_rec)

    # Peer A é o Seeder (porta base_port)
    # Demais peers (B, C, D) são Leechers
    try:
        # Seeder
        storage_a = PeerStorage(
            metadata=metadata,
            chunks_dir=pastas_chunks[0],
            eh_seeder=True,
            arquivo_origem=str(caminho_arquivo)
        )
        peer_a = Peer(
            host="127.0.0.1",
            porta=base_port,
            vizinhos=[],
            storage=storage_a,
            nome="Peer-A",
            pasta_reconstrucao=pastas_rec[0]
        )
        peer_a.iniciar()
        peers.append(peer_a)

        # Leechers
        leechers = []
        for i in range(1, qtd_peers):
            porta = base_port + i
            p_nome = f"Peer-{chr(65+i)}"
            
            # Se for 2 peers: B conecta em A (base_port)
            # Se for 4 peers: Malha onde todos conectam em todos os nós anteriores
            vizinhos = [("127.0.0.1", base_port + j) for j in range(i)]

            storage_le = PeerStorage(
                metadata=metadata,
                chunks_dir=pastas_chunks[i],
                eh_seeder=False
            )
            peer_le = Peer(
                host="127.0.0.1",
                porta=porta,
                vizinhos=vizinhos,
                storage=storage_le,
                nome=p_nome,
                pasta_reconstrucao=pastas_rec[i]
            )
            peers.append(peer_le)
            leechers.append(peer_le)

        # Inicia Leechers e marca tempo
        start_time = time.perf_counter()
        for le in leechers:
            le.iniciar()

        # Aguarda todos os leechers terminarem o download
        timeout = 600 # 10 minutos max por teste
        t0 = time.time()
        sucesso = False
        while time.time() - t0 < timeout:
            if all(le.arquivo_montado.is_set() for le in leechers):
                sucesso = True
                break
            time.sleep(0.01)

        tempo_total = time.perf_counter() - start_time

        # Validação de integridade em todos os leechers
        hash_original = metadata.file_hash
        todos_validos = True
        for i in range(1, qtd_peers):
            rec_file = Path(pastas_rec[i]) / metadata.filename
            if not rec_file.exists():
                todos_validos = False
                break
            with open(rec_file, "rb") as f:
                h_rec = hashlib.sha256(f.read()).hexdigest()
            if h_rec != hash_original:
                todos_validos = False
                break

        status_str = "OK" if (sucesso and todos_validos) else "FALHA"

    finally:
        for p in peers:
            p.parar()
        limpar_pastas(pastas_chunks + pastas_rec)
        if os.path.exists(meta_path):
            os.remove(meta_path)
        time.sleep(0.3) # Pausa para liberação de portas TCP

    return tempo_total, status_str, metadata.total_chunks

def main():
    print("=" * 80)
    print(" BATERIA DE ESTUDOS DE CASO - REDE P2P (TABELA 1)")
    print("=" * 80)

    resultados = []
    
    # Cabeçalho da Tabela
    print(f"{'Arquivo':<10} | {'Tamanho':<8} | {'Bloco':<6} | {'Peers':<5} | {'Total Chunks':<12} | {'Tempo (s)':<10} | {'Integridade'}")
    print("-" * 80)

    tamanhos_legiveis = {
        "10KB.bin": "10 KB",
        "20KB.bin": "20 KB",
        "1MB.bin": "1 MB",
        "5MB.bin": "5 MB",
        "10MB.bin": "10 MB",
        "20MB.bin": "20 MB",
    }

    base_p = 15000
    for nome_arq, chunk_size, qtd_peers in TEST_CASES:
        t_legivel = tamanhos_legiveis.get(nome_arq, nome_arq)
        bloco_legivel = f"{chunk_size//1024} KB"
        
        tempo, status, total_chunks = executar_caso(nome_arq, chunk_size, qtd_peers, base_port=base_p)
        base_p += 10 # varia portas para evitar TIME_WAIT do TCP

        print(f"{nome_arq:<10} | {t_legivel:<8} | {bloco_legivel:<6} | {qtd_peers:<5} | {total_chunks:<12} | {tempo:<10.3f} | {status}")
        
        resultados.append({
            "arquivo": nome_arq,
            "tamanho": t_legivel,
            "bloco": bloco_legivel,
            "chunk_bytes": chunk_size,
            "peers": qtd_peers,
            "chunks": total_chunks,
            "tempo": tempo,
            "status": status
        })

    print("=" * 80)
    print("Bateria finalizada com sucesso!")

    # Salva os resultados em formato Markdown para anexar direto no relatório
    with open("RESULTADOS_TESTES.md", "w", encoding="utf-8") as f:
        f.write("# Resultados dos Estudos de Caso (Tabela 1)\n\n")
        f.write("| Arquivo | Tamanho | Tamanho do Bloco | Qtd. Peers | Total de Chunks | Tempo Médio (s) | Integridade SHA-256 |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for r in resultados:
            f.write(f"| {r['arquivo']} | {r['tamanho']} | {r['bloco']} | {r['peers']} | {r['chunks']} | {r['tempo']:.3f} s | {r['status']} |\n")

    print("[✔] Resultados salvos em 'TP2-SD/RESULTADOS_TESTES.md'!")

if __name__ == "__main__":
    main()

