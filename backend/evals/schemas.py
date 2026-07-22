"""오프라인 평가 데이터셋의 Pydantic 스키마."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.application.usecase.personal_assistant_agent import PersonalAssistantMode


class ExpectedGuardrail(StrEnum):
    """평가자가 기대하는 가드레일의 최종 동작."""

    PASS = "PASS"
    BLOCK = "BLOCK"


class ExpectedDecision(StrEnum):
    NO_TOOL = "NO_TOOL"
    TOOL_CALL = "TOOL_CALL"


class EvalHistoryMessage(BaseModel):
    role: str
    content: str


class PersonalAssistantEvalCase(BaseModel):
    """실제 LLM 호출 없이 평가 계약을 기록하는 한 개의 데이터셋 행."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    mode: PersonalAssistantMode
    input: str
    history: list[EvalHistoryMessage] = Field(default_factory=list)
    expected_tools: list[str] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    expected_decision: ExpectedDecision | None = None
    expected_guardrail: ExpectedGuardrail
    expected_document_ids: list[str] = Field(default_factory=list)
    category: str = Field(min_length=1)
    note: str | None = None
