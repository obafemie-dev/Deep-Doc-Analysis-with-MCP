"""
Analytics service for event tracking and analytics operations
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, or_
from datetime import datetime, timedelta
import logging

from ..models.analytics import AnalyticsEvent, Session, QueryFeedback, ErrorLog

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service class for analytics operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Event Tracking
    # ========================================================================

    async def log_event(
        self,
        event_type: str,
        session_id: str,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AnalyticsEvent:
        """
        Log an analytics event.

        Args:
            event_type: Type of event (query, response, error, etc.)
            session_id: Session UUID
            data: Event-specific data
            metadata: Performance metrics, context

        Returns:
            Created AnalyticsEvent
        """
        event = AnalyticsEvent(
            event_type=event_type,
            session_id=session_id,
            data=data or {},
            metadata=metadata or {}
        )
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)

        logger.info(f"Event logged: {event_type} for session {session_id}")
        return event

    async def track_query(
        self,
        session_id: str,
        query_text: str,
        file_path: Optional[str],
        conversation_turn: int,
        llm_provider: str
    ) -> AnalyticsEvent:
        """Track a user query"""
        return await self.log_event(
            event_type="query",
            session_id=session_id,
            data={
                "query_text": query_text,
                "file_path": file_path,
                "conversation_turn": conversation_turn,
                "llm_provider": llm_provider
            }
        )

    async def track_response(
        self,
        session_id: str,
        query_id: Optional[int],
        response_text: str,
        tool_calls: List[Dict[str, Any]],
        duration_ms: int,
        success: bool,
        streaming: bool = True
    ) -> AnalyticsEvent:
        """Track an AI response"""
        return await self.log_event(
            event_type="response",
            session_id=session_id,
            data={
                "query_id": query_id,
                "response_text": response_text,
                "response_length": len(response_text),
                "tool_calls": tool_calls,
                "tool_count": len(tool_calls),
                "success": success,
                "streaming": streaming
            },
            metadata={
                "total_duration_ms": duration_ms,
                "tokens_estimated": len(response_text) // 4  # Rough estimate
            }
        )

    async def track_tool_call(
        self,
        session_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        duration_ms: int,
        success: bool,
        error: Optional[str] = None
    ) -> AnalyticsEvent:
        """Track individual tool execution"""
        return await self.log_event(
            event_type="tool_call",
            session_id=session_id,
            data={
                "tool_name": tool_name,
                "parameters": parameters,
                "success": success,
                "error": error
            },
            metadata={
                "duration_ms": duration_ms
            }
        )

    async def track_file_upload(
        self,
        session_id: str,
        filename: str,
        file_size: int,
        file_type: str,
        processing_time_ms: int
    ) -> AnalyticsEvent:
        """Track file upload"""
        return await self.log_event(
            event_type="upload",
            session_id=session_id,
            data={
                "filename": filename,
                "file_size": file_size,
                "file_type": file_type
            },
            metadata={
                "processing_time_ms": processing_time_ms
            }
        )

    # ========================================================================
    # Session Management
    # ========================================================================

    async def create_session(
        self,
        session_id: str,
        llm_provider: Optional[str] = None
    ) -> Session:
        """Create a new session"""
        session = Session(
            id=session_id,
            llm_provider=llm_provider
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)

        logger.info(f"Session created: {session_id}")
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        stmt = select(Session).where(Session.id == session_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_session(
        self,
        session_id: str,
        **updates
    ):
        """Update session data"""
        # Always update last_activity_at
        updates['last_activity_at'] = datetime.utcnow()

        stmt = (
            update(Session)
            .where(Session.id == session_id)
            .values(**updates)
        )
        await self.db.execute(stmt)

    async def end_session(self, session_id: str):
        """Mark session as ended"""
        await self.update_session(
            session_id,
            ended_at=datetime.utcnow()
        )

    async def increment_message_count(self, session_id: str):
        """Increment session message count"""
        stmt = (
            update(Session)
            .where(Session.id == session_id)
            .values(
                message_count=Session.message_count + 1,
                last_activity_at=datetime.utcnow()
            )
        )
        await self.db.execute(stmt)

    async def increment_file_count(self, session_id: str):
        """Increment session file count"""
        stmt = (
            update(Session)
            .where(Session.id == session_id)
            .values(
                file_count=Session.file_count + 1,
                last_activity_at=datetime.utcnow()
            )
        )
        await self.db.execute(stmt)

    # ========================================================================
    # Feedback Management
    # ========================================================================

    async def submit_feedback(
        self,
        session_id: str,
        message_id: str,
        rating: int,
        query_event_id: Optional[int] = None,
        comment: Optional[str] = None
    ) -> QueryFeedback:
        """Submit user feedback"""
        feedback = QueryFeedback(
            session_id=session_id,
            message_id=message_id,
            query_event_id=query_event_id,
            rating=rating,
            comment=comment
        )
        self.db.add(feedback)
        await self.db.flush()
        await self.db.refresh(feedback)

        logger.info(f"Feedback submitted: {rating} for message {message_id}")
        return feedback

    async def get_feedback_by_message(self, message_id: str) -> Optional[QueryFeedback]:
        """Get feedback for a specific message"""
        stmt = select(QueryFeedback).where(QueryFeedback.message_id == message_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ========================================================================
    # Error Logging
    # ========================================================================

    async def log_error(
        self,
        session_id: Optional[str],
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        endpoint: Optional[str] = None,
        request_data: Optional[Dict[str, Any]] = None
    ) -> ErrorLog:
        """Log an error"""
        error_log = ErrorLog(
            session_id=session_id,
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            endpoint=endpoint,
            request_data=request_data
        )
        self.db.add(error_log)
        await self.db.flush()
        await self.db.refresh(error_log)

        logger.error(f"Error logged: {error_type} - {error_message}")
        return error_log

    # ========================================================================
    # Analytics Queries
    # ========================================================================

    async def get_events_by_session(
        self,
        session_id: str,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[AnalyticsEvent]:
        """Get events for a session"""
        stmt = select(AnalyticsEvent).where(AnalyticsEvent.session_id == session_id)

        if event_type:
            stmt = stmt.where(AnalyticsEvent.event_type == event_type)

        stmt = stmt.order_by(AnalyticsEvent.timestamp.desc()).limit(limit)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Get analytics summary for the last N days.

        Returns counts, averages, and rates.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Total sessions
        sessions_stmt = select(func.count(Session.id)).where(
            Session.started_at >= cutoff_date
        )
        total_sessions = await self.db.scalar(sessions_stmt) or 0

        # Total queries
        queries_stmt = select(func.count(AnalyticsEvent.id)).where(
            and_(
                AnalyticsEvent.event_type == 'query',
                AnalyticsEvent.timestamp >= cutoff_date
            )
        )
        total_queries = await self.db.scalar(queries_stmt) or 0

        # Total responses
        responses_stmt = select(func.count(AnalyticsEvent.id)).where(
            and_(
                AnalyticsEvent.event_type == 'response',
                AnalyticsEvent.timestamp >= cutoff_date
            )
        )
        total_responses = await self.db.scalar(responses_stmt) or 0

        # Total errors
        errors_stmt = select(func.count(ErrorLog.id)).where(
            ErrorLog.timestamp >= cutoff_date
        )
        total_errors = await self.db.scalar(errors_stmt) or 0

        # Average response time
        avg_time_stmt = select(
            func.avg(
                func.cast(
                    func.json_extract(AnalyticsEvent.metadata, '$.total_duration_ms'),
                    Integer
                )
            )
        ).where(
            and_(
                AnalyticsEvent.event_type == 'response',
                AnalyticsEvent.timestamp >= cutoff_date
            )
        )
        avg_response_time = await self.db.scalar(avg_time_stmt)

        # Positive feedback rate
        total_feedback_stmt = select(func.count(QueryFeedback.id)).where(
            QueryFeedback.timestamp >= cutoff_date
        )
        total_feedback = await self.db.scalar(total_feedback_stmt) or 0

        positive_feedback_stmt = select(func.count(QueryFeedback.id)).where(
            and_(
                QueryFeedback.rating == 1,
                QueryFeedback.timestamp >= cutoff_date
            )
        )
        positive_feedback = await self.db.scalar(positive_feedback_stmt) or 0

        positive_rate = (positive_feedback / total_feedback) if total_feedback > 0 else None

        return {
            "total_sessions": total_sessions,
            "total_queries": total_queries,
            "total_responses": total_responses,
            "total_errors": total_errors,
            "average_response_time_ms": round(avg_response_time, 2) if avg_response_time else None,
            "positive_feedback_rate": round(positive_rate, 3) if positive_rate is not None else None,
            "total_feedback": total_feedback,
            "time_period": f"last_{days}_days"
        }

    # ========================================================================
    # Data Cleanup
    # ========================================================================

    async def cleanup_old_events(self, days: int = 90) -> int:
        """
        Delete events older than specified days.

        Returns number of deleted events.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        from sqlalchemy import delete

        stmt = delete(AnalyticsEvent).where(
            AnalyticsEvent.timestamp < cutoff_date
        )
        result = await self.db.execute(stmt)

        logger.info(f"Cleaned up {result.rowcount} old events")
        return result.rowcount
