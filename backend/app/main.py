from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.application.service.personal_assistant_timeout import PersonalAssistantTimeoutError
from app.infrastructure.config.database import engine
from app.presentation.router.auth_router import router as auth_router
from app.presentation.router.chat_router import router as chat_router
from app.presentation.router.coaching_router import router as coaching_router
from app.presentation.router.diary_router import router as diary_router
from app.presentation.router.game_router import router as game_router
from app.presentation.router.health_chat_router import router as health_chat_router
from app.presentation.router.insight_router import router as insight_router
from app.presentation.router.me_router import router as me_router
from app.presentation.router.settings_router import router as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # B-004: create_all 제거 — alembic upgrade head 단독 운영
    yield
    await engine.dispose()


app = FastAPI(title="AI Diary", version="0.1.0", lifespan=lifespan)

PERSONAL_ASSISTANT_TIMEOUT_DETAIL = (
    "AI 응답 처리 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요."
)


@app.exception_handler(PersonalAssistantTimeoutError)
async def handle_personal_assistant_timeout(
    request: Request,
    exc: PersonalAssistantTimeoutError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        content={"detail": PERSONAL_ASSISTANT_TIMEOUT_DETAIL},
    )


# B-001: CORS — FE(localhost:3000, 5173) + Expo Web 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:19006",  # Expo Web
        # 127.0.0.1 동등 허용 — Playwright e2e/일부 로컬 환경은 localhost 대신 127.0.0.1 사용
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(coaching_router)
app.include_router(diary_router)
app.include_router(game_router)
app.include_router(health_chat_router)
app.include_router(insight_router)
app.include_router(settings_router)
app.include_router(me_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
