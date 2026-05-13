from fastapi import APIRouter

from app.api.v1.admin_auth import router as admin_auth_router
from app.api.v1.admin_knowledge import router as admin_knowledge_router
from app.api.v1.chat import router as chat_router
from app.api.v1.health import router as health_router
from app.api.v1.leads import router as leads_router

router = APIRouter(prefix="/api/v1")
router.include_router(health_router, tags=["health"])
router.include_router(admin_auth_router)
router.include_router(admin_knowledge_router)
router.include_router(chat_router)
router.include_router(leads_router)
