"""완전 삭제 라우터 — liv-zz Private-First 핵심(서버측 device 데이터 영구 삭제).

feature-spec §3.11 DELETE /me/data 정합. confirm 가드로 오삭제 방지.
device_id 키잉(User 테이블 없음). 건강 공용 데이터(record_date 키잉)는 대상 외.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.usecase.purge_device_data import PurgeDeviceDataUseCase
from app.infrastructure.config.database import get_db

router = APIRouter(prefix="/api/v1/me", tags=["me"])


@router.delete(
    "/data",
    summary="내 데이터 완전 삭제",
    description="device_id에 귀속된 모든 서버 데이터(일기·대화·정성신호·CLOVA설정·게임·인벤토리)를 영구 삭제. "
    "liv-zz Private-First 약속 이행. confirm='DELETE-MY-DATA' 필수.",
)
async def delete_my_data(
    device_id: str = Query(..., description="익명 디바이스 식별자"),
    confirm: str = Query(..., description="안전 확인 문자열 'DELETE-MY-DATA'"),
    db: AsyncSession = Depends(get_db),
):
    if confirm != "DELETE-MY-DATA":
        raise HTTPException(status_code=400, detail="confirm 값이 올바르지 않습니다.")
    try:
        removed = await PurgeDeviceDataUseCase(db).execute(device_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"deleted": True, "items_removed": removed}
