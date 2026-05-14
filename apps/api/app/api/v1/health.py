from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import engine as async_engine

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    db_status = "connected"
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return {"status": "ok", "version": "1.0.0", "db": db_status}
