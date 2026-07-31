from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from database.connection import get_db
from database import crud
from backend.models.session import SessionHistoryResponse, MessageOut

router = APIRouter()


@router.get("/sessions/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: str,
    limit: int = 200,
    db: AsyncSession | None = Depends(get_db),
) -> SessionHistoryResponse:
    if db is None:
        return SessionHistoryResponse(
            session_id=session_id, messages=[], total=0, db_available=False
        )

    messages = await crud.get_session_messages(db, session_id, limit=limit)
    logger.debug(f"[API] GET history | session={session_id[:8]} | {len(messages)} messages")

    return SessionHistoryResponse(
        session_id=session_id,
        messages=[MessageOut.model_validate(m) for m in messages],
        total=len(messages),
        db_available=True,
    )
