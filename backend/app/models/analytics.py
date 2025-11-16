"""
SQLAlchemy models for analytics
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database import Base


class AnalyticsEvent(Base):
    """
    Unified event log for all analytics data.

    Stores all types of events (queries, responses, errors, uploads, tool_calls, etc.)
    with flexible JSON storage for event-specific data.

    Includes user_id for user-specific analytics tracking.
    """
    __tablename__ = "analytics_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_type = Column(String(50), nullable=False, index=True)
    session_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(255), nullable=True, index=True)  # Stytch user ID
    timestamp = Column(DateTime, server_default=func.now(), index=True)
    data = Column(JSON, default={})  # Event-specific data
    event_metadata = Column(JSON, default={})  # Performance metrics, context

    # Composite indexes for common queries
    __table_args__ = (
        Index('idx_session_event_time', 'session_id', 'event_type', 'timestamp'),
        Index('idx_user_event_time', 'user_id', 'event_type', 'timestamp'),
    )

    def __repr__(self):
        return f"<AnalyticsEvent(id={self.id}, type={self.event_type}, session={self.session_id})>"


class Session(Base):
    """
    Track conversation sessions and engagement metrics.

    Includes user_id for user-specific session analytics.
    """
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(String(255), nullable=True, index=True)  # Stytch user ID
    started_at = Column(DateTime, server_default=func.now(), index=True)
    ended_at = Column(DateTime, nullable=True)
    last_activity_at = Column(DateTime, server_default=func.now())
    message_count = Column(Integer, default=0)
    file_count = Column(Integer, default=0)
    llm_provider = Column(String(20), nullable=True)  # 'ollama' or 'claude'
    total_query_time_ms = Column(Integer, default=0)

    # Relationship to feedback
    feedback = relationship("QueryFeedback", back_populates="session", cascade="all, delete-orphan")

    # Composite index for user queries
    __table_args__ = (
        Index('idx_user_started', 'user_id', 'started_at'),
    )

    def __repr__(self):
        return f"<Session(id={self.id}, started={self.started_at}, messages={self.message_count})>"


class QueryFeedback(Base):
    """
    Store user feedback on AI responses (thumbs up/down + optional comments).

    Includes user_id for user-specific feedback analytics.
    """
    __tablename__ = "query_feedback"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(255), nullable=True, index=True)  # Stytch user ID
    message_id = Column(String(50), nullable=False)  # Frontend message ID
    query_event_id = Column(Integer, ForeignKey("analytics_events.id", ondelete="SET NULL"), nullable=True)
    rating = Column(Integer, nullable=False, index=True)  # 1 (thumbs up), -1 (thumbs down)
    comment = Column(Text, nullable=True)
    timestamp = Column(DateTime, server_default=func.now())

    # Relationship to session
    session = relationship("Session", back_populates="feedback")

    # Composite index for user feedback queries
    __table_args__ = (
        Index('idx_user_rating_time', 'user_id', 'rating', 'timestamp'),
    )

    def __repr__(self):
        rating_str = "👍" if self.rating == 1 else "👎"
        return f"<QueryFeedback(id={self.id}, rating={rating_str}, session={self.session_id})>"


class ErrorLog(Base):
    """
    Detailed error tracking and debugging information.

    Includes user_id to track errors by user.
    """
    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(36), nullable=True, index=True)
    user_id = Column(String(255), nullable=True, index=True)  # Stytch user ID
    error_type = Column(String(100), nullable=False, index=True)  # Exception class name
    error_message = Column(Text, nullable=False)
    stack_trace = Column(Text, nullable=True)
    endpoint = Column(String(200), nullable=True)
    request_data = Column(JSON, nullable=True)  # Request body, params
    timestamp = Column(DateTime, server_default=func.now(), index=True)

    # Composite indexes for common query patterns
    __table_args__ = (
        Index('idx_error_session_time', 'session_id', 'timestamp'),
        Index('idx_error_user_time', 'user_id', 'timestamp'),
    )

    def __repr__(self):
        return f"<ErrorLog(id={self.id}, type={self.error_type}, session={self.session_id})>"
