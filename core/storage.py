import os
from pathlib import Path
from core.metadata import Metadata
from core.file_manager import FileManager
from core.bitfield import BitField

class PeerStorage:
    """
    Controla o armazenamento de chunks e estado do BitField para um Peer.
    Utiliza as classes Metadata, BitField e FileManager feitas pela dupla.
    """
    def __init__(self, metadata: Metadata, chunks_dir: str, eh_seeder: bool = False, arquivo_origem: str = None):
        self.metadata = metadata
        self.chunks_dir = Path(chunks_dir)
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.file_manager = FileManager()
        self.bitfield = BitField(self.metadata.total_chunks)
        self.eh_seeder = eh_seeder

        if eh_seeder:
            # Se for o Seeder inicial e foi informado o arquivo original, fragmenta
            if arquivo_origem and os.path.exists(arquivo_origem):
                self.file_manager.split_file(
                    arquivo_origem,
                    str(self.chunks_dir),
                    self.metadata.chunk_size
                )
            
            # Marca todos os chunks como possuídos
            for i in range(self.metadata.total_chunks):
                chunk_path = self.chunks_dir / f"chunk_{i}.part"
                if chunk_path.exists():
                    self.bitfield.have(i)
                else:
                    # Se não fragmentou de arquivo externo, verifica se já estavam lá
                    if not arquivo_origem:
                        self.bitfield.have(i)
        else:
            # Se for leecher, verifica se já existe algum chunk baixado no diretório
            for i in range(self.metadata.total_chunks):
                chunk_path = self.chunks_dir / f"chunk_{i}.part"
                if chunk_path.exists():
                    with open(chunk_path, "rb") as f:
                        conteudo = f.read()
                    if self.file_manager.validate_chunk(conteudo, self.metadata.chunk_hashes[i]):
                        self.bitfield.have(i)

    def tem_chunk(self, index: int) -> bool:
        return self.bitfield.has(index)

    def pegar_chunk(self, index: int) -> bytes | None:
        chunk_path = self.chunks_dir / f"chunk_{index}.part"
        if not chunk_path.exists():
            return None
        with open(chunk_path, "rb") as f:
            return f.read()

    def salvar_chunk(self, index: int, data: bytes) -> bool:
        if self.tem_chunk(index):
            return True

        # Validação usando a lógica da dupla
        esperado = self.metadata.chunk_hashes[index]
        if not self.file_manager.validate_chunk(data, esperado):
            return False

        chunk_path = self.chunks_dir / f"chunk_{index}.part"
        with open(chunk_path, "wb") as f:
            f.write(data)

        self.bitfield.have(index)
        return True

    def lista_do_que_tenho(self) -> list[int]:
        return [i for i, tem in enumerate(self.bitfield.blocks) if tem]

    def lista_do_que_falta(self) -> list[int]:
        return self.bitfield.missing()

    def download_finalizado(self) -> bool:
        return self.bitfield.complete()

    def montar_arquivo(self, destino: str) -> bool:
        if not self.download_finalizado():
            return False
        
        self.file_manager.assemble_file(
            str(self.chunks_dir),
            self.metadata,
            destino
        )
        return self.file_manager.validate_file(destino, self.metadata)

