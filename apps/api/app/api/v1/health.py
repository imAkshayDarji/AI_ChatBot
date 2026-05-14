from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    db_status = "not_tested"
    try:
        from sqlalchemy import text

        from app.db.session import engine as async_engine

        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "error"

    return {"status": "ok", "version": "1.0.0", "db": db_status}
