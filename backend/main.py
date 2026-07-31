import sys
from pathlib import Path

# Ensure project root is on the Python path when running directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from config.settings import settings
from backend.api.routes import health, chat, sessions, files, knowledge, reports
from database.connection import init_db
from rag.vectorstore import collection_stats
from rag.seed import seed as seed_knowledge_base


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"LLM provider: {settings.llm_provider} | model: {settings.groq_model}")
    await init_db()
    try:
        stats = collection_stats()
        if stats["count"] == 0:
            logger.info("Knowledge base empty — running initial seed")
            seed_knowledge_base()
        else:
            logger.info(f"Knowledge base ready | chunks={stats['count']}")
    except Exception as exc:
        logger.warning(f"Knowledge base init failed (non-fatal): {exc}")
    yield
    logger.info("Shutting down AI Engineering Copilot")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-agent AI system for Data Engineering and AI mentorship",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
