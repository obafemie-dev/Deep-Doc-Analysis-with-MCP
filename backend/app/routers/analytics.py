"""
Analytics API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from ..database import get_analytics_db
from ..services.analytics_service import AnalyticsService
from ..schemas.analytics import (
    EventRequest,
    EventResponse,
    FeedbackRequest,
    FeedbackResponse,
    SessionStartRequest,
    SessionUpdateRequest,
    AnalyticsSummary
)
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix=f"{settings.API_V1_STR}/analytics",
    tags=["analytics"],
    responses={404: {"description": "Not found"}}
)


def get_analytics_service(db: AsyncSession = Depends(get_analytics_db)) -> AnalyticsService:
    """Dependency to get analytics service instance"""
    return AnalyticsService(db)


# ============================================================================
# Event Tracking Endpoints
# ============================================================================

@router.post("/event", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def track_event(
    event: EventRequest,
    analytics: AnalyticsService = Depends(get_analytics_service)
):
    """
    Track a custom analytics event from frontend.

    Events can be:
    - query: User asks a question
    - response: AI generates a response
    - upload: File uploaded
    - tool_call: MCP tool executed
    - session_start: Session begins
    - session_end: Session ends
    - clear_chat: User clears conversation
    - custom: Any other event
    """
    try:
        created_event = await analytics.log_event(
            event_type=event.event_type,
            session_id=event.session_id,
            data=event.data,
            metadata=event.metadata
        )

        return EventResponse(
            status="success",
            event_id=created_event.id,
            message=f"Event '{event.event_type}' tracked successfully"
        )

    except Exception as e:
        logger.error(f"Failed to track event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to track event"
        )


# ============================================================================
# Feedback Endpoints
# ============================================================================

@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    feedback: FeedbackRequest,
    analytics: AnalyticsService = Depends(get_analytics_service)
):
    """
    Submit user feedback on an AI response.

    Rating:
    - 1: Thumbs up (helpful)
    - -1: Thumbs down (not helpful)

    Optional comment provides more context.
    """
    try:
        created_feedback = await analytics.submit_feedback(
            session_id=feedback.session_id,
            message_id=feedback.message_id,
            rating=feedback.rating,
            query_event_id=feedback.query_event_id,
            comment=feedback.comment
        )

        return FeedbackResponse(
            status="success",
            feedback_id=created_feedback.id,
            message="Feedback submitted successfully"
        )

    except Exception as e:
        logger.error(f"Failed to submit feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback"
        )


# ============================================================================
# Session Management Endpoints
# ============================================================================

@router.post("/session/start", status_code=status.HTTP_201_CREATED)
async def start_session(
    session_request: SessionStartRequest,
    analytics: AnalyticsService = Depends(get_analytics_service)
):
    """
    Start a new analytics session.

    Should be called when user first loads the application.
    """
    try:
        # Check if session already exists
        existing_session = await analytics.get_session(session_request.session_id)

        if existing_session:
            return {
                "status": "exists",
                "session_id": session_request.session_id,
                "message": "Session already exists"
            }

        # Create new session
        await analytics.create_session(
            session_id=session_request.session_id,
            llm_provider=session_request.llm_provider
        )

        # Log session start event
        await analytics.log_event(
            event_type="session_start",
            session_id=session_request.session_id,
            data={
                "llm_provider": session_request.llm_provider
            }
        )

        return {
            "status": "created",
            "session_id": session_request.session_id,
            "message": "Session started successfully"
        }

    except Exception as e:
        logger.error(f"Failed to start session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start session"
        )


@router.post("/session/end")
async def end_session(
    session_id: str,
    analytics: AnalyticsService = Depends(get_analytics_service)
):
    """
    End an analytics session.

    Should be called when user closes the application.
    """
    try:
        await analytics.end_session(session_id)

        # Log session end event
        await analytics.log_event(
            event_type="session_end",
            session_id=session_id,
            data={}
        )

        return {
            "status": "success",
            "message": "Session ended successfully"
        }

    except Exception as e:
        logger.error(f"Failed to end session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to end session"
        )


@router.patch("/session/update")
async def update_session(
    session_update: SessionUpdateRequest,
    analytics: AnalyticsService = Depends(get_analytics_service)
):
    """
    Update session metadata (message count, file count, etc.).
    """
    try:
        updates = {}
        if session_update.message_count is not None:
            updates['message_count'] = session_update.message_count
        if session_update.file_count is not None:
            updates['file_count'] = session_update.file_count
        if session_update.total_query_time_ms is not None:
            updates['total_query_time_ms'] = session_update.total_query_time_ms

        await analytics.update_session(session_update.session_id, **updates)

        return {
            "status": "success",
            "message": "Session updated successfully"
        }

    except Exception as e:
        logger.error(f"Failed to update session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update session"
        )


# ============================================================================
# Analytics Summary Endpoints
# ============================================================================

@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    days: int = 7,
    analytics: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get analytics summary for the last N days.

    Returns:
    - Total sessions
    - Total queries and responses
    - Total errors
    - Average response time
    - Positive feedback rate
    """
    try:
        summary = await analytics.get_summary(days=days)
        return AnalyticsSummary(**summary)

    except Exception as e:
        logger.error(f"Failed to get analytics summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analytics summary"
        )


# ============================================================================
# Utility Endpoints
# ============================================================================

@router.get("/health")
async def analytics_health():
    """Health check for analytics service"""
    return {
        "status": "healthy",
        "analytics_enabled": settings.ANALYTICS_ENABLED,
        "database_url": settings.ANALYTICS_DB_URL.split("///")[0] + "///"  # Hide path
    }
