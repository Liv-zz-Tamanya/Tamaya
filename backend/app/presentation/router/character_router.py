from fastapi import APIRouter, Depends, HTTPException

from app.application.usecase.create_character import CreateCharacterUseCase
from app.domain.model.user import User
from app.domain.repository.character_repository import CharacterRepository
from app.infrastructure.config.dependencies import get_character_repo, get_current_user
from app.presentation.router.v1_schemas import (
    CharacterCreateRequest,
    CharacterCreateResponse,
    CharacterResponse,
)

router = APIRouter(prefix="/v1/character", tags=["character"])

_ERROR_STATUS = {
    "name_too_long": 422,
    "personalities_max_2": 422,
    "invalid_color": 422,
    "invalid_personality": 422,
}


@router.post("", response_model=CharacterCreateResponse, status_code=201, summary="캐릭터 생성")
async def create_character(
    body: CharacterCreateRequest,
    user: User = Depends(get_current_user),
    character_repo: CharacterRepository = Depends(get_character_repo),
):
    try:
        character = await CreateCharacterUseCase(character_repo).execute(
            user_id=user.id,
            name=body.name,
            color=body.color,
            personalities=body.personalities,
        )
    except ValueError as e:
        raise HTTPException(status_code=_ERROR_STATUS.get(str(e), 400), detail=str(e))
    return CharacterCreateResponse(character=CharacterResponse.from_domain(character))


@router.get("", response_model=CharacterResponse, summary="내 캐릭터 조회")
async def get_character(
    user: User = Depends(get_current_user),
    character_repo: CharacterRepository = Depends(get_character_repo),
):
    character = await character_repo.find_by_user_id(user.id)
    if character is None:
        raise HTTPException(status_code=404, detail="캐릭터가 아직 없습니다.")
    return CharacterResponse.from_domain(character)
