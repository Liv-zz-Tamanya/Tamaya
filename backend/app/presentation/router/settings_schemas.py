"""설정 라우터 DTO — 원문 키는 요청에만 존재하고 응답에는 마스킹만 담는다."""

from pydantic import BaseModel


class ClovaTestRequest(BaseModel):
    api_key: str


class ClovaTestResponse(BaseModel):
    ok: bool
    masked: str  # ••••last4 — 원문 키 미포함


class ClovaSettingPutRequest(BaseModel):
    # device_id는 본문이 아니라 Bearer 토큰 세션에서 추출한다(타 계정 설정 조작 방지).
    api_key: str


class ClovaSettingResponse(BaseModel):
    has_key: bool
    masked: str
