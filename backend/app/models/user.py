"""
SQLAlchemy model for user authentication via Stytch
"""
from sqlalchemy import Column, String, DateTime, Integer, Index
from sqlalchemy.sql import func

from ..database import Base


class User(Base):
    """
    User model for storing application-specific user data.

    Authentication is handled by Stytch. This model stores metadata
    and application-specific information synchronized from Stytch.
    """
    __tablename__ = "users"

    # Primary key - Stytch user ID
    stytch_user_id = Column(String(255), primary_key=True, index=True)

    # User information (synced from Stytch)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime, nullable=True)

    # Application-specific metadata
    subscription_tier = Column(String(50), default="free", nullable=False)
    file_upload_quota = Column(Integer, default=100, nullable=False)  # Number of files allowed

    # Composite index for common queries
    __table_args__ = (
        Index('idx_email_created', 'email', 'created_at'),
        Index('idx_subscription_tier', 'subscription_tier'),
    )

    def __repr__(self):
        return f"<User(stytch_user_id='{self.stytch_user_id}', email='{self.email}')>"
