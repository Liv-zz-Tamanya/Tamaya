# Tamanya 백엔드 (FastAPI + uv). NCP VM에서 docker compose로 빌드/실행.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

# uv 캐시/링크 설정 — 빌드 안정성
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    # sentence-transformers 모델 캐시 위치 (컨테이너 내부)
    HF_HOME=/app/.hf_cache

# 1) 의존성만 먼저 설치 (레이어 캐시 — 코드만 바뀌면 재설치 안 함)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 2) 앱 코드 복사 후 프로젝트 설치
COPY . .
RUN uv sync --frozen --no-dev \
    && chmod +x docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
