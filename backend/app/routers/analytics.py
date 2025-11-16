"""
Analytics API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging
import asyncio

from ..database import get_analytics_db
from ..services.analytics_service import AnalyticsService
from ..schemas.analytics import (
    EventRequest,
    EventResponse,
    FeedbackRequest,
    FeedbackResponse,
    SessionStartRequest,
    SessionEndRequest,
    SessionUpdateRequest,
    AnalyticsSummary
)
from ..config import settings
from ..routers.auth import get_current_user
from ..models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix=f"{settings.API_V1_STR}/analytics",
    tags=["analytics"],
    responses={404: {"description": "Not found"}}
)


def get_analytics_service(db: AsyncSession = Depends(get_analytics_db)) -> AnalyticsService:
    """Dependency to get analytics service instance"""
    return AnalyticsService(db)


async def get_current_user_optional(
    stytch_session: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_analytics_db)
) -> Optional[User]:
    """
    Optional authentication dependency for analytics.

    Returns User if authenticated, None if anonymous.
    Allows analytics tracking for both authenticated and anonymous users.
    """
    if not stytch_session:
        return None

    try:
        # Reuse the auth logic but catch exceptions
        return await get_current_user(stytch_session=stytch_session, db=db)
    except HTTPException:
        # Session invalid or expired, treat as anonymous
        return None
    except Exception as e:
        logger.warning(f"Error validating session for analytics: {e}")
        return None


# ============================================================================
# Event Tracking Endpoints
# ============================================================================

@router.post("/event", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def track_event(
    event: EventRequest,
    analytics: AnalyticsService = Depends(get_analytics_service),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Track a custom analytics event from frontend.

    Two-tier async logging for optimal performance:
    - Synchronous: query, response (need event_id immediately for linking)
    - Asynchronous: upload, session_start, clear_chat, etc. (fire-and-forget)

    Events can be:
    - query: User asks a question (SYNC - returns event_id)
    - response: AI generates a response (SYNC - returns event_id)
    - upload: File uploaded (ASYNC - better performance)
    - tool_call: MCP tool executed (ASYNC)
    - session_start: Session begins (ASYNC)
    - session_end: Session ends (ASYNC)
    - clear_chat: User clears conversation (ASYNC)
    - custom: Any other event (ASYNC)

    Automatically includes user_id if user is authenticated.
    """
    try:
        # Extract user_id from authenticated user (None if anonymous)
        user_id = current_user.stytch_user_id if current_user else None

        # Critical events that need event_id immediately (synchronous)
        SYNC_EVENTS = {'query', 'response'}

        if event.event_type in SYNC_EVENTS:
            # Synchronous logging - wait for completion and return event_id
            created_event = await analytics.log_event(
                event_type=event.event_type,
                session_id=event.session_id,
                user_id=user_id,
                data=event.data,
                metadata=event.metadata
            )

            return EventResponse(
                status="success",
                event_id=created_event.id,
                message=f"Event '{event.event_type}' tracked successfully"
            )
        else:
            # Asynchronous logging - fire and forget for better performance
            async def log_in_background():
                """Background task for non-critical event logging"""
                try:
                    await analytics.log_event(
                        event_type=event.event_type,
                        session_id=event.session_id,
                        user_id=user_id,
                        data=event.data,
                        metadata=event.metadata
                    )
                except Exception as e:
                    logger.error(f"Background event logging failed: {e}")

            # Create background task (non-blocking)
            asyncio.create_task(log_in_background())

            # Return immediately without waiting for DB write
            return EventResponse(
                status="success",
                event_id=None,  # No event_id for async events
                message=f"Event '{event.event_type}' queued for tracking"
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
    analytics: AnalyticsService = Depends(get_analytics_service),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Submit user feedback on an AI response.

    Rating:
    - 1: Thumbs up (helpful)
    - -1: Thumbs down (not helpful)

    Optional comment provides more context.
    Automatically includes user_id if user is authenticated.
    """
    try:
        # Extract user_id from authenticated user (None if anonymous)
        user_id = current_user.stytch_user_id if current_user else None

        created_feedback = await analytics.submit_feedback(
            session_id=feedback.session_id,
            message_id=feedback.message_id,
            rating=feedback.rating,
            user_id=user_id,  # Pass user_id for user-specific feedback tracking
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
    analytics: AnalyticsService = Depends(get_analytics_service),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Start a new analytics session.

    Should be called when user first loads the application.
    Automatically includes user_id if user is authenticated.
    """
    try:
        # Extract user_id from authenticated user (None if anonymous)
        user_id = current_user.stytch_user_id if current_user else None

        # Check if session already exists
        existing_session = await analytics.get_session(session_request.session_id)

        if existing_session:
            return {
                "status": "exists",
                "session_id": session_request.session_id,
                "message": "Session already exists"
            }

        # Create new session with user_id
        await analytics.create_session(
            session_id=session_request.session_id,
            user_id=user_id,  # Track which user owns this session
            llm_provider=session_request.llm_provider
        )

        # Log session start event with user_id
        await analytics.log_event(
            event_type="session_start",
            session_id=session_request.session_id,
            user_id=user_id,  # Include user_id in event
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
    session_end: SessionEndRequest,
    analytics: AnalyticsService = Depends(get_analytics_service),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    End an analytics session.

    Should be called when user closes the application.
    Automatically includes user_id if user is authenticated.
    Only session owner can end their session.
    """
    try:
        # Extract user_id from authenticated user (None if anonymous)
        user_id = current_user.stytch_user_id if current_user else None

        # Get session to verify existence and ownership
        session = await analytics.get_session(session_end.session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found"
            )

        # Authorization: Only session owner can end their session
        # If session has user_id, must match current user
        if session.user_id is not None and session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to end this session"
            )

        # Check if already ended (idempotency)
        if session.ended_at is not None:
            return {
                "status": "already_ended",
                "message": "Session already ended",
                "ended_at": session.ended_at.isoformat()
            }

        await analytics.end_session(session_end.session_id)

        # Log session end event with user_id
        await analytics.log_event(
            event_type="session_end",
            session_id=session_end.session_id,
            user_id=user_id,
            data={}
        )

        return {
            "status": "success",
            "message": "Session ended successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to end session {session_end.session_id}: {e}")
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
