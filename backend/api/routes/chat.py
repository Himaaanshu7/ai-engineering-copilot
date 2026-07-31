from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from backend.models.chat import ChatRequest, ChatResponse
from backend.services.chat_service import process_chat
from database.connection import get_db
from database import crud

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession | None = Depends(get_db),
) -> ChatResponse:
    logger.info(f"[API] POST /chat | session={request.session_id} | message={request.message[:60]}...")

    try:
        result = await process_chat(request.message, request.session_id, file_path=request.file_path)

        response_text = result["final_response"]
        intent = result["intent"]
        agent_used = result["active_agents"][0] if result.get("active_agents") else "planner"
        sources = result.get("sources", [])

        logger.info(f"[API] Response ready | intent={intent} | session={request.session_id}")

        # Persist exchange to DB (non-fatal if DB unavailable)
        if db is not None:
            try:
                await crud.save_message(db, request.session_id, "user", request.message)
                await crud.save_message(
                    db, request.session_id, "assistant", response_text,
                    intent=intent, agent_used=agent_used, sources=sources,
                )
            except Exception as exc:
                logger.warning(f"[API] DB persist failed (non-fatal): {exc}")

        return ChatResponse(
            response=response_text,
            intent=intent,
            session_id=request.session_id,
            sources=sources,
            agent_used=agent_used,
        )

    except Exception as e:
        logger.error(f"[API] Chat error | session={request.session_id} | error={e}")
        raise HTTPException(status_code=500, detail=str(e))
