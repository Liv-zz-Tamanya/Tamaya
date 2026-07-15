from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://aidiary:aidiary@localhost:5432/aidiary"
    clova_api_key: str = ""
    clova_base_url: str = "https://clovastudio.stream.ntruss.com/v1/openai"
    clova_model: str = "HCX-005"  # B-003: brief HCX-005로 통일
    clova_agent_max_tokens: int = 1024
    clova_agent_temperature: float = 0.2
    clova_agent_timeout_seconds: float = 30.0
    # DEC-022.4: Mock mode — NCP API 키 수령 전 true (디폴트 true)
    clova_mock_mode: bool = True
    # DEC-022.4: 카카오 REST API 앱 키 (사용자 발급 후 .env에 설정)
    kakao_app_key: str = ""
    # DEC-023: JWT 서명 시크릿 (프로덕션에서는 반드시 강력한 랜덤값으로 교체)
    jwt_secret: str = "CHANGE_ME_IN_PRODUCTION_USE_STRONG_RANDOM_SECRET"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
