from pathlib import Path
import hashlib

from core.chunk import Chunk
from core.metadata import Metadata

class FileManager:

    def split_file(
            self,
            filepath,
            chunks_dir,
            chunk_size
    ):
        chunks = []

        Path(
            chunks_dir
        ).mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
            filepath,
            "rb"
        )as file:

            index = 0
            
            while True:

                data = file.read(
                    chunk_size
                )

                if not data:
                    break

                chunk = Chunk(
                    index=index,
                    data=data
                )

                chunk_path = (
                    Path(chunks_dir)
                    / f"chunk_{index}.part"
                )

                with open(
                    chunk_path,
                    "wb"
                )as out:
                    out.write(
                        data
                    )

                chunks.append(
                    chunk
                )

                index += 1

        return chunks

    def assemble_file(
            self, 
            chunks_dir,
            metadata,
            output_path
    ):
        with open(
            output_path,
            "wb"
        )as out:

            for i in range(
                metadata.total_chunks
            ):

                chunk_path = (
                    Path(chunks_dir)
                    / f"chunk_{i}.part"
                )

                with open(
                    chunk_path,
                    "rb"
                )as chunk:

                    out. write(
                        chunk.read()
                    )

    def validate_chunk(
            self,
            chunk_data,
            expected_hash
    ):

        current_hash = (
            hashlib.sha256(
                chunk_data
            ).hexdigest()
        )

        return(
            current_hash == expected_hash
        )

    def validate_file(
            self,
            filepath,
            metadata
    ):

        sha = hashlib.sha256()

        with open(
            filepath,
            "rb"
        )as f:

            while True:

                block = f.read(
                    4096
                )

                if not block:
                    break

                sha.update(
                    block
                )

        return(
            sha.hexdigest() == metadata.file_hash
        )

    def create_metadata(
            self,
            filepath,
            chunk_size
    ):
        return Metadata.create_from_file(
            filepath,
            chunk_size
        )