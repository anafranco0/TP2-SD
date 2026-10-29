import argparse
import time
import sys
from pathlib import Path

from core.metadata import Metadata
from core.file_manager import FileManager
from core.storage import PeerStorage
from core.peer import Peer

def formatar_vizinho(texto: str) -> tuple[str, int]:
    if ":" in texto:
        ip, porta = texto.split(":")
        return ip, int(porta)
    return "127.0.0.1", int(texto)

def main():
    parser = argparse.ArgumentParser(description="P2P File Transfer - Sistemas Distribuídos CEFET-MG")
    parser.add_argument("--porta", type=int, required=True, help="Porta onde esse peer escutará conexões")
    parser.add_argument("--nome", type=str, default=None, help="Nome do Peer para os logs (ex: Peer-A)")
    parser.add_argument("--seeder", action="store_true", help="Se ativado, inicia o nó como Seeder inicial")
    parser.add_argument("--arquivo", type=str, default=None, help="Caminho do arquivo de origem (usado pelo Seeder para fatiar)")
    parser.add_argument("--metadata", type=str, default="metadata.json", help="Caminho do arquivo .json de metadados")
    parser.add_argument("--chunk-size", type=int, default=1024, help="Tamanho do chunk em bytes (1024 ou 4096)")
    parser.add_argument("--chunks-dir", type=str, default=None, help="Diretório onde os chunks ficam salvos")
    parser.add_argument("--vizinhos", nargs="*", default=[], help="Lista de vizinhos (ex: 5000 127.0.0.1:5002)")

    args = parser.parse_args()

    nome_peer = args.nome if args.nome else f"Peer-{args.porta}"
    vizinhos = [formatar_vizinho(v) for v in args.vizinhos]
    pasta_chunks = args.chunks_dir if args.chunks_dir else f"chunks_{nome_peer}"

    # Carrega ou cria metadados
    fm = FileManager()
    if args.seeder and args.arquivo:
        # Se for Seeder com arquivo, gera os metadados a partir do arquivo
        metadata = fm.create_metadata(args.arquivo, args.chunk_size)
        metadata.save(args.metadata)
    else:
        # Lê metadados existentes
        if not Path(args.metadata).exists():
            print(f"[ERRO] Arquivo de metadados '{args.metadata}' não encontrado!")
            sys.exit(1)
        metadata = Metadata.load(args.metadata)

    # Inicializa Storage desacoplado
    storage = PeerStorage(
        metadata=metadata,
        chunks_dir=pasta_chunks,
        eh_seeder=args.seeder,
        arquivo_origem=args.arquivo
    )

    peer = Peer(
        host="127.0.0.1",
        porta=args.porta,
        vizinhos=vizinhos,
        storage=storage,
        nome=nome_peer,
        pasta_reconstrucao=f"reconstructed_{nome_peer}"
    )

    try:
        peer.iniciar()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando peer...")
        peer.parar()
        sys.exit(0)

if __name__ == "__main__":
    main()

