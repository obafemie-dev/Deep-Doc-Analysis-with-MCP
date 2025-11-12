from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ChatMessage(BaseModel):
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    file_path: Optional[str] = Field(None, description="Path to uploaded Excel file")
    conversation_history: List[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str = Field(..., description="Assistant response")
    timestamp: datetime = Field(default_factory=datetime.now)
    tool_calls: Optional[List[Dict[str, Any]]] = None


class FileUploadResponse(BaseModel):
    filename: str
    file_path: str
    size: int
    upload_time: datetime = Field(default_factory=datetime.now)


class AnalysisResult(BaseModel):
    analysis_type: str
    result: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
