from typing import List, Optional, Dict, Any, Union

from pydantic import BaseModel, Field, AliasChoices, ConfigDict

# ============================================================
# MODELS
# ============================================================

class MessageItem(BaseModel):
    sender: Optional[str] = None
    text: Optional[str] = None
    timestamp: Optional[Union[str, int, float]] = None


class IncomingRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    session_id: Optional[str] = Field(
        None, validation_alias=AliasChoices("sessionId", "sessionld", "session_id")
    )

    sender: Optional[str] = None
    text: Optional[str] = None
    message: Optional[Dict[str, Any]] = None

    conversation_history: List[MessageItem] = Field(
        default_factory=list,
        validation_alias=AliasChoices("conversationHistory", "conversation_history"),
    )

    metadata: Optional[Dict[str, Any]] = None


class AgentResponse(BaseModel):
    status: str
    reply: str
    finalCallback: Optional[Dict[str, Any]] = None
    finalOutput: Optional[Dict[str, Any]] = None  # compatibility
