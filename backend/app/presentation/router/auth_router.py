"""
인증 라우터 — DEC-022.4 + DEC-023
POST /auth/kakao    : 카카오 code → 우리 JWT 발급
POST /auth/device   : device_id 익명 사용자 → JWT 발급
POST /auth/refresh  : refresh token rotation (동시접속 strict 정합)
POST /auth/logout   : 현 세션 revoke

동시접속 strict (DEC-023):
  - 신규 로그인 시 동일 identity의 기존 active 세션 revoke → 새 세션 insert
  - 보호 라우트는 get_current_session dependency로 jti 검증 (revoked_at IS NOT NULL → 401)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.auth.jwt_handler import (
    decode_token,
    issue_access_token,
    issue_refresh_token,
)
from app.infrastructure.config.database import get_db
from app.infrastructure.config.settings import settings
from app.infrastructure.persistence.models import UserModel, UserSessionModel

router = APIRouter(prefix="/auth", tags=["auth"])


# ─── Request / Response 스키마 ──────────────────────────────────────────────────


class KakaoLoginRequest(BaseModel):
    code: str  # 카카오 인가 코드


class DeviceLoginRequest(BaseModel):
    device_id: str  # UUID v4 형식 권장 (FE 생성)


class RefreshRequest(BaseModel):
    refresh_token: str


class NicknameLoginRequest(BaseModel):
    nickname: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    identity: str  # device_id 또는 kakao_id


class NicknameCheckResponse(BaseModel):
    nickname: str
    available: bool  # True = 미사용(가입 가능) / False = 이미 사용 중(로그인됨)


class NicknameTokenResponse(TokenResponse):
    device_id: str  # 데이터 네임스페이스 (= f"nick-{nickname}")
    is_new: bool  # True = 이번에 신규 가입 / False = 기존 계정 로그인


_NICKNAME_MIN = 1
_NICKNAME_MAX = 16


def _normalize_nickname(raw: str) -> str:
    """앞뒤 공백 제거 후 길이 검증. 위반 시 400."""
    nickname = raw.strip()
    if not (_NICKNAME_MIN <= len(nickname) <= _NICKNAME_MAX):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"닉네임은 {_NICKNAME_MIN}~{_NICKNAME_MAX}자여야 합니다",
        )
    return nickname


# ─── 동시접속 strict 1세션 헬퍼 ────────────────────────────────────────────────


async def _revoke_existing_sessions(
    db: AsyncSession, *, device_id: str | None = None, kakao_id: str | None = None
) -> None:
    """동일 identity의 모든 active 세션 revoke (DEC-023)"""
    now = datetime.now(UTC).replace(tzinfo=None)
    if device_id:
        await db.execute(
            update(UserSessionModel)
            .where(UserSessionModel.device_id == device_id, UserSessionModel.revoked_at.is_(None))
            .values(revoked_at=now)
        )
    if kakao_id:
        await db.execute(
            update(UserSessionModel)
            .where(UserSessionModel.kakao_id == kakao_id, UserSessionModel.revoked_at.is_(None))
            .values(revoked_at=now)
        )
    await db.commit()


async def _create_session(
    db: AsyncSession,
    *,
    device_id: str | None = None,
    kakao_id: str | None = None,
) -> tuple[str, str, str, str]:
    """
    1. 기존 세션 revoke
    2. access jti 발급
    3. DB insert
    4. refresh token 발급 (별도 jti)
    반환: (access_token, refresh_token, access_jti, identity)
    """
    identity = device_id or kakao_id or ""
    await _revoke_existing_sessions(db, device_id=device_id, kakao_id=kakao_id)

    access_jti = str(uuid.uuid4())
    now = datetime.now(UTC).replace(tzinfo=None)

    session = UserSessionModel(
        id=uuid.uuid4(),
        device_id=device_id,
        kakao_id=kakao_id,
        jti=access_jti,
        issued_at=now,
        expires_at=now + timedelta(minutes=15),
    )
    db.add(session)
    await db.commit()

    access_token = issue_access_token(identity, access_jti)
    refresh_token, _ = issue_refresh_token(identity)
    return access_token, refresh_token, access_jti, identity


# ─── 라우트 ────────────────────────────────────────────────────────────────────


@router.post("/device", response_model=TokenResponse, summary="device_id 익명 인증")
async def login_device(body: DeviceLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    device_id 기반 익명 인증. 동일 device_id 재로그인 시 기존 세션 자동 revoke.
    Phase 1 Closed Beta 전용. Open Beta 직전 카카오/Apple OAuth로 머지.
    """
    access_token, refresh_token, _, identity = await _create_session(db, device_id=body.device_id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, identity=identity)


@router.get(
    "/nickname/check",
    response_model=NicknameCheckResponse,
    summary="닉네임 중복 확인",
)
async def check_nickname(nickname: str, db: AsyncSession = Depends(get_db)):
    """닉네임 사용 가능 여부 조회. available=True면 신규 가입, False면 기존 계정 로그인 대상."""
    name = _normalize_nickname(nickname)
    existing = await db.scalar(select(UserModel).where(UserModel.nickname == name))
    return NicknameCheckResponse(nickname=name, available=existing is None)


async def _issue_nickname_token(
    db: AsyncSession, name: str, *, is_new: bool
) -> NicknameTokenResponse:
    """닉네임 계정 세션 발급. 데이터는 device_id = f"nick-{nickname}" 네임스페이스로 분리."""
    device_id = f"nick-{name}"
    access_token, refresh_token, _, identity = await _create_session(db, device_id=device_id)
    return NicknameTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        identity=identity,
        device_id=device_id,
        is_new=is_new,
    )


@router.post(
    "/nickname/signup",
    response_model=NicknameTokenResponse,
    summary="닉네임 회원가입",
)
async def signup_nickname(body: NicknameLoginRequest, db: AsyncSession = Depends(get_db)):
    """닉네임 회원가입 (데모: 비밀번호 없음). 이미 있으면 409."""
    name = _normalize_nickname(body.nickname)
    existing = await db.scalar(select(UserModel).where(UserModel.nickname == name))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 닉네임입니다"
        )
    db.add(UserModel(id=uuid.uuid4(), nickname=name))
    await db.commit()
    return await _issue_nickname_token(db, name, is_new=True)


@router.post(
    "/nickname/login",
    response_model=NicknameTokenResponse,
    summary="닉네임 로그인",
)
async def login_nickname(body: NicknameLoginRequest, db: AsyncSession = Depends(get_db)):
    """닉네임 로그인 (데모: 비밀번호 없음). 없는 닉네임이면 404."""
    name = _normalize_nickname(body.nickname)
    existing = await db.scalar(select(UserModel).where(UserModel.nickname == name))
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="존재하지 않는 닉네임입니다. 회원가입해 주세요",
        )
    return await _issue_nickname_token(db, name, is_new=False)


@router.post("/kakao", response_model=TokenResponse, summary="카카오 OAuth2 인증")
async def login_kakao(body: KakaoLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    카카오 인가 코드 → 카카오 토큰 교환 → 사용자 정보 조회 → 우리 JWT 발급.
    KAKAO_APP_KEY 미설정 시 Mock 모드로 kakao_id = 'mock_kakao_user' 반환.
    """
    if not settings.kakao_app_key or settings.kakao_app_key == "your-kakao-rest-api-key":
        # MOCK: API 키 미수령 시 개발용 고정 kakao_id
        kakao_id = "mock_kakao_user"
    else:
        # 실 카카오 토큰 교환
        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                "https://kauth.kakao.com/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.kakao_app_key,
                    "code": body.code,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
        if token_res.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="카카오 토큰 발급 실패"
            )

        kakao_access = token_res.json().get("access_token", "")

        async with httpx.AsyncClient() as client:
            user_res = await client.get(
                "https://kapi.kakao.com/v2/user/me",
                headers={"Authorization": f"Bearer {kakao_access}"},
                timeout=10,
            )
        if user_res.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="카카오 사용자 정보 조회 실패"
            )

        kakao_id = str(user_res.json().get("id", ""))

    access_token, refresh_token, _, identity = await _create_session(db, kakao_id=kakao_id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, identity=identity)


@router.post("/refresh", response_model=TokenResponse, summary="refresh token rotation")
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """
    refresh token → 새 access + refresh 쌍 발급 (rotation).
    DEC-023: 기존 세션 revoke 후 새 세션 발급 → 강제 로그아웃 트리거.
    """
    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 refresh token"
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token이 아닙니다"
        )

    identity = payload.get("sub", "")
    # identity 형식 추론: kakao_id는 숫자 문자열, device_id는 UUID
    try:
        uuid.UUID(identity)
        device_id, kakao_id = identity, None
    except ValueError:
        device_id, kakao_id = None, identity

    access_token, new_refresh, _, ident = await _create_session(
        db, device_id=device_id, kakao_id=kakao_id
    )
    return TokenResponse(access_token=access_token, refresh_token=new_refresh, identity=ident)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="현 세션 revoke")
async def logout(
    # 실제로는 Bearer 토큰을 Authorization 헤더에서 추출해야 함
    # MVP 단계에서는 jti를 body로 받아 처리 (헤더 추출 미들웨어는 Week 2에 추가)
    jti: str,
    db: AsyncSession = Depends(get_db),
):
    """jti로 세션 revoke — 클라이언트 로그아웃"""
    now = datetime.now(UTC).replace(tzinfo=None)
    result = await db.execute(
        update(UserSessionModel)
        .where(UserSessionModel.jti == jti, UserSessionModel.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없거나 이미 로그아웃됨"
        )
