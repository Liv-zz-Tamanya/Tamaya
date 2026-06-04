from uuid import UUID

from app.domain.model.character import (
    CHARACTER_COLORS,
    CHARACTER_PERSONALITIES,
    Character,
)
from app.domain.repository.character_repository import CharacterRepository


class CreateCharacterUseCase:
    def __init__(self, character_repo: CharacterRepository) -> None:
        self._character_repo = character_repo

    async def execute(
        self, user_id: UUID, name: str, color: str, personalities: list[str]
    ) -> Character:
        if len(name) > 10:
            raise ValueError("name_too_long")
        if len(personalities) > 2:
            raise ValueError("personalities_max_2")
        if color not in CHARACTER_COLORS:
            raise ValueError("invalid_color")
        if any(p not in CHARACTER_PERSONALITIES for p in personalities):
            raise ValueError("invalid_personality")

        existing = await self._character_repo.find_by_user_id(user_id)
        character = Character(user_id=user_id, name=name, color=color, personalities=personalities)
        if existing:
            # 재생성 시 동일 행 갱신 (characters.user_id unique)
            character.id = existing.id
        return await self._character_repo.save(character)
