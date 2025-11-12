"""
Main FastAPI Application - Deep Doc Analysis with MCP
"""
import os
import shutil
from pathlib import Path
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from .config import settings
from .models import (
    ChatRequest,
    ChatResponse,
    FileUploadResponse,
    AnalysisResult
)
from .llm_service import llm_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# Ensure upload directory exists
UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": settings.PROJECT_NAME}


@app.get(f"{settings.API_V1_STR}/status")
async def get_status():
    """Get system status including Ollama and model availability"""
    ollama_status = llm_service.check_ollama_status()

    return {
        "api_status": "running",
        "ollama_status": ollama_status,
        "upload_dir": str(UPLOAD_DIR),
        "mcp_server": "active",
        "available_tools": len(llm_service.mcp_tools)
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

        # Get LLM response
        response_text = await llm_service.chat(
            message=request.message,
            conversation_history=request.conversation_history,
            file_path=request.file_path,
            stream=False
        )

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


# ============================================================================
# MODEL MANAGEMENT ENDPOINTS
# ============================================================================

@app.post(f"{settings.API_V1_STR}/models/pull")
async def pull_model():
    """
    Pull the configured Ollama model if not available

    Returns:
        Success status and message
    """
    try:
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

    for tool in llm_service.mcp_tools:
        tools.append({
            "name": tool['function']['name'],
            "description": tool['function']['description'],
            "parameters": list(tool['function']['parameters']['properties'].keys())
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
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

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
