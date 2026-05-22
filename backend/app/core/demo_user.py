"""Shared demo user for no-auth dev mode."""
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import User

DEMO_USER_ID = "a0000000-0000-4000-8000-000000000001"
DEMO_USER_EMAIL = "demo@assessment.local"
# Precomputed bcrypt for "demo" — avoids passlib/bcrypt version issues at startup
DEMO_USER_PASSWORD_HASH = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMUMYPLYBGJNFvVt9mAQh6Bq.."


async def ensure_demo_user() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == DEMO_USER_ID))
        if result.scalar_one_or_none():
            return
        db.add(
            User(
                id=DEMO_USER_ID,
                email=DEMO_USER_EMAIL,
                hashed_password=DEMO_USER_PASSWORD_HASH,
                full_name="Demo User",
                institution="Assessment Engine",
                role="teacher",
            )
        )
        await db.commit()
