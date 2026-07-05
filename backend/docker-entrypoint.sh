#!/bin/sh
# 컨테이너 시작 시: DB 마이그레이션 → 서버 기동
set -e

echo "[entrypoint] alembic upgrade head ..."
uv run alembic upgrade head

echo "[entrypoint] starting uvicorn on :8000 ..."
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
