from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.application.usecase.upsert_daily_check import UpsertDailyCheckUseCase
from app.domain.model.user import User
from app.domain.repository.daily_check_repository import DailyCheckRepository
from app.infrastructure.config.dependencies import get_current_user, get_daily_check_repo
from app.presentation.router.v1_schemas import (
    DailyCheckBody,
    DailyCheckMonthResponse,
    DailyCheckPutResponse,
)

router = APIRouter(prefix="/v1/daily-check", tags=["daily-check"])


def _to_body(check) -> DailyCheckBody:
    return DailyCheckBody(
        food=check.food,
        water=check.water,
        sleep=check.sleep,
        movement=check.movement,
        sun=check.sun,
    )


@router.put("/{check_date}", response_model=DailyCheckPutResponse, summary="데일리 체크 저장(upsert)")
async def put_daily_check(
    check_date: date,
    body: DailyCheckBody,
    user: User = Depends(get_current_user),
    repo: DailyCheckRepository = Depends(get_daily_check_repo),
):
    result = await UpsertDailyCheckUseCase(repo).execute(
        user_id=user.id,
        check_date=check_date,
        food=body.food,
        water=body.water,
        sleep=body.sleep,
        movement=body.movement,
        sun=body.sun,
    )
    return DailyCheckPutResponse(**result)


@router.get("", response_model=DailyCheckMonthResponse, summary="월별 데일리 체크")
async def get_daily_check_month(
    month: str = Query(..., description="YYYY-MM"),
    user: User = Depends(get_current_user),
    repo: DailyCheckRepository = Depends(get_daily_check_repo),
):
    try:
        year, mon = (int(x) for x in month.split("-"))
    except ValueError:
        raise HTTPException(status_code=400, detail="month 형식은 YYYY-MM 입니다.")
    checks = await repo.find_by_month(user.id, year, mon)
    days = {str(c.check_date.day): _to_body(c) for c in checks}
    return DailyCheckMonthResponse(days=days)


@router.get("/{check_date}", response_model=DailyCheckBody, summary="날짜별 데일리 체크")
async def get_daily_check(
    check_date: date,
    user: User = Depends(get_current_user),
    repo: DailyCheckRepository = Depends(get_daily_check_repo),
):
    check = await repo.find_by_date(user.id, check_date)
    if check is None:
        return DailyCheckBody()
    return _to_body(check)
