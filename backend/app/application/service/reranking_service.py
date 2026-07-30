"""Reranking 추상화 — 2단계 검색(candidate retrieval → cross-encoder 재정렬)의 2단계.

인터페이스는 application에, CrossEncoder 구현은 infrastructure에 둔다.
Repository는 ML 모델을 모른다 — 재정렬은 QueryService 계층의 책임이다.

장애 정책: reranker 로딩·실행 실패가 검색 요청 전체를 죽이면 안 된다.
apply_reranking은 실패 시 기존 vector ranking을 그대로 반환하고
structured log로 fallback을 기록한다.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence

logger = logging.getLogger(__name__)

# candidate_k 기본/상한 — 과도한 추론 비용 방지. final_k(호출자 limit)보다 작으면
# apply 시점에 final_k로 올려 잡는다.
DEFAULT_CANDIDATE_K = 15
MAX_CANDIDATE_K = 50

class RerankingService(ABC):
    @abstractmethod
    def rerank(self, query: str, documents: list[str]) -> list[float]:
        """문서별 관련도 점수를 반환한다(입력 순서 유지, 높을수록 관련)."""


class NoOpRerankingService(RerankingService):
    """평가 비교(mode B)용 — 점수를 내지 않아 vector 순서가 그대로 유지된다."""

    def rerank(self, query: str, documents: list[str]) -> list[float]:
        return [0.0] * len(documents)


async def apply_reranking[T](
    reranker: RerankingService,
    query: str,
    items: Sequence[T],
    texts: Sequence[str],
    final_k: int,
) -> list[T]:
    """후보를 reranker 점수 내림차순으로 재정렬해 final_k개 반환한다.

    - 빈 후보·단일 후보는 모델을 호출하지 않는다.
    - 동점은 기존 vector 순서를 안정적으로 보존한다.
    - CPU-bound 추론은 to_thread로 실행해 event loop를 막지 않는다.
    - 실패 시 vector 순서 그대로 fallback (요청은 계속 성공한다).
    """
    if len(items) <= 1:
        return list(items[:final_k])
    try:
        scores = await asyncio.to_thread(reranker.rerank, query, list(texts))
        if len(scores) != len(items):
            raise ValueError(f"reranker returned {len(scores)} scores for {len(items)} documents")
    except Exception:
        logger.warning(
            "reranker_fallback: vector ranking 유지 (reranker=%s, candidates=%d)",
            type(reranker).__name__,
            len(items),
            exc_info=True,
        )
        return list(items[:final_k])
    order = sorted(range(len(items)), key=lambda i: (-scores[i], i))
    return [items[i] for i in order[:final_k]]
