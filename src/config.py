"""
Configuration settings for RAG Assistant
Loaded from environment variables via .env file
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Claude API
    anthropic_api_key: str

    # Bank Website
    bank_website_url: str
    bank_website_sitemap_url: Optional[str] = None

    # RAG Configuration
    chunk_size: int = 500
    chunk_overlap: int = 100
    retrieval_top_k: int = 5

    # Conversation
    context_window: int = 5
    max_conversation_length: int = 100

    # Chroma DB
    chroma_db_path: str = "./chroma_db"
    chroma_collection: str = "bank_content"
    chroma_persist_directory: str = "./chroma_data"

    # Database (Supabase)
    supabase_url: Optional[str] = None
    supabase_api_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"
    debug: bool = False

    # Frontend
    frontend_url: str = "http://localhost:3000"

    # Vercel
    vercel_env: str = "development"
    vercel_token: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
