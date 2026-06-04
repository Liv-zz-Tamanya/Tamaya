from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.application.usecase.save_diary_entry import SaveDiaryEntryUseCase
from app.domain.model.diary_entry import DiaryEntry
from app.domain.model.user import User
from app.domain.repository.diary_entry_repository import DiaryEntryRepository
from app.infrastructure.config.dependencies import get_current_user, get_diary_entry_repo
from app.presentation.router.v1_schemas import (
    DiaryEntryResponse,
    DiarySaveRequest,
    DiarySaveResponse,
    RewardResponse,
)

router = APIRouter(prefix="/v1/diary", tags=["diary"])


def _to_response(entry: DiaryEntry) -> DiaryEntryResponse:
    return DiaryEntryResponse(
        diary_id=entry.id,
        date=entry.entry_date,
        moods=entry.moods,
        keywords=entry.keywords,
        body=entry.body,
        tomorrow=entry.tomorrow,
        created_at=entry.created_at,
    )


@router.post("", response_model=DiarySaveResponse, status_code=201, summary="일기 저장 + 리워드")
async def save_diary(
    body: DiarySaveRequest,
    user: User = Depends(get_current_user),
    repo: DiaryEntryRepository = Depends(get_diary_entry_repo),
):
    try:
        result = await SaveDiaryEntryUseCase(repo).execute(
            user_id=user.id,
            entry_date=body.date,
            moods=body.moods,
            keywords=body.keywords,
            body=body.body,
            tomorrow=body.tomorrow,
            daily_check_snapshot=body.daily_check_snapshot,
            session_id=body.session_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return DiarySaveResponse(
        diary_id=result["diary_id"],
        reward=RewardResponse(**result["reward"]),
    )


@router.get("", response_model=list[DiaryEntryResponse], summary="월별 일기 목록")
async def list_diary(
    month: str = Query(..., description="YYYY-MM"),
    user: User = Depends(get_current_user),
    repo: DiaryEntryRepository = Depends(get_diary_entry_repo),
):
    try:
        year, mon = (int(x) for x in month.split("-"))
    except ValueError:
        raise HTTPException(status_code=400, detail="month 형식은 YYYY-MM 입니다.")
    entries = await repo.find_by_month(user.id, year, mon)
    return [_to_response(e) for e in entries]


@router.get("/{entry_date}", response_model=DiaryEntryResponse, summary="날짜별 일기")
async def get_diary(
    entry_date: date,
    user: User = Depends(get_current_user),
    repo: DiaryEntryRepository = Depends(get_diary_entry_repo),
):
    entry = await repo.find_by_date(user.id, entry_date)
    if entry is None:
        raise HTTPException(status_code=404, detail="해당 날짜의 일기가 없습니다.")
    return _to_response(entry)
