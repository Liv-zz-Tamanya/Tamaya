from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.model.character import Character
from app.domain.repository.character_repository import CharacterRepository
from app.infrastructure.persistence.models import CharacterModel


class CharacterRepositoryImpl(CharacterRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save(self, character: Character) -> Character:
        model = await self._db.get(CharacterModel, character.id)
        if model is None:
            model = CharacterModel(id=character.id, created_at=character.created_at)
            self._db.add(model)
        model.user_id = character.user_id
        model.name = character.name
        model.color = character.color
        model.personalities = character.personalities
        model.level = character.level
        model.intimacy = character.intimacy
        model.satiety = character.satiety
        model.vitality = character.vitality
        model.equipped_item = character.equipped_item
        await self._db.commit()
        return character

    async def find_by_user_id(self, user_id: UUID) -> Character | None:
        stmt = select(CharacterModel).where(CharacterModel.user_id == user_id)
        result = await self._db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    @staticmethod
    def _to_domain(model: CharacterModel) -> Character:
        return Character(
            id=model.id,
            user_id=model.user_id,
            name=model.name,
            color=model.color,
            personalities=list(model.personalities),
            level=model.level,
            intimacy=model.intimacy,
            satiety=model.satiety,
            vitality=model.vitality,
            equipped_item=model.equipped_item,
            created_at=model.created_at,
        )
