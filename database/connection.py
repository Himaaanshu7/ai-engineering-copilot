from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from loguru import logger

from config.settings import settings


class Base(DeclarativeBase):
    pass


# Module-level singletons — None until init_db() succeeds
_engine = None
_AsyncSessionFactory: async_sessionmaker | None = None


async def init_db() -> bool:
    """
    Create the async engine, run create_all, and return True on success.
    Returns False (and logs a warning) if Postgres is unreachable — the app
    continues to run without persistence in that case.
    """
    global _engine, _AsyncSessionFactory

    url = settings.postgres_url
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    try:
        _engine = create_async_engine(
            url,
            pool_size=settings.postgres_pool_size,
            max_overflow=5,
            echo=settings.debug,
            pool_pre_ping=True,
        )
        _AsyncSessionFactory = async_sessionmaker(
            _engine, expire_on_commit=False, class_=AsyncSession
        )

        # Import models here so Base.metadata is populated before create_all
        from database import models  # noqa: F401

        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("PostgreSQL connected — tables ready")
        return True

    except Exception as exc:
        logger.warning(
            f"PostgreSQL unavailable ({exc}). Chat works but history won't be persisted. "
            "Start Postgres with: docker compose -f docker/docker-compose.yml up postgres -d"
        )
        _engine = None
        _AsyncSessionFactory = None
        return False


async def get_db() -> AsyncGenerator[AsyncSession | None, None]:
    """FastAPI dependency. Yields None when the DB is unavailable."""
    if _AsyncSessionFactory is None:
        yield None
        return

    async with _AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
