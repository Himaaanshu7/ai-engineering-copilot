from fastapi import APIRouter
from config.settings import settings

router = APIRouter()


@router.get("/health", tags=["health"])
async def health_check() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.groq_model if settings.llm_provider == "groq" else "see config",
    }
