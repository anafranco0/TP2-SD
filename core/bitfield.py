class BitField:

    def __init__(
            self,
            total_chunks
    ):
        self.blocks = (
            [False]
            *total_chunks
        )

    def have(self, index):
        self.blocks[index]=True

    def has(self, index):
        return self.blocks[index]

    def missing(self):
        return[
            i
            for i, status
            in enumerate(
                self.blocks
            )
            if not status
        ]

    def complete(self):
        return all(self.blocks)

    def count(self):
        return sum(self.blocks)

    def serialize(self):
        return self.blocks