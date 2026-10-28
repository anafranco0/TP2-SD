from dataclasses import dataclass
import hashlib

@dataclass
class Chunk:
    index:int
    data:bytes

    @property
    def hash(self):
        return hashlib.sha256(
            self.data
        ).hexdigest()