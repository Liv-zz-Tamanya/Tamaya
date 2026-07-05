from dataclasses import dataclass

from app.domain.model.diary import Diary
from app.domain.repository.diary_repository import DiaryRepository


@dataclass
class ListDiariesResult:
    items: list[Diary]
    total: int


class ListDiariesUseCase:
    def __init__(self, repo: DiaryRepository) -> None:
        self._repo = repo

    async def execute(
        self, device_id: str, offset: int = 0, limit: int = 20
    ) -> ListDiariesResult:
        items = await self._repo.find_all(device_id, offset=offset, limit=limit)
        total = await self._repo.count(device_id)
        return ListDiariesResult(items=items, total=total)
