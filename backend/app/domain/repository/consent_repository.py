from abc import ABC, abstractmethod

from app.domain.model.consent import Consent


class ConsentRepository(ABC):
    @abstractmethod
    async def save(self, consent: Consent) -> Consent: ...
