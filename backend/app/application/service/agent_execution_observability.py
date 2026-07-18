import contextvars
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol
from uuid import uuid4


class AgentTerminationReason(StrEnum):
    COMPLETED = "completed"
    INPUT_GUARDRAIL_BLOCKED = "input_guardrail_blocked"
    OUTPUT_GUARDRAIL_BLOCKED = "output_guardrail_blocked"
    ITERATION_LIMIT = "iteration_limit"
    TIMEOUT = "timeout"
    PROVIDER_ERROR = "provider_error"
    TOOL_ERROR = "tool_error"
    CANCELLED = "cancelled"
    UNEXPECTED_ERROR = "unexpected_error"


@dataclass(frozen=True)
class AgentExecutionRecord:
    trace_id: str
    mode: str
    termination_reason: AgentTerminationReason
    guardrail_verdict: str | None
    llm_calls: int
    tool_rounds: int
    tool_names: tuple[str, ...]
    model_duration_ms: int
    tool_duration_ms: int
    execution_duration_ms: int
    retry_attempts: int
    provider_error_category: str | None
    timeout_stage: str | None
    retrieval_result_count: int | None
    diary_retrieval_result_count: int | None
    health_retrieval_result_count: int | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None


class AgentExecutionRecorder(Protocol):
    def record(self, record: AgentExecutionRecord) -> None: ...


class NullAgentExecutionRecorder:
    def record(self, record: AgentExecutionRecord) -> None:
        return None


@dataclass
class AgentExecutionTrace:
    mode: str
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    guardrail_verdict: str | None = None
    termination_reason: AgentTerminationReason = AgentTerminationReason.COMPLETED
    llm_calls: int = 0
    tool_rounds: int = 0
    tool_names: list[str] = field(default_factory=list)
    model_duration_seconds: float = 0.0
    tool_duration_seconds: float = 0.0
    retry_attempts: int = 0
    provider_error_category: str | None = None
    timeout_stage: str | None = None
    diary_retrieval_result_count: int | None = None
    health_retrieval_result_count: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    _tool_round_in_progress: bool = False
    _started_at: float = field(default_factory=time.monotonic)

    def record_model_attempt(self) -> None:
        self.llm_calls += 1

    def record_retry_attempt(self) -> None:
        self.retry_attempts += 1

    def add_model_duration(self, duration_seconds: float) -> None:
        self.model_duration_seconds += duration_seconds

    def start_tool_round(self, tool_names: list[str]) -> None:
        self.tool_rounds += 1
        self.tool_names.extend(tool_names)
        self._tool_round_in_progress = True

    def complete_tool_round(self, duration_seconds: float) -> None:
        self.tool_duration_seconds += duration_seconds
        self._tool_round_in_progress = False

    def add_failed_tool_duration(self, duration_seconds: float) -> None:
        self.tool_duration_seconds += duration_seconds

    @property
    def tool_round_in_progress(self) -> bool:
        return self._tool_round_in_progress

    def record_guardrail_verdict(self, verdict: str) -> None:
        self.guardrail_verdict = verdict

    def record_provider_error(self, category: str) -> None:
        self.provider_error_category = category

    def record_timeout(self, stage: str) -> None:
        self.timeout_stage = stage

    def record_retrieval_result(self, tool_name: str, count: int) -> None:
        if tool_name == "search_diary_memories":
            self.diary_retrieval_result_count = (self.diary_retrieval_result_count or 0) + count
        elif tool_name == "search_health_records":
            self.health_retrieval_result_count = (self.health_retrieval_result_count or 0) + count

    def record_token_usage(self, usage: dict[str, int] | None) -> None:
        if usage is None:
            return
        self.input_tokens = (self.input_tokens or 0) + usage.get("input_tokens", 0)
        self.output_tokens = (self.output_tokens or 0) + usage.get("output_tokens", 0)
        self.total_tokens = (self.total_tokens or 0) + usage.get("total_tokens", 0)

    def to_record(self) -> AgentExecutionRecord:
        return AgentExecutionRecord(
            trace_id=self.trace_id,
            mode=self.mode,
            termination_reason=self.termination_reason,
            guardrail_verdict=self.guardrail_verdict,
            llm_calls=self.llm_calls,
            tool_rounds=self.tool_rounds,
            tool_names=tuple(self.tool_names),
            model_duration_ms=_duration_ms(self.model_duration_seconds),
            tool_duration_ms=_duration_ms(self.tool_duration_seconds),
            execution_duration_ms=_duration_ms(time.monotonic() - self._started_at),
            retry_attempts=self.retry_attempts,
            provider_error_category=self.provider_error_category,
            timeout_stage=self.timeout_stage,
            retrieval_result_count=_retrieval_result_count(
                self.diary_retrieval_result_count,
                self.health_retrieval_result_count,
            ),
            diary_retrieval_result_count=self.diary_retrieval_result_count,
            health_retrieval_result_count=self.health_retrieval_result_count,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            total_tokens=self.total_tokens,
        )


_active_agent_execution_trace: contextvars.ContextVar[AgentExecutionTrace | None] = (
    contextvars.ContextVar("active_agent_execution_trace", default=None)
)


def activate_agent_execution_trace(trace: AgentExecutionTrace) -> contextvars.Token:
    return _active_agent_execution_trace.set(trace)


def reset_agent_execution_trace(token: contextvars.Token) -> None:
    _active_agent_execution_trace.reset(token)


def get_active_agent_execution_trace() -> AgentExecutionTrace | None:
    return _active_agent_execution_trace.get()


def _duration_ms(duration_seconds: float) -> int:
    return max(0, round(duration_seconds * 1000))


def _retrieval_result_count(diary_count: int | None, health_count: int | None) -> int | None:
    if diary_count is None and health_count is None:
        return None
    return (diary_count or 0) + (health_count or 0)
