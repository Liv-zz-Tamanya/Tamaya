"""정성신호 추출 usecase — best-effort 오케스트레이션 (G002-2, TDD).

서비스가 추출한 dict를 QualitativeSignal 도메인 객체로 매핑해 영속한다.
CLOVA 실패(예외)나 None·잘못된 emotion은 대화 흐름을 깨지 않도록 흡수한다.
"""

from uuid import UUID, uuid4

from app.application.service.signal_extraction_service import SignalExtractionService
from app.application.usecase.extract_signals import ExtractSignalsUseCase
from app.domain.model.chat_message import ChatMessage
from app.domain.model.emotion import Emotion
from app.domain.model.qualitative_signal import QualitativeSignal
from app.domain.repository.qualitative_signal_repository import QualitativeSignalRepository


class _FakeService(SignalExtractionService):
    def __init__(self, result=None, raises: Exception | None = None) -> None:
        self._result = result
        self._raises = raises
        self.called = False

    async def extract_signal(self, messages: list[ChatMessage]) -> dict | None:
        self.called = True
        if self._raises is not None:
            raise self._raises
        return self._result


class _FakeRepo(QualitativeSignalRepository):
    def __init__(self) -> None:
        self.saved: list[tuple[str, UUID, QualitativeSignal]] = []

    async def save(self, device_id: str, session_id: UUID, signal: QualitativeSignal) -> None:
        self.saved.append((device_id, session_id, signal))

    async def find_by_date_range(self, device_id, start, end) -> list[QualitativeSignal]:
        return []


async def test_extracted_signal_is_persisted():
    service = _FakeService(
        result={
            "emotion": "happy",
            "behavior_mentions": [{"behavior": "운동", "polarity": 1}],
        }
    )
    repo = _FakeRepo()
    uc = ExtractSignalsUseCase(service, repo)
    sid = uuid4()

    await uc.execute(device_id="dev-1", session_id=sid, messages=[])

    assert len(repo.saved) == 1
    device_id, session_id, signal = repo.saved[0]
    assert device_id == "dev-1"
    assert session_id == sid
    assert signal.emotion == Emotion.HAPPY
    assert signal.behavior_mentions[0].behavior == "운동"
    assert signal.behavior_mentions[0].polarity == 1


async def test_none_extraction_persists_nothing():
    service = _FakeService(result=None)
    repo = _FakeRepo()
    uc = ExtractSignalsUseCase(service, repo)

    await uc.execute(device_id="dev-1", session_id=uuid4(), messages=[])

    assert repo.saved == []


async def test_service_exception_is_swallowed_best_effort():
    service = _FakeService(raises=RuntimeError("CLOVA 5xx"))
    repo = _FakeRepo()
    uc = ExtractSignalsUseCase(service, repo)

    # 예외가 호출자에게 전파되지 않아야 함(대화 흐름 보호)
    await uc.execute(device_id="dev-1", session_id=uuid4(), messages=[])

    assert service.called is True
    assert repo.saved == []


async def test_invalid_emotion_persists_nothing():
    service = _FakeService(result={"emotion": "존재하지않는감정", "behavior_mentions": []})
    repo = _FakeRepo()
    uc = ExtractSignalsUseCase(service, repo)

    await uc.execute(device_id="dev-1", session_id=uuid4(), messages=[])

    assert repo.saved == []
