import time
from pathlib import Path

from core.file_manager import FileManager


manager = FileManager()

TEST_FILES = [
    "10KB.bin",
    "20KB.bin",
    "1MB.bin",
    "5MB.bin",
    "10MB.bin",
    "20MB.bin"
]

BLOCKS = [
    1024,
    4096
]

for filename in TEST_FILES:

    print(
        "\n=========================================================="
    )

    for block_size in BLOCKS:

        filepath = (
            f"files/{filename}"
        )

        start = (
            time.perf_counter()
        )

        metadata = (
            manager.create_metadata(
                filepath,
                block_size
            )
        )

        chunks = (
            manager.split_file(
                filepath,
                f"chunks/{filename}_{block_size}",
                block_size
            )
        )

        split_time = (
            time.perf_counter()
            - start
        )

        Path("reconstructed").mkdir(
            exist_ok=True
        )

        rebuilt_file = (
            f"reconstructed/{filename}"
        )

        start = (
            time.perf_counter()
        )

        manager.assemble_file(
            f"chunks/{filename}_{block_size}",
            metadata,
            rebuilt_file
        )

        assembly_time = (
            time.perf_counter()
            - start
        )

        valid = (
            manager.validate_file(
                rebuilt_file,
                metadata
            )
        )

        print(
            f"\nArquivo: {filename}"
        )

        print(
            f"Bloco: {block_size}"
        )

        print(
            f"Total blocos: {metadata.total_chunks}"
        )

        print(
            f"Fragmentação: "
            f"{split_time:.4f}s"
        )

        print(
            f"Montagem: "
            f"{assembly_time:.4f}s"
        )

        print(
            f"Integridade: "
            f"{'OK' if valid else 'ERRO'}"
        )