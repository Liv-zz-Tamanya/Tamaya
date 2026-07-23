from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://aidiary:aidiary@localhost:5432/aidiary"
    # 평가 전용 DB — 운영 DB와 같은 postgres 인스턴스의 별도 database.
    # evals/seed_fixtures가 DB명에 "eval"이 없으면 실행을 거부한다(운영 오염 방지).
    eval_database_url: str = "postgresql+asyncpg://aidiary:aidiary@localhost:5432/aidiary_eval"
    clova_api_key: str = ""
    clova_base_url: str = "https://clovastudio.stream.ntruss.com/v1/openai"
    clova_model: str = "HCX-005"  # B-003: brief HCX-005로 통일
    clova_agent_max_tokens: int = 1024
    clova_agent_temperature: float = 0.2
    clova_agent_timeout_seconds: float = 30.0
    personal_assistant_model_call_timeout_seconds: float = Field(default=25.0, gt=0)
    personal_assistant_tool_round_timeout_seconds: float = Field(default=15.0, gt=0)
    personal_assistant_execution_timeout_seconds: float = Field(default=45.0, gt=0)
    personal_assistant_model_retry_max_attempts: int = Field(default=2, ge=1)
    personal_assistant_model_retry_initial_backoff_seconds: float = Field(default=0.5, ge=0)
    personal_assistant_model_retry_backoff_multiplier: float = Field(default=2.0, ge=1)
    personal_assistant_model_retry_max_backoff_seconds: float = Field(default=2.0, ge=0)
    # DEC-022.4: Mock mode — NCP API 키 수령 전 true (디폴트 true)
    clova_mock_mode: bool = True
    # DEC-022.4: 카카오 REST API 앱 키 (사용자 발급 후 .env에 설정)
    kakao_app_key: str = ""
    # DEC-023: JWT 서명 시크릿 (프로덕션에서는 반드시 강력한 랜덤값으로 교체)
    jwt_secret: str = "CHANGE_ME_IN_PRODUCTION_USE_STRONG_RANDOM_SECRET"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def _validate_model_retry_backoff(self) -> "Settings":
        if (
            self.personal_assistant_model_retry_max_backoff_seconds
            < self.personal_assistant_model_retry_initial_backoff_seconds
        ):
            raise ValueError(
                "personal_assistant_model_retry_max_backoff_seconds must be at least "
                "personal_assistant_model_retry_initial_backoff_seconds"
            )
        return self


settings = Settings()
