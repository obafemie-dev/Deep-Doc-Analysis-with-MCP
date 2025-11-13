"""
Main FastAPI Application - Deep Doc Analysis with MCP
"""
import os
import json
import asyncio
import shutil
from pathlib import Path
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import logging

from .config import settings
from .models import (
    ChatRequest,
    ChatResponse,
    FileUploadResponse,
    AnalysisResult
)
from .llm_service import llm_service
from .claude_service import claude_service
from .database import init_analytics_db
from .middleware.analytics_middleware import AnalyticsMiddleware
from .routers import analytics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Select LLM service based on configuration
active_llm_service = claude_service if settings.LLM_PROVIDER == "claude" else llm_service
logger.info(f"Using LLM provider: {settings.LLM_PROVIDER}")

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add analytics middleware (if enabled)
if settings.ANALYTICS_ENABLED:
    app.add_middleware(AnalyticsMiddleware)
    logger.info("Analytics middleware enabled")

# Include analytics router
app.include_router(analytics.router)

# Ensure upload directory exists
UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# STARTUP & SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting application...")

    # Initialize analytics database
    if settings.ANALYTICS_ENABLED:
        try:
            await init_analytics_db()
            logger.info("Analytics database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize analytics database: {e}")

    logger.info("Application started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Shutting down application...")


# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": settings.PROJECT_NAME}


@app.get(f"{settings.API_V1_STR}/status")
async def get_status():
    """Get system status including LLM provider and model availability"""
    llm_status = {}

    if settings.LLM_PROVIDER == "ollama":
        llm_status = llm_service.check_ollama_status()
    else:
        llm_status = {
            "status": "configured",
            "provider": "claude",
            "model": settings.CLAUDE_MODEL
        }

    return {
        "api_status": "running",
        "llm_provider": settings.LLM_PROVIDER,
        "llm_status": llm_status,
        "upload_dir": str(UPLOAD_DIR),
        "mcp_server": "active",
        "available_tools": len(active_llm_service.mcp_tools)
    }


# ============================================================================
# FILE UPLOAD ENDPOINTS
# ============================================================================

@app.post(
    f"{settings.API_V1_STR}/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED
)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload Excel file for analysis

    Args:
        file: Excel file (.xlsx, .xls, .xlsm)

    Returns:
        File upload information including path and size
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # Validate file size (basic check, actual size checked during read)
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {settings.MAX_FILE_SIZE / (1024*1024)}MB"
        )

    # Save file
    file_path = UPLOAD_DIR / file.filename

    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"File uploaded successfully: {file_path}")

        return FileUploadResponse(
            filename=file.filename,
            file_path=str(file_path),
            size=file_size
        )

    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )


@app.get(f"{settings.API_V1_STR}/files")
async def list_uploaded_files():
    """
    List all uploaded files

    Returns:
        List of uploaded file information
    """
    files = []

    for file_path in UPLOAD_DIR.glob("*"):
        if file_path.is_file():
            files.append({
                "filename": file_path.name,
                "file_path": str(file_path),
                "size": file_path.stat().st_size,
                "modified": file_path.stat().st_mtime
            })

    return {"files": files, "count": len(files)}


@app.delete(f"{settings.API_V1_STR}/files/{{filename}}")
async def delete_file(filename: str):
    """
    Delete an uploaded file

    Args:
        filename: Name of file to delete

    Returns:
        Success message
    """
    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {filename}"
        )

    try:
        file_path.unlink()
        logger.info(f"File deleted: {file_path}")
        return {"message": f"File '{filename}' deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting file: {str(e)}"
        )


# ============================================================================
# CHAT ENDPOINTS
# ============================================================================

@app.post(
    f"{settings.API_V1_STR}/chat",
    response_model=ChatResponse
)
async def chat(request: ChatRequest):
    """
    Chat with LLM about Excel files

    Args:
        request: Chat request with message, optional file path, and conversation history

    Returns:
        LLM response with potential tool call information
    """
    try:
        # Validate file path if provided
        if request.file_path:
            file_path = Path(request.file_path)
            if not file_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File not found: {request.file_path}"
                )

        # Get LLM response (chat returns an async generator)
        response_generator = active_llm_service.chat(
            message=request.message,
            conversation_history=request.conversation_history,
            file_path=request.file_path,
            stream=False
        )

        # Collect the response from the async generator
        response_text = ""
        async for chunk in response_generator:
            response_text += chunk

        logger.info(f"Chat response generated successfully")

        return ChatResponse(
            response=response_text
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat: {str(e)}"
        )


@app.post(f"{settings.API_V1_STR}/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Chat with LLM about Excel files (Server-Sent Events streaming)

    Args:
        request: Chat request with message, optional file path, and conversation history

    Returns:
        Streaming response with real-time updates
    """
    try:
        # Validate file path if provided
        if request.file_path:
            file_path = Path(request.file_path)
            if not file_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File not found: {request.file_path}"
                )

        async def event_generator():
            """Generate Server-Sent Events"""
            try:
                # Get streaming response from LLM
                response_generator = active_llm_service.chat(
                    message=request.message,
                    conversation_history=request.conversation_history,
                    file_path=request.file_path,
                    stream=True
                )

                # Stream each chunk as SSE
                async for chunk in response_generator:
                    # SSE format: "data: {json}\n\n"
                    if isinstance(chunk, dict):
                        # Chain of thought event (tool execution, thinking, etc.)
                        event_data = json.dumps(chunk)
                    else:
                        # Text content chunk
                        event_data = json.dumps({"type": "content", "content": chunk})

                    yield f"data: {event_data}\n\n"
                    await asyncio.sleep(0)  # Force immediate event loop flush

                # Send completion signal
                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error(f"Error in streaming: {e}", exc_info=True)
                error_data = json.dumps({"error": str(e)})
                yield f"data: {error_data}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
                "Transfer-Encoding": "chunked"  # Force chunked transfer
            }
        )

    except Exception as e:
        logger.error(f"Error setting up stream: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error setting up stream: {str(e)}"
        )


# ============================================================================
# MODEL MANAGEMENT ENDPOINTS
# ============================================================================

@app.post(f"{settings.API_V1_STR}/models/pull")
async def pull_model():
    """
    Pull the configured Ollama model if not available (Ollama only)

    Returns:
        Success status and message
    """
    try:
        if settings.LLM_PROVIDER != "ollama":
            return {
                "success": False,
                "message": f"Model pulling only available for Ollama provider. Current provider: {settings.LLM_PROVIDER}"
            }

        result = await llm_service.pull_model_if_needed()
        return result

    except Exception as e:
        logger.error(f"Error pulling model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error pulling model: {str(e)}"
        )


@app.get(f"{settings.API_V1_STR}/tools")
async def list_available_tools():
    """
    List all available MCP tools

    Returns:
        List of tool names and descriptions
    """
    tools = []

    for tool in active_llm_service.mcp_tools:
        # Handle both Ollama and Claude tool formats
        if settings.LLM_PROVIDER == "ollama":
            tools.append({
                "name": tool['function']['name'],
                "description": tool['function']['description'],
                "parameters": list(tool['function']['parameters']['properties'].keys())
            })
        else:  # Claude format
            tools.append({
                "name": tool['name'],
                "description": tool['description'],
                "parameters": list(tool['input_schema']['properties'].keys())
            })

    return {
        "tools": tools,
        "count": len(tools)
    }


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler with analytics logging"""
    import traceback
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    # Log error to analytics (async, non-blocking)
    if settings.ANALYTICS_ENABLED:
        try:
            from .database import AsyncSessionLocal
            from .services.analytics_service import AnalyticsService

            session_id = request.headers.get("X-Session-ID")

            async def log_error_async():
                async with AsyncSessionLocal() as db:
                    analytics = AnalyticsService(db)
                    await analytics.log_error(
                        session_id=session_id,
                        error_type=type(exc).__name__,
                        error_message=str(exc),
                        stack_trace=traceback.format_exc(),
                        endpoint=str(request.url.path),
                        request_data={
                            "method": request.method,
                            "url": str(request.url)
                        }
                    )
                    await db.commit()

            asyncio.create_task(log_error_async())
        except Exception as e:
            logger.error(f"Failed to log error to analytics: {e}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
