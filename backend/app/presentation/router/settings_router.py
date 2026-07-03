"""BYOK CLOVA 설정 라우터 — 연결 테스트 + 마스킹 설정 영속.

보안 불변식: 원문 키는 요청 본문으로만 받고, 응답·저장소에는 마스킹된 프리뷰만 남긴다.
device_id 키잉(User 테이블 없음).
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.application.usecase.test_clova_connection import TestClovaConnectionUseCase
from app.domain.model.clova_setting import ClovaSetting
from app.domain.repository.clova_setting_repository import ClovaSettingRepository
from app.domain.service.clova_credential import mask_api_key
from app.infrastructure.config.dependencies import (
    get_clova_connection_tester,
    get_clova_setting_repo,
)
from app.presentation.router.settings_schemas import (
    ClovaSettingPutRequest,
    ClovaSettingResponse,
    ClovaTestRequest,
    ClovaTestResponse,
)

router = APIRouter(prefix="/api/v1/settings/clova", tags=["settings"])


@router.post(
    "/test",
    response_model=ClovaTestResponse,
    summary="CLOVA 키 연결 테스트",
    description="제공된 키로 CLOVA 연결 가능 여부를 확인합니다. 원문 키는 응답에 노출되지 않습니다.",
)
async def test_clova_connection(
    req: ClovaTestRequest,
    tester=Depends(get_clova_connection_tester),
):
    key = (req.api_key or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="API 키가 비어 있습니다.")
    usecase = TestClovaConnectionUseCase(tester)
    ok = await usecase.execute(key)
    return ClovaTestResponse(ok=ok, masked=mask_api_key(key))


@router.put(
    "",
    response_model=ClovaSettingResponse,
    summary="CLOVA 키 설정 저장(마스킹)",
    description="키의 마스킹 프리뷰만 device_id 기준으로 저장합니다. 원문 키는 서버에 저장되지 않습니다.",
)
async def put_clova_setting(
    req: ClovaSettingPutRequest,
    repo: ClovaSettingRepository = Depends(get_clova_setting_repo),
):
    key = (req.api_key or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="API 키가 비어 있습니다.")
    masked = mask_api_key(key)
    await repo.upsert(ClovaSetting(device_id=req.device_id, masked_key=masked, has_key=True))
    return ClovaSettingResponse(has_key=True, masked=masked)


@router.get(
    "",
    response_model=ClovaSettingResponse,
    summary="CLOVA 키 설정 조회(마스킹)",
    description="device_id의 저장된 마스킹 프리뷰와 키 보유 여부를 반환합니다.",
)
async def get_clova_setting(
    device_id: str = Query(..., description="익명 디바이스 식별자"),
    repo: ClovaSettingRepository = Depends(get_clova_setting_repo),
):
    setting = await repo.get(device_id)
    if setting is None:
        return ClovaSettingResponse(has_key=False, masked="")
    return ClovaSettingResponse(has_key=setting.has_key, masked=setting.masked_key)
