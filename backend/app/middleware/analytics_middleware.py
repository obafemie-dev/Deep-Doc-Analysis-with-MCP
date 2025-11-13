"""
Analytics middleware for automatic request/response tracking
"""
import time
import asyncio
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable

from ..config import settings
from ..database import AsyncSessionLocal
from ..services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)


class AnalyticsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically track API requests and responses.

    Features:
    - Non-blocking async event logging
    - Performance metrics (request duration)
    - Session tracking via X-Session-ID header
    - Excludes health check and static endpoints
    """

    # Endpoints to exclude from analytics
    EXCLUDED_PATHS = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and track analytics.

        Args:
            request: Incoming request
            call_next: Next middleware/endpoint handler

        Returns:
            Response from endpoint
        """
        # Skip analytics for excluded paths
        if self._should_exclude(request.url.path):
            return await call_next(request)

        # Skip if analytics disabled
        if not settings.ANALYTICS_ENABLED:
            return await call_next(request)

        # Extract session ID from headers
        session_id = request.headers.get("X-Session-ID")

        # Track request start time
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Log API request asynchronously (non-blocking)
        if session_id:
            asyncio.create_task(
                self._log_api_request(
                    path=str(request.url.path),
                    method=request.method,
                    session_id=session_id,
                    status_code=response.status_code,
                    duration_ms=duration_ms
                )
            )

        # Add performance header
        response.headers["X-Response-Time"] = f"{duration_ms}ms"

        return response

    def _should_exclude(self, path: str) -> bool:
        """Check if path should be excluded from analytics"""
        # Exact match
        if path in self.EXCLUDED_PATHS:
            return True

        # Prefix match for static files
        excluded_prefixes = ("/static/", "/assets/", "/favicon.ico")
        return any(path.startswith(prefix) for prefix in excluded_prefixes)

    async def _log_api_request(
        self,
        path: str,
        method: str,
        session_id: str,
        status_code: int,
        duration_ms: int
    ):
        """
        Log API request to analytics database (async, non-blocking).

        This runs in the background and won't affect response time.
        """
        try:
            async with AsyncSessionLocal() as db:
                analytics = AnalyticsService(db)

                await analytics.log_event(
                    event_type="api_request",
                    session_id=session_id,
                    data={
                        "endpoint": path,
                        "method": method,
                        "status_code": status_code
                    },
                    metadata={
                        "duration_ms": duration_ms
                    }
                )

                await db.commit()

        except Exception as e:
            # Don't let analytics errors affect the main application
            logger.error(f"Failed to log API request: {e}")
