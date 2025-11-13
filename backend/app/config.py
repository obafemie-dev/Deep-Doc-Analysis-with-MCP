from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Deep Doc Analysis with MCP"

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # File Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: set[str] = {".xlsx", ".xls", ".xlsm"}

    # LLM Provider Settings
    LLM_PROVIDER: str = "claude"  # "claude" or "ollama"

    # Ollama Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:1.5b-instruct"

    # Claude Settings
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20241022"
    ANTHROPIC_API_KEY: Optional[str] = None  # Used by claude_service.py

    # MCP Server Settings
    MCP_SERVER_NAME: str = "Excel Analysis Server"

    # Analytics Settings
    ANALYTICS_ENABLED: bool = True
    ANALYTICS_DB_URL: str = "sqlite+aiosqlite:///./analytics.db"
    ANALYTICS_BATCH_SIZE: int = 100
    ANALYTICS_RETENTION_DAYS: int = 90

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
