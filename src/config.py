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

    # Database (Supabase)
    supabase_url: str
    supabase_api_key: str
    supabase_service_role_key: str

    # Vector Store Configuration
    vector_dimension: int = 1024  # BGE-M3 produces 1024-dimensional vectors
    embedding_model: str = "BAAI/bge-m3"

    # RAG Retrieval Configuration
    retrieval_score_threshold: float = 0.40  # BGE-M3 cosine similarity minimum (0.40-0.54 = weak relevance)
    mmr_lambda: float = 0.7  # Maximal Marginal Relevance: λ·relevance - (1-λ)·diversity

    # Claude API Configuration
    claude_model: str = "claude-haiku-4-5-20251001"

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
