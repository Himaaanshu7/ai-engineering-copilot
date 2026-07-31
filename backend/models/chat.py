from pydantic import BaseModel, Field
from typing import Optional
import uuid


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10_000, description="User's message")
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique session identifier",
    )
    file_path: Optional[str] = Field(default=None, description="Absolute path to an uploaded file for data-aware responses")
    context: Optional[dict] = Field(default=None, description="Optional extra context")


class ChatResponse(BaseModel):
    response: str = Field(..., description="Assistant's response")
    intent: str = Field(..., description="Classified intent category")
    session_id: str = Field(..., description="Session identifier")
    agent_used: str = Field(default="planner", description="Primary agent that handled the request")
    sources: list[str] = Field(default_factory=list, description="Source citations")
