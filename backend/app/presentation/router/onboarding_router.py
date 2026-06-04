from datetime import datetime

from fastapi import APIRouter, Depends

from app.domain.model.consent import Consent
from app.domain.model.user import User
from app.domain.repository.consent_repository import ConsentRepository
from app.domain.repository.user_repository import UserRepository
from app.infrastructure.config.dependencies import (
    get_consent_repo,
    get_current_user,
    get_user_repo,
)
from app.presentation.router.v1_schemas import (
    OnboardingCompleteResponse,
    PrivacyConsentRequest,
    PrivacyConsentResponse,
)

router = APIRouter(prefix="/v1/onboarding", tags=["onboarding"])


@router.post("/privacy-consent", response_model=PrivacyConsentResponse, summary="개인정보 동의")
async def privacy_consent(
    body: PrivacyConsentRequest,
    user: User = Depends(get_current_user),
    consent_repo: ConsentRepository = Depends(get_consent_repo),
):
    consent = Consent(
        user_id=user.id,
        version=body.version,
        agreed_at=body.agreed_at or datetime.now(),
    )
    await consent_repo.save(consent)
    return PrivacyConsentResponse(ok=True, consent_id=consent.id)


@router.post("/complete", response_model=OnboardingCompleteResponse, summary="온보딩 완료")
async def complete_onboarding(
    user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repo),
):
    user.needs_onboarding = False
    await user_repo.save(user)
    return OnboardingCompleteResponse(ok=True, completed_at=datetime.now())
