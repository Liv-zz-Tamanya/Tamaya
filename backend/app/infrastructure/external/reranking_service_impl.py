"""Sentence Transformers CrossEncoder 기반 reranker 구현.

모델은 lazy 전역 singleton으로 최초 1회만 로드한다(요청마다 재로드 금지).
모델명은 settings.reranker_model(환경변수 RERANKER_MODEL)로 교체 가능하다 —
하드코딩하지 않는다. 기본값 선정 근거는 evals/README.md 참고.
"""

import threading

from app.application.service.reranking_service import RerankingService
from app.infrastructure.config.settings import settings

_model = None
_model_name = None
_lock = threading.Lock()


def _get_cross_encoder(model_name: str):
    global _model, _model_name
    if _model is None or _model_name != model_name:
        with _lock:
            if _model is None or _model_name != model_name:
                from sentence_transformers import CrossEncoder

                _model = CrossEncoder(model_name)
                _model_name = model_name
    return _model


class CrossEncoderRerankingService(RerankingService):
    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or settings.reranker_model

    def rerank(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        model = _get_cross_encoder(self._model_name)
        scores = model.predict([(query, document) for document in documents])
        return [float(score) for score in scores]
