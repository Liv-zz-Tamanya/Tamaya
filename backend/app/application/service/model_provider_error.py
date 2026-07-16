from enum import StrEnum


class ModelProviderErrorCategory(StrEnum):
    RATE_LIMIT = "rate_limit"
    UNAVAILABLE = "unavailable"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    INVALID_REQUEST = "invalid_request"
    UNKNOWN = "unknown"


class ModelProviderError(RuntimeError):
    def __init__(
        self,
        *,
        category: ModelProviderErrorCategory,
        retryable: bool,
        status_code: int | None = None,
    ) -> None:
        self.category = category
        self.retryable = retryable
        self.status_code = status_code
        super().__init__(f"model provider error: {category.value}")
