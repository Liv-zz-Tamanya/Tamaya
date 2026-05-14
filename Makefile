.PHONY: help up down be fe migrate seed dev clean

help:
	@echo "  make up        # Postgres 컨테이너 기동"
	@echo "  make down      # Postgres 컨테이너 중지"
	@echo "  make be        # 백엔드 서버 (포트 8000)"
	@echo "  make fe        # 프론트 서버 (포트 5173)"
	@echo "  make migrate   # alembic upgrade head"
	@echo "  make dev       # postgres + be + fe 동시 (tmux 또는 별도 터미널 권장)"
	@echo "  make clean     # 컨테이너·데이터 초기화"

up:
	docker compose up -d postgres

down:
	docker compose stop postgres

be:
	cd backend && uvicorn app.main:app --reload --port 8000

fe:
	cd frontend && npm run dev

migrate:
	cd backend && alembic upgrade head

dev: up
	@echo "Postgres 띄움. 별도 터미널에서:"
	@echo "  터미널 1: make be"
	@echo "  터미널 2: make fe"

clean:
	docker compose down -v
	@echo "Postgres 데이터 초기화 완료"
