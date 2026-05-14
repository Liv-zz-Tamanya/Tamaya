from abc import ABC, abstractmethod


class EmbeddingService(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...
