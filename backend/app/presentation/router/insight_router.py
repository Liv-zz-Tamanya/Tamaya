"""웰빙 인사이트 라우터 — 주/월 집계 조회.

device_id 키잉(User 테이블 없음)으로 기간 정성신호를 집계한다. 기간 파라미터가
잘못된 형식이면 400, 빈 기간이어도 usecase가 well-formed 결과를 주므로 200을 반환한다.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.application.service.insight_output_parser import InsightOutputError
from app.application.usecase.generate_weekly_insight_report import (
    GenerateWeeklyInsightReportUseCase,
    GetCachedWeeklyInsightReportUseCase,
)
from app.application.usecase.get_monthly_insight import GetMonthlyInsightUseCase
from app.application.usecase.get_weekly_insight import GetWeeklyInsightUseCase
from app.domain.service.insight_period import parse_iso_week, parse_month, week_bounds
from app.infrastructure.config.dependencies import (
    get_cached_weekly_insight_report_usecase,
    get_generate_weekly_insight_report_usecase,
    get_monthly_insight_usecase,
    get_weekly_insight_usecase,
)
from app.presentation.router.insight_schemas import InsightReportResponse, InsightResponse

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


@router.post(
    "/weekly/report",
    response_model=InsightReportResponse,
    summary="주간 인사이트 리포트 생성 또는 캐시 반환",
    description=(
        "통계 게이트를 통과한 후보로 주간 인사이트 카드를 생성합니다. "
        "같은 주차의 리포트가 이미 있으면 LLM 호출 없이 캐시를 반환합니다."
    ),
)
async def create_weekly_insight_report(
    device_id: str = Query(..., min_length=1, description="익명 디바이스 식별자"),
    week: str = Query(..., description="ISO 주차 (예: 2026-W31)"),
    usecase: GenerateWeeklyInsightReportUseCase = Depends(
        get_generate_weekly_insight_report_usecase
    ),
):
    try:
        year, week_no = parse_iso_week(week)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        report, from_cache = await usecase.execute(
            device_id=device_id, year=year, week=week_no
        )
    except InsightOutputError as e:
        # 잘못된 LLM 출력은 빈 리포트로 위장하지 않는다 — 캐시 미저장, 502
        raise HTTPException(status_code=502, detail=f"인사이트 생성 출력 오류: {e}")
    start, end = week_bounds(year, week_no)
    return InsightReportResponse.from_domain(report, start, end, from_cache)


@router.get(
    "/weekly/report",
    response_model=InsightReportResponse,
    summary="주간 인사이트 리포트 캐시 조회",
    description="캐시된 리포트만 반환합니다. 없으면 404이며 LLM을 호출하지 않습니다.",
)
async def get_weekly_insight_report(
    device_id: str = Query(..., min_length=1, description="익명 디바이스 식별자"),
    week: str = Query(..., description="ISO 주차 (예: 2026-W31)"),
    usecase: GetCachedWeeklyInsightReportUseCase = Depends(
        get_cached_weekly_insight_report_usecase
    ),
):
    try:
        year, week_no = parse_iso_week(week)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    report = await usecase.execute(device_id=device_id, year=year, week=week_no)
    if report is None:
        raise HTTPException(status_code=404, detail="해당 주차의 리포트가 없습니다.")
    start, end = week_bounds(year, week_no)
    return InsightReportResponse.from_domain(report, start, end, from_cache=True)


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
