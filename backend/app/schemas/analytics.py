"""
Pydantic schemas for analytics API validation
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime


class EventRequest(BaseModel):
    """Request schema for tracking custom events"""
    event_type: str = Field(..., min_length=1, max_length=50, description="Type of event")
    session_id: str = Field(..., min_length=36, max_length=36, description="Session UUID")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Event-specific data")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Performance metrics, context")

    @validator('event_type')
    def validate_event_type(cls, v):
        """Validate event type against allowed values"""
        allowed_types = [
            'query', 'response', 'error', 'upload', 'tool_call',
            'feedback', 'session_start', 'session_end', 'clear_chat',
            'file_delete', 'custom'
        ]
        if v not in allowed_types:
            raise ValueError(f'Invalid event type. Must be one of {allowed_types}')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "query",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "data": {
                    "query_text": "What is the average sales?",
                    "file_path": "/uploads/sales.xlsx"
                },
                "metadata": {
                    "endpoint": "/api/v1/chat/stream"
                }
            }
        }


class FeedbackRequest(BaseModel):
    """Request schema for user feedback on AI responses"""
    message_id: str = Field(..., min_length=1, description="Frontend message ID")
    session_id: str = Field(..., min_length=36, max_length=36, description="Session UUID")
    query_event_id: Optional[int] = Field(default=None, description="Reference to query event")
    rating: int = Field(..., description="Rating: 1 (thumbs up) or -1 (thumbs down)")
    comment: Optional[str] = Field(default=None, max_length=1000, description="Optional user comment")

    @validator('rating')
    def validate_rating(cls, v):
        """Validate rating is either 1 or -1"""
        if v not in [1, -1]:
            raise ValueError('Rating must be 1 (thumbs up) or -1 (thumbs down)')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "msg_123",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "query_event_id": 42,
                "rating": 1,
                "comment": "Great analysis!"
            }
        }


class SessionStartRequest(BaseModel):
    """Request schema for starting a new session"""
    session_id: str = Field(..., min_length=36, max_length=36, description="Session UUID")
    llm_provider: Optional[str] = Field(default=None, description="LLM provider (ollama or claude)")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "llm_provider": "claude"
            }
        }


class SessionUpdateRequest(BaseModel):
    """Request schema for updating session data"""
    session_id: str = Field(..., min_length=36, max_length=36, description="Session UUID")
    message_count: Optional[int] = Field(default=None, description="Total message count")
    file_count: Optional[int] = Field(default=None, description="Total file count")
    total_query_time_ms: Optional[int] = Field(default=None, description="Total query time in ms")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "message_count": 10,
                "file_count": 2,
                "total_query_time_ms": 45000
            }
        }


class EventResponse(BaseModel):
    """Response schema for event tracking"""
    status: str = Field(default="success", description="Status of operation")
    event_id: Optional[int] = Field(default=None, description="ID of created event")
    message: Optional[str] = Field(default=None, description="Status message")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "event_id": 12345,
                "message": "Event tracked successfully"
            }
        }


class FeedbackResponse(BaseModel):
    """Response schema for feedback submission"""
    status: str = Field(default="success", description="Status of operation")
    feedback_id: Optional[int] = Field(default=None, description="ID of created feedback")
    message: Optional[str] = Field(default=None, description="Status message")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "feedback_id": 67,
                "message": "Feedback submitted successfully"
            }
        }


class AnalyticsSummary(BaseModel):
    """Response schema for analytics summary"""
    total_sessions: int
    total_queries: int
    total_responses: int
    total_errors: int
    average_response_time_ms: Optional[float]
    positive_feedback_rate: Optional[float]
    time_period: str

    class Config:
        json_schema_extra = {
            "example": {
                "total_sessions": 150,
                "total_queries": 1250,
                "total_responses": 1200,
                "total_errors": 50,
                "average_response_time_ms": 2345.67,
                "positive_feedback_rate": 0.85,
                "time_period": "last_7_days"
            }
        }
