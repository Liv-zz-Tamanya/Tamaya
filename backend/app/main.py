from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infrastructure.config.database import engine
from app.infrastructure.config.settings import settings
from app.infrastructure.persistence.models import Base
from app.presentation.router.auth_router import router as auth_router
from app.presentation.router.character_router import router as character_router
from app.presentation.router.daily_check_router import router as daily_check_router
from app.presentation.router.diary_session_router import router as diary_session_router
from app.presentation.router.diary_v1_router import router as diary_v1_router
from app.presentation.router.health_chat_router import router as health_chat_router
from app.presentation.router.onboarding_router import router as onboarding_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Tamaya (이음:me)", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# F1·F4·F5 (P0)
app.include_router(auth_router)
app.include_router(onboarding_router)
app.include_router(character_router)
app.include_router(daily_check_router)
app.include_router(diary_session_router)
app.include_router(diary_v1_router)

# 기존 헬스 챗 (유지)
app.include_router(health_chat_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
