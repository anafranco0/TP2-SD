from core.file_manager import FileManager

def main():

    fm = FileManager()

    print("=== TESTE 1: Criar Metadata ===")

    metadata = fm.create_metadata(
        "arquivo_teste.txt",
        4
    )

    print("Arquivo:", metadata.filename)
    print("Chunks:", metadata.total_chunks)

    print("\n=== TESTE 2: Dividir Arquivo ===")

    chunks = fm.split_file(
        "arquivo_teste.txt",
        "chunks",
        4
    )

    print("Quantidade de chunks:", len(chunks))

    for chunk in chunks:
        print(
            chunk.index,
            chunk.hash
        )

    print("\n=== TESTE 3: Validar Arquivo ===")

    print(
        fm.validate_file(
            "arquivo_teste.txt",
            metadata
        )
    )

    print("\n=== TESTE 4: Validar Primeiro Chunk ===")

    print(
        fm.validate_chunk(
            chunks[0].data,
            metadata.chunk_hashes[0]
        )
    )

    print("\n=== TESTE 5: Montar Arquivo ===")

    fm.assemble_file(
        "chunks",
        metadata,
        "arquivo_recuperado.txt"
    )

    print(
        "arquivo_recuperado.txt criado!"
    )

    print("\n=== TESTE 6: Validar Arquivo Recuperado ===")

    print(
        fm.validate_file(
            "arquivo_recuperado.txt",
            metadata
        )
    )

if __name__ == "__main__":
    main()