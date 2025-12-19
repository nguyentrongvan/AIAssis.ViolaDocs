from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    app_name: str = "ViolaDocs API"
    env: str = "local"
    api_prefix: str = "/api/v1"
    api_v1_prefix: str = "/api/v1"  # Alias for env variable API_V1_PREFIX
    debug: bool = True
    log_level: str = "INFO"

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "viadocs"
    postgres_password: str = "viadocs_pass"
    postgres_db: str = "viadocs_db"

    @property
    def postgres_dsn(self) -> str:
        return f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def postgres_async_dsn(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_secure: bool = False
    minio_bucket: str = "documents"

    # JWT
    jwt_secret_key: str = "change-me-in-production-min-32-chars-long"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Root User - Auto-create on startup if not exists
    root_user_email: str = "admin@example.com"
    root_user_password: str = "admin123"
    root_user_name: str = "Admin"

    # Ollama - Local LLM with OpenAI-compatible API
    ollama_base_url: str = "http://localhost:11434"  # Default to localhost, use http://ollama:11434 in docker
    ollama_api_key: str = ""  # Optional API key for OpenAI-compatible endpoints
    ollama_llm_model: str = "llama3.2:1b"  # Default LLM model for chat
    ollama_embedding_model: str = "nomic-embed-text:latest"  # Default embedding model

    # OCR
    # Only Tesseract is supported now
    # Supported languages: en (English), vi (Vietnamese), ja (Japanese), ko (Korean), zh (Chinese)
    ocr_provider: str = "tesseract"
    ocr_languages: str = "en,vi"  # Default: English and Vietnamese. Can add: ja,ko,zh
    
    # Qdrant vector store config
    qdrant_host: str = "localhost"  # Qdrant server host (use "qdrant" in Docker)
    qdrant_port: int = 6333  # HTTP API port
    qdrant_grpc_port: int = 6334  # gRPC API port (optional, for better performance)
    qdrant_collection: str = "embeddings"  # Collection name
    qdrant_api_key: str = ""  # Optional API key for Qdrant Cloud
    
    # Backward compatibility - ChromaDB settings (deprecated, will be removed)
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection: str = "embeddings"
    chroma_server_host: str = ""
    chroma_server_port: int = 8001
    chroma_server_ssl: bool = False

    @property
    def ocr_lang_list(self) -> List[str]:
        return [lang.strip() for lang in self.ocr_languages.split(",")]

    # Retention
    default_retention_days: int = 365
    purge_grace_period_days: int = 30

    # Upload
    max_upload_size_mb: int = 100
    allowed_mime_types: str = "application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,image/jpeg,image/png,image/tiff,text/csv,application/csv,text/plain"
    
    # Worker Configuration
    max_concurrent_ocr_jobs: int = 5  # Max parallel OCR jobs
    max_concurrent_embed_jobs: int = 3  # Max parallel embedding jobs
    worker_batch_size: int = 10  # Number of jobs to fetch per iteration
    
    # Purge Worker Configuration
    purge_worker_poll_interval: int = 3600  # Poll interval in seconds (default: 1 hour)
    purge_worker_batch_size: int = 100  # Max documents to process per run

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def allowed_mime_list(self) -> List[str]:
        return [mime.strip() for mime in self.allowed_mime_types.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env that don't match model fields


settings = Settings()


# Helper functions to get settings from DB with fallback to config
# These are used by services that need to read settings dynamically
async def get_ocr_provider_from_db() -> str:
    """Get OCR provider from DB, fallback to config"""
    try:
        from .services.settings_service import SettingsService
        return await SettingsService.get_setting("ocr.provider", settings.ocr_provider)
    except Exception:
        return settings.ocr_provider


async def get_ocr_languages_from_db() -> List[str]:
    """Get OCR languages from DB, fallback to config"""
    try:
        from .services.settings_service import SettingsService
        db_langs = await SettingsService.get_setting("ocr.languages", None)
        if db_langs and isinstance(db_langs, list):
            return db_langs
        return settings.ocr_lang_list
    except Exception:
        return settings.ocr_lang_list


async def get_ollama_base_url_from_db() -> str:
    """Get Ollama base URL from DB, fallback to config"""
    try:
        from .services.settings_service import SettingsService
        return await SettingsService.get_setting("llm.ollama.base_url", settings.ollama_base_url)
    except Exception:
        return settings.ollama_base_url


async def get_ollama_llm_model_from_db() -> str:
    """Get Ollama LLM model from DB, fallback to config"""
    try:
        from .services.settings_service import SettingsService
        return await SettingsService.get_setting("llm.ollama.llm_model", settings.ollama_llm_model)
    except Exception:
        return settings.ollama_llm_model


async def get_ollama_embedding_model_from_db() -> str:
    """Get Ollama embedding model from DB, fallback to config"""
    try:
        from .services.settings_service import SettingsService
        return await SettingsService.get_setting("llm.ollama.embedding_model", settings.ollama_embedding_model)
    except Exception:
        return settings.ollama_embedding_model

