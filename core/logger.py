import sys
import threading
from datetime import datetime

_trava_terminal = threading.Lock()

class Logger:
    def __init__(self, nome_peer: str):
        self.nome_peer = nome_peer

    def _imprimir(self, tipo: str, texto: str):
        hora = datetime.now().strftime("%H:%M:%S")
        linha = f"[{hora}] [{self.nome_peer}] [{tipo}] {texto}"
        with _trava_terminal:
            try:
                print(linha, flush=True)
            except UnicodeEncodeError:
                print(linha.encode("ascii", errors="replace").decode("ascii"), flush=True)

    def info(self, msg: str):
        self._imprimir("INFO", msg)

    def sucesso(self, msg: str):
        self._imprimir("OK", msg)

    def aviso(self, msg: str):
        self._imprimir("AVISO", msg)

    def erro(self, msg: str):
        self._imprimir("ERRO", msg)

    def enviou(self, destinatario: str, tipo_msg: str, detalhes: str = ""):
        info_extra = f" -> {detalhes}" if detalhes else ""
        self._imprimir("ENVIANDO", f"{destinatario} | {tipo_msg}{info_extra}")

    def recebeu(self, remetente: str, tipo_msg: str, detalhes: str = ""):
        info_extra = f" <- {detalhes}" if detalhes else ""
        self._imprimir("RECEBIDO", f"{remetente} | {tipo_msg}{info_extra}")

    def progresso(self, tem: int, total: int):
        porcentagem = (tem / total * 100) if total > 0 else 0
        self._imprimir("PROGRESSO", f"{tem}/{total} blocos baixados ({porcentagem:.1f}%)")

