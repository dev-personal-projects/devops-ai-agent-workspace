from pydantic import  BaseModel, Field
from typing import Optional, List
from  datetime import datetime

class ChatMessage(BaseModel):
    """Represents a single message in the conversation"""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now)

class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str = Field(..., min_length=1, description="User's question or message")
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID for context")

class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    response: str = Field(..., description="AI agent's response")
    conversation_id: str = Field(..., description="Conversation ID for session continuity")
    sources: List[str] = Field(default=[], description="Source documents used (if any)")