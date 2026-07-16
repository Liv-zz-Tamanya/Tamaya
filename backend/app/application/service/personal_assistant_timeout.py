from dataclasses import dataclass
from typing import Literal

PersonalAssistantTimeoutStage = Literal["model", "tool", "execution"]


@dataclass(frozen=True)
class PersonalAssistantTimeoutPolicy:
    model_call_seconds: float
    tool_round_seconds: float
    execution_seconds: float

    def __post_init__(self) -> None:
        for name, value in (
            ("model_call_seconds", self.model_call_seconds),
            ("tool_round_seconds", self.tool_round_seconds),
            ("execution_seconds", self.execution_seconds),
        ):
            if value <= 0:
                raise ValueError(f"{name} must be greater than 0")


DEFAULT_PERSONAL_ASSISTANT_TIMEOUT_POLICY = PersonalAssistantTimeoutPolicy(
    model_call_seconds=25.0,
    tool_round_seconds=15.0,
    execution_seconds=45.0,
)


class PersonalAssistantTimeoutError(RuntimeError):
    def __init__(self, stage: PersonalAssistantTimeoutStage) -> None:
        self.stage = stage
        super().__init__(f"personal assistant {stage} execution timed out")
