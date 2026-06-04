from datetime import date
from uuid import UUID

from app.application.service.ai_chat_service import AiChatService
from app.domain.model.diary_session import DiarySession
from app.domain.repository.daily_check_repository import DailyCheckRepository
from app.domain.repository.diary_session_repository import DiarySessionRepository

MAX_TURN = 5


def _turns_to_dicts(session: DiarySession) -> list[dict]:
    return [{"role": t.role, "content": t.content} for t in session.turns]


class StartDiarySessionUseCase:
    def __init__(
        self,
        session_repo: DiarySessionRepository,
        ai: AiChatService,
        daily_check_repo: DailyCheckRepository,
    ) -> None:
        self._session_repo = session_repo
        self._ai = ai
        self._daily_check_repo = daily_check_repo

    async def execute(self, user_id: UUID, mode: str, session_date: date) -> dict:
        session = DiarySession(user_id=user_id, session_date=session_date, mode=mode)

        first_question = await self._ai.diary_next_question([], next_turn=1)
        session.add_turn(role="bot", content=first_question, turn=1)
        await self._session_repo.save(session)

        # day_memos 인계 (P0: 데일리 체크가 있으면 간단 요약, 없으면 빈 배열)
        day_memos: list[dict] = []
        check = await self._daily_check_repo.find_by_date(user_id, session_date)
        if check and check.done_count > 0:
            day_memos.append(
                {
                    "id": str(check.id),
                    "text": f"오늘 데일리 체크 {check.done_count}/5 완료",
                    "from": "daily-check",
                    "at": check.updated_at.isoformat(),
                }
            )

        return {
            "session_id": session.id,
            "day_memos": day_memos,
            "first_question": {"text": first_question, "hint": None},
        }


class DiarySessionTurnUseCase:
    def __init__(self, session_repo: DiarySessionRepository, ai: AiChatService) -> None:
        self._session_repo = session_repo
        self._ai = ai

    async def execute(self, user_id: UUID, session_id: UUID, turn: int, user_text: str) -> dict:
        session = await self._session_repo.find_by_id(session_id)
        if session is None or session.user_id != user_id:
            raise ValueError("세션을 찾을 수 없습니다.")

        session.add_turn(role="user", content=user_text, turn=turn)
        is_final = turn >= MAX_TURN

        next_question = None
        if not is_final:
            text = await self._ai.diary_next_question(_turns_to_dicts(session), next_turn=turn + 1)
            session.add_turn(role="bot", content=text, turn=turn + 1)
            next_question = {"text": text, "hint": None}

        await self._session_repo.save(session)
        return {
            "next_question": next_question,
            "is_final": is_final,
            "auto_save": True,
        }


class FinalizeDiarySessionUseCase:
    def __init__(self, session_repo: DiarySessionRepository, ai: AiChatService) -> None:
        self._session_repo = session_repo
        self._ai = ai

    async def execute(self, user_id: UUID, session_id: UUID) -> dict:
        session = await self._session_repo.find_by_id(session_id)
        if session is None or session.user_id != user_id:
            raise ValueError("세션을 찾을 수 없습니다.")

        result = await self._ai.finalize_diary_entry(_turns_to_dicts(session))
        session.status = "finalized"
        await self._session_repo.save(session)

        return {
            "mood_distribution": result.get("mood_distribution", []),
            "primary_emoji": result.get("primary_emoji", "🙂"),
            "keywords": result.get("keywords", []),
            "diary_body": result.get("diary_body", ""),
            "tomorrow_one_thing": result.get("tomorrow_one_thing", ""),
            "actionable_chips": ["설정", "나중에"],
        }
