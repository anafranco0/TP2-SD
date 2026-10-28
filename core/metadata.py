import json
import hashlib
import os

class Metadata:
    def __init__(
            self,
            filename,
            file_size,
            chunk_size,
            total_chunks,
            file_hash,
            chunk_hashes
    ):

        self.filename = filename
        self.file_size = file_size
        self.chunk_size = chunk_size
        self.total_chunks = total_chunks
        self.file_hash = file_hash
        self.chunk_hashes = chunk_hashes

    def to_dict(self):
        return{
            "filename":self.filename,
            "file_size":self.file_size,
            "chunk_size":self.chunk_size,
            "total_chunks": self.total_chunks,
            "file_hash": self.file_hash,
            "chunk_hashes": self.chunk_hashes
        }

    def save(self, filepath):

        with open(filepath, "w") as f:
            json.dump(
                self.to_dict(),
                f,
                indent=4
            )
    @classmethod
    def load(cls, filepath):

        with open(filepath, "r") as f:
            data=json.load(f)

        return cls(**data)

    @classmethod
    def create_from_file(
        cls,
        filepath,
        chunk_size
    ):
        chunk_hashes = []
        sha = hashlib.sha256()

        with open(filepath,"rb") as f:
            while True:
                chunk = f.read(
                    chunk_size
                )

                if not chunk:
                    break

                sha.update(chunk)

                chunk_hashes.append(
                    hashlib.sha256(
                        chunk
                    ).hexdigest()
                )
        return cls(
            filename=os.path.basename(
                filepath
            ),
            file_size=os.path.getsize(
                filepath
            ),
            chunk_size=chunk_size,
            total_chunks=len(
                chunk_hashes
            ),
            file_hash=sha.hexdigest(),
            chunk_hashes=chunk_hashes
        )