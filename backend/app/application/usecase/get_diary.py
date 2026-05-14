from datetime import date

from app.domain.model.diary import Diary
from app.domain.repository.diary_repository import DiaryRepository


class GetDiaryByDateUseCase:
    def __init__(self, repo: DiaryRepository) -> None:
        self._repo = repo

    async def execute(self, diary_date: date) -> Diary:
        diary = await self._repo.find_by_date(diary_date)
        if not diary:
            raise ValueError("해당 날짜의 일기를 찾을 수 없습니다.")
        return diary
