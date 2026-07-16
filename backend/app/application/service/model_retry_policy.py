from dataclasses import dataclass


@dataclass(frozen=True)
class ModelRetryPolicy:
    max_attempts: int = 2
    initial_backoff_seconds: float = 0.5
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 2.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.initial_backoff_seconds < 0:
            raise ValueError("initial_backoff_seconds must be at least 0")
        if self.backoff_multiplier < 1:
            raise ValueError("backoff_multiplier must be at least 1")
        if self.max_backoff_seconds < self.initial_backoff_seconds:
            raise ValueError("max_backoff_seconds must be at least initial_backoff_seconds")

    def backoff_seconds(self, retry_index: int) -> float:
        if retry_index < 1:
            raise ValueError("retry_index must be at least 1")
        return min(
            self.initial_backoff_seconds * self.backoff_multiplier ** (retry_index - 1),
            self.max_backoff_seconds,
        )


DEFAULT_MODEL_RETRY_POLICY = ModelRetryPolicy()
