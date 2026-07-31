from datetime import datetime
from pydantic import BaseModel


class MessageOut(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    intent: str | None = None
    agent_used: str | None = None
    sources: list[str] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionHistoryResponse(BaseModel):
    session_id: str
    messages: list[MessageOut]
    total: int
    db_available: bool = True
