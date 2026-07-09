from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

LOCAL_DEV_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:19006",  # Expo Web
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

# Vite --host, .local 호스트명, 사설망 IP로 여는 로컬 개발 브라우저를 허용한다.
LOCAL_DEV_ORIGIN_REGEX = (
    r"^https?://("
    r"localhost"
    r"|127\.0\.0\.1"
    r"|[A-Za-z0-9-]+\.local"
    r"|10(?:\.\d{1,3}){3}"
    r"|192\.168(?:\.\d{1,3}){2}"
    r"|172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2}"
    r")(?::\d+)?$"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # B-004: create_all 제거 — alembic upgrade head 단독 운영
    yield
    await engine.dispose()


app = FastAPI(title="AI Diary", version="0.1.0", lifespan=lifespan)

# B-001: CORS — FE(localhost:3000, 5173) + Expo Web 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=LOCAL_DEV_ORIGINS,
    allow_origin_regex=LOCAL_DEV_ORIGIN_REGEX,
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
