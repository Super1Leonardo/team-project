from __future__ import annotations

import hashlib
import math
import re


class HashEmbeddingEncoder:
    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions

    def encode(self, text: str) -> list[float]:
        normalized = " ".join(text.casefold().split())
        tokens = re.findall(r"\w+", normalized) or [normalized or "empty"]
        vector = [0.0] * self.dimensions

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for index in range(self.dimensions):
                byte = digest[index % len(digest)]
                sign = 1.0 if byte % 2 == 0 else -1.0
                vector[index] += sign * (0.25 + byte / 255.0)

        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]
