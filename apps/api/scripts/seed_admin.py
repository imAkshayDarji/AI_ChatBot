"""Idempotent admin seed: creates owner if missing (async)."""

import asyncio
import os
import secrets
import string

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models.user import User
from app.db.session import async_session_factory


def _generate_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def seed_admin() -> None:
    settings = get_settings()
    email = os.environ.get("ADMIN_EMAIL", "admin@krystaltattoo.com").strip().lower()
    env_password = os.environ.get("ADMIN_PASSWORD")
    if env_password is not None and len(env_password) < 8:
        raise ValueError("ADMIN_PASSWORD must be at least 8 characters")

    password = env_password if env_password is not None else _generate_password()
    print_once = env_password is None

    async with async_session_factory() as session:
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is not None:
            print(f"Seed skipped: user already exists for {email}")
            return

        user = User(
            email=email,
            password_hash=hash_password(password),
            role="owner",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        print(f"Created owner user: {email}")
        if print_once:
            print("Generated password (save securely; not shown again):")
            print(password)


def main() -> None:
    asyncio.run(seed_admin())


if __name__ == "__main__":
    main()
