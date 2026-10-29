import json
import struct
import base64

def criar_pacote(dados: dict) -> bytes:
    """Transforma um dicionário Python em bytes prontos para a rede com prefixo de tamanho."""
    corpo = json.dumps(dados).encode("utf-8")
    tamanho = struct.pack("!I", len(corpo))
    return tamanho + corpo

def ler_pacote(conexao) -> dict | None:
    """Lê uma mensagem completa vinda do socket."""
    try:
        cabecalho = _receber_tudo(conexao, 4)
        if not cabecalho:
            return None
        
        tamanho_pacote = struct.unpack("!I", cabecalho)[0]
        corpo = _receber_tudo(conexao, tamanho_pacote)
        if not corpo:
            return None
        
        return json.loads(corpo.decode("utf-8"))
    except (ConnectionResetError, ConnectionAbortedError, OSError):
        return None

def _receber_tudo(conexao, total_bytes: int) -> bytes | None:
    """Garante a leitura de todos os bytes solicitados do stream TCP."""
    buffer = bytearray()
    while len(buffer) < total_bytes:
        pedaco = conexao.recv(total_bytes - len(buffer))
        if not pedaco:
            return None
        buffer.extend(pedaco)
    return bytes(buffer)

def bytes_para_texto(dados: bytes) -> str:
    """Converte os bytes de um chunk para Base64 para trafegar no JSON."""
    return base64.b64encode(dados).decode("ascii")

def texto_para_bytes(texto: str) -> bytes:
    """Converte a string Base64 recebida de volta para bytes."""
    return base64.b64decode(texto.encode("ascii"))

