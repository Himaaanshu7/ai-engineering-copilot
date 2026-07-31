from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from database.models import ChatSession, Message, UploadedFile


# ── Session ──────────────────────────────────────────────────────────────────

async def get_or_create_session(db: AsyncSession, session_id: str) -> ChatSession:
    result = await db.execute(
        select(ChatSession).where(ChatSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        session = ChatSession(session_id=session_id)
        db.add(session)
        await db.flush()
    return session


# ── Messages ─────────────────────────────────────────────────────────────────

async def save_message(
    db: AsyncSession,
    session_id: str,
    role: str,
    content: str,
    intent: str | None = None,
    agent_used: str | None = None,
    sources: list | None = None,
) -> Message:
    await get_or_create_session(db, session_id)

    msg = Message(
        session_id=session_id,
        role=role,
        content=content,
        intent=intent,
        agent_used=agent_used,
        sources=sources or [],
    )
    db.add(msg)

    await db.execute(
        update(ChatSession)
        .where(ChatSession.session_id == session_id)
        .values(message_count=ChatSession.message_count + 1)
    )
    return msg


async def get_session_messages(
    db: AsyncSession, session_id: str, limit: int = 200
) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
        .limit(limit)
    )
    return list(result.scalars().all())


# ── Files ─────────────────────────────────────────────────────────────────────

async def save_uploaded_file(
    db: AsyncSession,
    session_id: str | None,
    filename: str,
    original_filename: str,
    file_type: str,
    file_path: str,
    size_bytes: int,
) -> UploadedFile:
    record = UploadedFile(
        session_id=session_id,
        filename=filename,
        original_filename=original_filename,
        file_type=file_type,
        file_path=file_path,
        size_bytes=size_bytes,
    )
    db.add(record)
    return record
