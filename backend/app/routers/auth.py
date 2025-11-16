"""
Stytch Authentication Router for Deep Doc Analysis
"""
import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Response, Cookie, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import stytch
import logging

from ..database import get_analytics_db
from ..models.user import User
from ..config import settings

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize Stytch client
stytch_client = stytch.Client(
    project_id=settings.STYTCH_PROJECT_ID or "",
    secret=settings.STYTCH_SECRET or "",
    environment=settings.STYTCH_ENV
)

router = APIRouter(prefix="/auth", tags=["authentication"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class SendMagicLinkRequest(BaseModel):
    email: EmailStr


class SendMagicLinkResponse(BaseModel):
    success: bool
    message: str
    user_id: Optional[str] = None


class AuthenticateRequest(BaseModel):
    token: str


class UserResponse(BaseModel):
    stytch_user_id: str
    email: str
    full_name: Optional[str] = None
    created_at: datetime
    subscription_tier: str


class AuthenticateResponse(BaseModel):
    success: bool
    user: UserResponse
    session_token: str


class LogoutResponse(BaseModel):
    success: bool
    message: str


# ============================================================================
# DEPENDENCY FOR PROTECTING ROUTES
# ============================================================================

async def get_current_user(
    stytch_session: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_analytics_db)
) -> User:
    """
    Dependency to get current authenticated user.

    Use this to protect routes that require authentication:

    Example:
        @router.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_email": user.email}
    """
    if not stytch_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in."
        )

    try:
        # Validate session with Stytch (JWT validation, very fast)
        stytch_resp = stytch_client.sessions.authenticate(
            session_token=stytch_session
        )

        # Get user from local database
        result = await db.execute(
            select(User).where(User.stytch_user_id == stytch_resp.user.user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in database"
            )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired session: {str(e)}"
        )


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@router.post("/send-magic-link", response_model=SendMagicLinkResponse)
async def send_magic_link(request: SendMagicLinkRequest):
    """
    Send magic link email for passwordless authentication.
    Works for both signup and login (unified flow).

    The user will receive an email with a unique link that authenticates them.
    """
    try:
        logger.info(f"Sending magic link to {request.email}")

        # Send magic link via Stytch (handles both new and existing users)
        resp = stytch_client.magic_links.email.login_or_create(
            email=request.email,
            login_magic_link_url=f"{settings.FRONTEND_URL}/authenticate",
            signup_magic_link_url=f"{settings.FRONTEND_URL}/authenticate",
            login_expiration_minutes=60,
        )

        logger.info(f"Magic link sent successfully to {request.email}, user_id: {resp.user_id}")

        return SendMagicLinkResponse(
            success=True,
            message="Magic link sent! Check your email to log in.",
            user_id=resp.user_id
        )
    except Exception as e:
        logger.error(f"Failed to send magic link to {request.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send magic link: {str(e)}"
        )


@router.post("/authenticate", response_model=AuthenticateResponse)
async def authenticate_magic_link(
    request: AuthenticateRequest,
    response: Response,
    db: AsyncSession = Depends(get_analytics_db)
):
    """
    Authenticate magic link token and create session.

    This endpoint:
    1. Validates the token with Stytch
    2. Creates or updates user in local database
    3. Sets HTTP-only session cookie
    4. Returns user information
    """
    try:
        logger.info(f"Authenticating magic link token")

        # Authenticate with Stytch
        stytch_resp = stytch_client.magic_links.authenticate(
            token=request.token,
            session_duration_minutes=10080  # 7 days
        )

        logger.info(f"Magic link authenticated for user: {stytch_resp.user.user_id}")

        # Get or create user in local database
        result = await db.execute(
            select(User).where(User.stytch_user_id == stytch_resp.user.user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            # Create new user
            logger.info(f"Creating new user: {stytch_resp.user.user_id}")

            # Get full name from Stytch user
            full_name = None
            if stytch_resp.user.name:
                first = stytch_resp.user.name.first_name or ""
                last = stytch_resp.user.name.last_name or ""
                full_name = f"{first} {last}".strip() or None

            user = User(
                stytch_user_id=stytch_resp.user.user_id,
                email=stytch_resp.user.emails[0].email if stytch_resp.user.emails else "",
                full_name=full_name,
                created_at=datetime.utcnow()
            )
            db.add(user)

        # Update last login
        user.last_login_at = datetime.utcnow()
        await db.commit()
        await db.refresh(user)

        logger.info(f"User synced to database: {user.email}")

        # Set session cookie (HTTP-only for security)
        # Use secure=True only for HTTPS (production), False for HTTP (localhost)
        is_production = settings.FRONTEND_URL.startswith("https://")
        response.set_cookie(
            key="stytch_session",
            value=stytch_resp.session_token,
            httponly=True,
            secure=is_production,  # True for HTTPS, False for HTTP
            samesite="lax",
            max_age=604800  # 7 days in seconds
        )

        return AuthenticateResponse(
            success=True,
            user=UserResponse(
                stytch_user_id=user.stytch_user_id,
                email=user.email,
                full_name=user.full_name,
                created_at=user.created_at,
                subscription_tier=user.subscription_tier
            ),
            session_token=stytch_resp.session_token
        )

    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    stytch_session: Optional[str] = Cookie(None)
):
    """
    Logout user and revoke session.
    """
    if stytch_session:
        try:
            # Revoke session in Stytch
            stytch_client.sessions.revoke(session_token=stytch_session)
            logger.info("Session revoked successfully")
        except Exception as e:
            # Session might already be expired, that's okay
            logger.warning(f"Failed to revoke session (might already be expired): {str(e)}")

    # Clear cookie
    response.delete_cookie("stytch_session")

    return LogoutResponse(
        success=True,
        message="Logged out successfully"
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    Protected route - requires valid session.
    """
    return UserResponse(
        stytch_user_id=current_user.stytch_user_id,
        email=current_user.email,
        full_name=current_user.full_name,
        created_at=current_user.created_at,
        subscription_tier=current_user.subscription_tier
    )
