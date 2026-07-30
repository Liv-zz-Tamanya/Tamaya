"""apply_reranking — 재정렬·안정성·fallback 정책 검증."""

from __future__ import annotations

from app.application.service.reranking_service import (
    NoOpRerankingService,
    RerankingService,
    apply_reranking,
)


class _ScriptedReranker(RerankingService):
    def __init__(self, scores: list[float]) -> None:
        self._scores = scores
        self.calls = 0

    def rerank(self, query: str, documents: list[str]) -> list[float]:
        self.calls += 1
        return self._scores


class _BrokenReranker(RerankingService):
    def rerank(self, query: str, documents: list[str]) -> list[float]:
        raise RuntimeError("model load failed")


async def test_sorts_by_score_descending():
    items = ["a", "b", "c"]
    result = await apply_reranking(
        _ScriptedReranker([0.1, 0.9, 0.5]), "q", items, items, final_k=3
    )
    assert result == ["b", "c", "a"]


async def test_equal_scores_preserve_vector_order():
    items = ["first", "second", "third"]
    result = await apply_reranking(
        _ScriptedReranker([0.5, 0.5, 0.5]), "q", items, items, final_k=3
    )
    assert result == ["first", "second", "third"]


async def test_final_k_truncates_after_rerank():
    items = ["a", "b", "c", "d"]
    result = await apply_reranking(
        _ScriptedReranker([0.1, 0.9, 0.8, 0.2]), "q", items, items, final_k=2
    )
    assert result == ["b", "c"]


async def test_empty_candidates_skip_model():
    reranker = _ScriptedReranker([])
    assert await apply_reranking(reranker, "q", [], [], final_k=5) == []
    assert reranker.calls == 0  # 빈 후보는 모델을 호출하지 않는다


async def test_single_candidate_skips_model():
    reranker = _ScriptedReranker([0.5])
    assert await apply_reranking(reranker, "q", ["only"], ["only"], final_k=5) == ["only"]
    assert reranker.calls == 0


async def test_model_failure_falls_back_to_vector_order():
    items = ["a", "b", "c"]
    result = await apply_reranking(_BrokenReranker(), "q", items, items, final_k=2)
    assert result == ["a", "b"]  # 요청은 죽지 않고 vector 순서 유지


async def test_score_length_mismatch_falls_back():
    items = ["a", "b", "c"]
    result = await apply_reranking(_ScriptedReranker([0.9]), "q", items, items, final_k=3)
    assert result == ["a", "b", "c"]


async def test_noop_keeps_vector_order():
    items = ["a", "b", "c"]
    result = await apply_reranking(NoOpRerankingService(), "q", items, items, final_k=2)
    assert result == ["a", "b"]
