from app.application.service.embedding_service import EmbeddingService

_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(_MODEL_NAME)
    return _model


class SentenceTransformerEmbeddingService(EmbeddingService):
    def embed(self, texts: list[str]) -> list[list[float]]:
        model = _get_model()
        embeddings = model.encode(texts, convert_to_numpy=True)
        return [emb.tolist() for emb in embeddings]
