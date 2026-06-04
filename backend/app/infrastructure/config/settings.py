from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://aidiary:aidiary@localhost:5432/aidiary"
    clova_api_key: str = ""
    clova_base_url: str = "https://clovastudio.stream.ntruss.com/v1/openai"
    clova_model: str = "HCX-003"

    # 인증 (JWT)
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_min: int = 5
    refresh_token_ttl_days: int = 14

    # Kakao OAuth (키 발급 후 설정 — P0에서는 미사용)
    kakao_rest_api_key: str = ""
    kakao_redirect_uri: str = ""

    # CORS 허용 오리진 (콤마 구분)
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
