from pathlib import Path
import os

FILES = [
    ("10KB.bin", 10*1024),
    ("20KB.bin", 20*1024),
    ("1MB.bin", 1024*1024),
    ("5MB.bin", 5*1024*1024),
    ("10MB.bin", 10*1024*1024),
    ("20MB.bin", 20*1024*1024)
]

Path("files").mkdir(
    exist_ok=True
)

def generate_files():
    for name,size in FILES:

        with open(
            f"files/{name}",
            "wb"
        )as f:

            f.write(
                os.urandom(size)
            )
        print(
            f"Arquivo criado: {name}"
        )