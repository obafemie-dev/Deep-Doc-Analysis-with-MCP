from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import Optional, Union


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Deep Doc Analysis with MCP"

    # CORS - Comma-separated list of allowed origins
    BACKEND_CORS_ORIGINS: Union[str, list[str]] = "http://localhost:3000,http://localhost:5173"

    @model_validator(mode='after')
    def parse_comma_separated_values(self):
        """Parse comma-separated values into lists/sets"""
        # Parse CORS origins
        if isinstance(self.BACKEND_CORS_ORIGINS, str):
            self.BACKEND_CORS_ORIGINS = [
                origin.strip()
                for origin in self.BACKEND_CORS_ORIGINS.split(',')
                if origin.strip()
            ]

        # Parse allowed extensions
        if isinstance(self.ALLOWED_EXTENSIONS, str):
            self.ALLOWED_EXTENSIONS = {
                ext.strip()
                for ext in self.ALLOWED_EXTENSIONS.split(',')
                if ext.strip()
            }

        return self

    # File Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: Union[str, set[str]] = {".xlsx", ".xls", ".xlsm"}

    # LLM Provider Settings
    LLM_PROVIDER: str = "claude"  # "claude" or "ollama"

    # Ollama Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"

    # Claude Settings
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
    ANTHROPIC_API_KEY: Optional[str] = None  # Used by claude_service.py

    # MCP Server Settings
    MCP_SERVER_NAME: str = "Excel Analysis Server"

    # Analytics Settings
    ANALYTICS_ENABLED: bool = True
    ANALYTICS_DB_URL: str = "sqlite+aiosqlite:///./analytics.db"
    ANALYTICS_BATCH_SIZE: int = 100
    ANALYTICS_RETENTION_DAYS: int = 90

    # Metabase Proxy Settings
    METABASE_ENABLED: bool = True
    METABASE_URL: str = "http://metabase:3000"
    METABASE_TIMEOUT: int = 60

    # Stytch Authentication Settings
    STYTCH_PROJECT_ID: Optional[str] = None
    STYTCH_SECRET: Optional[str] = None
    STYTCH_ENV: str = "test"  # "test" or "live"
    FRONTEND_URL: str = "http://localhost:3000"

    class Config:
        env_file = "../../.env"
        case_sensitive = True


settings = Settings()
