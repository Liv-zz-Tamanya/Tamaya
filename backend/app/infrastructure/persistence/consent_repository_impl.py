from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.model.consent import Consent
from app.domain.repository.consent_repository import ConsentRepository
from app.infrastructure.persistence.models import ConsentModel


class ConsentRepositoryImpl(ConsentRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save(self, consent: Consent) -> Consent:
        model = ConsentModel(
            id=consent.id,
            user_id=consent.user_id,
            version=consent.version,
            agreed_at=consent.agreed_at,
        )
        self._db.add(model)
        await self._db.commit()
        return consent
