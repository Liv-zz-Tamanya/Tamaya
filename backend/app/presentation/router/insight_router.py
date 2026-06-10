"""웰빙 인사이트 라우터 — 주/월 집계 조회.

device_id 키잉(User 테이블 없음)으로 기간 정성신호를 집계한다. 기간 파라미터가
잘못된 형식이면 400, 빈 기간이어도 usecase가 well-formed 결과를 주므로 200을 반환한다.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.application.usecase.get_monthly_insight import GetMonthlyInsightUseCase
from app.application.usecase.get_weekly_insight import GetWeeklyInsightUseCase
from app.domain.service.insight_period import parse_iso_week, parse_month
from app.infrastructure.config.dependencies import (
    get_monthly_insight_usecase,
    get_weekly_insight_usecase,
)
from app.presentation.router.insight_schemas import InsightResponse

router = APIRouter(prefix="/api/v1/insights", tags=["insights"])


@router.get(
    "/weekly",
    response_model=InsightResponse,
    summary="주간 웰빙 인사이트",
    description="ISO 주차(YYYY-Www)의 웰빙 스코어 집계와 일별 trend를 반환합니다.",
)
async def get_weekly_insight(
    device_id: str = Query(..., description="익명 디바이스 식별자"),
    week: str = Query(..., description="ISO 주차 (예: 2026-W23)"),
    usecase: GetWeeklyInsightUseCase = Depends(get_weekly_insight_usecase),
):
    try:
        year, week_no = parse_iso_week(week)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    result = await usecase.execute(device_id=device_id, year=year, week=week_no)
    return InsightResponse.from_result(result)


@router.get(
    "/monthly",
    response_model=InsightResponse,
    summary="월간 웰빙 인사이트",
    description="월(YYYY-MM)의 웰빙 스코어 집계와 주별 trend를 반환합니다.",
)
async def get_monthly_insight(
    device_id: str = Query(..., description="익명 디바이스 식별자"),
    month: str = Query(..., description="월 (예: 2026-06)"),
    usecase: GetMonthlyInsightUseCase = Depends(get_monthly_insight_usecase),
):
    try:
        year, month_no = parse_month(month)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    result = await usecase.execute(device_id=device_id, year=year, month=month_no)
    return InsightResponse.from_result(result)
