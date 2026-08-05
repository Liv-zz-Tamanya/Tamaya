"""비밀번호 해시/검증 유틸 — bcrypt.

bcrypt는 CPU-bound(~100ms)라 async 라우트에서는 asyncio.to_thread로 감싸 호출한다.
"""

from __future__ import annotations

import asyncio

import bcrypt


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        # 잘못된 해시 포맷(레거시 잔재 등)은 불일치로 처리
        return False


async def hash_password_async(plain: str) -> str:
    return await asyncio.to_thread(hash_password, plain)


async def verify_password_async(plain: str, hashed: str) -> bool:
    return await asyncio.to_thread(verify_password, plain, hashed)
