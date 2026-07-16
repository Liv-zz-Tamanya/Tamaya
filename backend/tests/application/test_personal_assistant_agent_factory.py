from uuid import UUID, uuid4

from langchain_core.messages import AIMessage, HumanMessage

from app.application.service.diary_chat_prompt import DiaryConversationContext
from app.application.service.personal_assistant_timeout import PersonalAssistantTimeoutPolicy
from app.application.service.tool_calling_chat_model import ToolCallingChatModel
from app.application.usecase.personal_assistant_agent import PersonalAssistantMode
from app.application.usecase.personal_assistant_agent_factory import PersonalAssistantAgentFactory


class _FakeToolCallingModel(ToolCallingChatModel):
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def ainvoke(self, messages, tools) -> AIMessage:
        self.calls.append({"messages": list(messages), "tools": list(tools)})
        return AIMessage(content="응답")


class _FakeDiaryQuery:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def search_similar(
        self,
        device_id: str,
        query: str,
        exclude_session_id: UUID | None = None,
        limit: int = 5,
    ) -> list:
        self.calls.append(
            {
                "device_id": device_id,
                "query": query,
                "exclude_session_id": exclude_session_id,
                "limit": limit,
            }
        )
        return []


class _FakeHealthQuery:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def search_similar(self, device_id: str, query: str, limit: int = 5) -> list:
        self.calls.append({"device_id": device_id, "query": query, "limit": limit})
        return []


def _factory(model: _FakeToolCallingModel | None = None) -> PersonalAssistantAgentFactory:
    return PersonalAssistantAgentFactory(
        model or _FakeToolCallingModel(),
        _FakeDiaryQuery(),
        _FakeHealthQuery(),
    )


async def test_factory_keeps_diary_tool_scope():
    model = _FakeToolCallingModel()
    factory = _factory(model)

    agent = factory.create(device_id="dev-a", session_id=uuid4(), mode=PersonalAssistantMode.DIARY)
    await agent.run(
        messages=[HumanMessage(content="지난 기록 알려줘")],
        mode=PersonalAssistantMode.DIARY,
        diary_context=DiaryConversationContext(
            max_turns=5,
            current_user_turn=1,
            suggest_finalize=False,
        ),
    )

    assert [tool.name for tool in model.calls[0]["tools"]] == [
        "search_diary_memories",
        "search_health_records",
    ]


async def test_factory_limits_health_tool_scope_to_health_records():
    model = _FakeToolCallingModel()
    factory = _factory(model)

    agent = factory.create(device_id="dev-a", session_id=uuid4(), mode=PersonalAssistantMode.HEALTH)
    await agent.run(
        messages=[HumanMessage(content="걸음 수 알려줘")],
        mode=PersonalAssistantMode.HEALTH,
    )

    assert [tool.name for tool in model.calls[0]["tools"]] == ["search_health_records"]


async def test_factory_uses_empty_tool_scope_for_coaching():
    model = _FakeToolCallingModel()
    factory = _factory(model)

    agent = factory.create(
        device_id="dev-a",
        session_id=uuid4(),
        mode=PersonalAssistantMode.COACHING,
    )
    await agent.run(
        messages=[HumanMessage(content="오늘 너무 지쳤어")],
        mode=PersonalAssistantMode.COACHING,
        coaching_context={"persona": None},
    )

    assert model.calls[0]["tools"] == []


def test_factory_creates_request_scoped_tool_objects():
    factory = _factory()
    first_session_id = uuid4()
    second_session_id = uuid4()

    first = factory.create(
        device_id="dev-a",
        session_id=first_session_id,
        mode=PersonalAssistantMode.HEALTH,
    )
    second = factory.create(
        device_id="dev-b",
        session_id=second_session_id,
        mode=PersonalAssistantMode.HEALTH,
    )

    assert first is not second
    assert first._tools[0] is not second._tools[0]
    assert first._tools[0].name == "search_health_records"
    assert second._tools[0].name == "search_health_records"


def test_factory_passes_timeout_policy_to_each_agent():
    policy = PersonalAssistantTimeoutPolicy(20, 10, 30)
    factory = PersonalAssistantAgentFactory(
        _FakeToolCallingModel(),
        _FakeDiaryQuery(),
        _FakeHealthQuery(),
        policy,
    )

    agent = factory.create(device_id="dev-a", session_id=uuid4(), mode=PersonalAssistantMode.HEALTH)

    assert agent._timeout_policy is policy
