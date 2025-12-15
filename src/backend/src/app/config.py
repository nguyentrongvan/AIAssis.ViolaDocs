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
    ollama_llm_model: str = "llama3.2"  # Default LLM model for chat
    ollama_embedding_model: str = "nomic-text-embedding"  # Default embedding model

    # OCR
    ocr_provider: str = "paddle"
    ocr_languages: str = "en,vi"
    
    # Embedding - Local model name (sentence-transformers)
    # Options: all-MiniLM-L6-v2 (fast, 384d), paraphrase-multilingual-MiniLM-L12-v2 (multilingual, 384d), all-mpnet-base-v2 (better quality, 768d)
    embedding_model_name: str = "all-MiniLM-L6-v2"
    # Chroma vector store config (local persistent by default; can point to HTTP server)
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection: str = "embeddings"
    chroma_server_host: str = ""   # e.g., "localhost" to use HTTP server
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
    allowed_mime_types: str = "application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,image/jpeg,image/png,image/tiff"

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

