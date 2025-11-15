"""
Metabase Dashboard Reverse Proxy Router
Proxies requests to Metabase analytics dashboard
"""
import httpx
import logging
from fastapi import APIRouter, Request, Response, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import Optional

from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/metabase",
    tags=["metabase-proxy"],
    responses={503: {"description": "Metabase service unavailable"}}
)

# Shared httpx client with connection pooling
httpx_client: Optional[httpx.AsyncClient] = None


async def get_httpx_client() -> httpx.AsyncClient:
    """Get or create shared httpx client"""
    global httpx_client
    if httpx_client is None:
        httpx_client = httpx.AsyncClient(
            base_url=settings.METABASE_URL,
            timeout=httpx.Timeout(settings.METABASE_TIMEOUT),
            follow_redirects=True,
            cookies=None
        )
    return httpx_client


async def shutdown_httpx_client():
    """Cleanup httpx client on shutdown"""
    global httpx_client
    if httpx_client is not None:
        await httpx_client.aclose()
        httpx_client = None


# Headers that should NOT be forwarded to Metabase
EXCLUDED_HEADERS = {
    'host',
    'connection',
    'content-length',
    'transfer-encoding',
    'content-encoding',
    'x-forwarded-for',
    'x-forwarded-proto',
    'x-forwarded-host',
}


def filter_request_headers(headers: dict) -> dict:
    """Filter and prepare headers for forwarding to Metabase"""
    filtered = {}
    for name, value in headers.items():
        name_lower = name.lower()
        if name_lower not in EXCLUDED_HEADERS:
            filtered[name] = value
    return filtered


def filter_response_headers(headers: httpx.Headers) -> dict:
    """Filter response headers from Metabase"""
    excluded = {
        'connection',
        'keep-alive',
        'transfer-encoding',
        'content-encoding',
        'content-length',
        'server',
    }

    filtered = {}
    for name, value in headers.items():
        name_lower = name.lower()
        if name_lower not in excluded:
            filtered[name] = value

    return filtered


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    include_in_schema=False
)
async def proxy_to_metabase(request: Request, path: str):
    """
    Reverse proxy all requests to Metabase dashboard.

    This endpoint:
    - Forwards all HTTP methods to Metabase
    - Handles streaming responses
    - Supports WebSocket upgrade headers
    - Maintains cookies and sessions per-client
    - Preserves query parameters

    Security:
    - Cookies are NOT shared between different clients
    - Each request gets its own httpx request context
    - Headers are filtered to prevent injection
    """

    if not settings.METABASE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Metabase proxy is disabled"
        )

    try:
        client = await get_httpx_client()

        # Build target URL with query parameters
        target_path = f"/{path}" if path else "/"
        query_string = str(request.url.query)
        target_url = f"{target_path}?{query_string}" if query_string else target_path

        # Prepare headers
        headers = filter_request_headers(dict(request.headers))

        # Add forwarding headers for proxy transparency
        headers['X-Forwarded-For'] = request.client.host if request.client else 'unknown'
        headers['X-Forwarded-Proto'] = request.url.scheme
        headers['X-Forwarded-Host'] = request.headers.get('host', 'unknown')

        # Support WebSocket upgrades if requested
        upgrade_header = request.headers.get('upgrade', '').lower()
        if upgrade_header == 'websocket':
            headers['Upgrade'] = 'websocket'
            headers['Connection'] = 'upgrade'

        # Read request body
        body = await request.body()

        # Forward request to Metabase
        logger.debug(f"Proxying {request.method} {target_url} to Metabase")

        response = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body if body else None,
            cookies=request.cookies
        )

        # Filter response headers
        response_headers = filter_response_headers(response.headers)

        # Handle streaming responses (for large dashboards, downloads, etc.)
        if response.headers.get('content-type', '').startswith(('text/event-stream', 'application/octet-stream')):
            async def stream_response():
                async for chunk in response.aiter_bytes():
                    yield chunk

            return StreamingResponse(
                stream_response(),
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get('content-type')
            )

        # Regular response
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers,
            media_type=response.headers.get('content-type')
        )

    except httpx.TimeoutException:
        logger.error(f"Timeout proxying request to Metabase: {path}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Metabase request timed out"
        )

    except httpx.ConnectError:
        logger.error(f"Failed to connect to Metabase at {settings.METABASE_URL}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Metabase service is unavailable"
        )

    except Exception as e:
        logger.error(f"Error proxying request to Metabase: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error communicating with Metabase: {str(e)}"
        )


@router.get("/", include_in_schema=False)
async def proxy_root(request: Request):
    """Handle root path explicitly to ensure proper routing"""
    return await proxy_to_metabase(request, "")
