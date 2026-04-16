"""
API routes for RAG Assistant
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException, Query, status
from datetime import datetime

from src.api.models import (
    ScrapeRequest,
    ScrapeResponse,
    QueryRequest,
    QueryResponse,
    HistoryResponse,
    ClearHistoryResponse,
    StatsResponse,
    MetricsResponse,
)
from src.metrics import MetricsCollector, MetricsAggregator
from src.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Components initialized lazily on first request (not at module import)
# This allows uvicorn to bind the port before heavy models load
_scraper = None
_embedding_manager = None
_retriever = None
_generator = None
_memory = None


def get_components():
    global _scraper, _embedding_manager, _retriever, _generator, _memory
    if _scraper is None:
        # Deferred imports: sentence_transformers/torch and google.generativeai are
        # large C-extension libraries. Importing them at module level blocks uvicorn
        # from binding the port (Render times out). Load them here on first request.
        from src.scraper.web_scraper import WebScraper
        from src.vectorizer.embedding import EmbeddingManager
        from src.rag.retriever import DocumentRetriever
        from src.rag.generator import ResponseGenerator
        from src.conversation.memory import ConversationMemory

        logger.info("Initializing components (first request)...")
        _scraper = WebScraper()
        _embedding_manager = EmbeddingManager()
        _retriever = DocumentRetriever()
        _generator = ResponseGenerator()
        _memory = ConversationMemory()
        logger.info("Components initialized.")
    return _scraper, _embedding_manager, _retriever, _generator, _memory


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_website(request: ScrapeRequest) -> ScrapeResponse:
    """
    Scrape and index bank website content

    This endpoint:
    1. Scrapes the bank website (or specified URL)
    2. Chunks the content
    3. Indexes it in Chroma DB for semantic search
    """
    try:
        scraper, embedding_manager, _, _, _ = get_components()
        url = request.url or scraper.base_url
        logger.info(f"Starting scrape of {url}")

        # Scrape website
        pages = scraper.scrape_all()
        if not pages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No content could be scraped from the website"
            )

        # Process and index
        chunks_indexed = embedding_manager.process_and_index(pages)

        return ScrapeResponse(
            success=True,
            message=f"Successfully scraped and indexed {len(pages)} pages with {chunks_indexed} chunks",
            documents_indexed=chunks_indexed,
        )
    except Exception as e:
        logger.error(f"Scrape error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest) -> QueryResponse:
    """
    Ask a question about bank information.

    Pipeline:
    1. Retrieve relevant documents from vector store (with MMR reranking)
    2. Generate response using Gemini with conversation history
    3. Persist conversation turn
    4. Fire-and-forget: persist metrics to Supabase
    """
    user_id = request.user_id.strip()
    question = request.question.strip()

    if not user_id or not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id and question are required"
        )

    _, _, retriever, generator, memory = get_components()
    collector = MetricsCollector(user_id)
    collector.set_query(question)

    try:
        # ── Retrieval ────────────────────────────────────────────
        with collector.retrieval_timer():
            documents = retriever.retrieve(question)

        context = retriever.format_context(documents)
        context_quality = retriever.assess_context_quality(documents)
        sources = retriever.get_sources(documents)
        retrieval_stats = retriever.get_last_retrieval_stats()

        collector.set_retrieval_stats(
            documents=documents,
            context_quality=context_quality,
            candidate_count=retrieval_stats.get("candidate_count", 0),
            threshold_filtered=retrieval_stats.get("threshold_filtered", 0),
            mmr_applied=retrieval_stats.get("mmr_applied", False),
        )

        # ── Generation ───────────────────────────────────────────
        conversation_history = memory.get_messages(user_id)

        with collector.generation_timer():
            result = await generator.generate(
                question, context, conversation_history, context_quality
            )

        collector.set_generation_stats(
            answer=result.text,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            model=settings.gemini_model,
        )

        # ── Persist conversation turn ────────────────────────────
        memory.add_message(user_id, "user", question)
        memory.add_message(user_id, "assistant", result.text)

        # ── Persist metrics (fire-and-forget) ────────────────────
        asyncio.create_task(collector.save())

        return QueryResponse(
            user_id=user_id,
            question=question,
            answer=result.text,
            sources=sources,
            timestamp=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        collector.mark_error(str(e))
        asyncio.create_task(collector.save())
        logger.error(f"Query error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/history/{user_id}", response_model=HistoryResponse)
async def get_history(user_id: str) -> HistoryResponse:
    """
    Get conversation history for a user

    Returns all messages in the conversation history
    (not limited by CONTEXT_WINDOW)
    """
    try:
        _, _, _, _, memory = get_components()
        user_id = user_id.strip()
        messages = memory.get_full_history(user_id)

        return HistoryResponse(
            user_id=user_id,
            messages=[
                {
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg["timestamp"],
                }
                for msg in messages
            ],
        )
    except Exception as e:
        logger.error(f"History error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/history/{user_id}", response_model=ClearHistoryResponse)
async def clear_history(user_id: str) -> ClearHistoryResponse:
    """
    Clear conversation history for a user
    """
    try:
        _, _, _, _, memory = get_components()
        user_id = user_id.strip()
        success = memory.clear_conversation(user_id)

        return ClearHistoryResponse(
            success=success,
            message=f"Conversation history cleared for user {user_id}" if success else "Failed to clear history",
        )
    except Exception as e:
        logger.error(f"Clear history error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/stats", response_model=StatsResponse)
async def get_stats() -> StatsResponse:
    """
    Get statistics about indexed content
    """
    try:
        _, embedding_manager, _, _, _ = get_components()
        stats = embedding_manager.get_stats()
        return StatsResponse(**stats)
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ── Metrics endpoints ─────────────────────────────────────────────────────────

_aggregator = MetricsAggregator()


@router.get("/metrics", response_model=MetricsResponse)
async def get_global_metrics(
    hours: int = Query(default=24, ge=1, le=720, description="Lookback window in hours (max 720 = 30 days)")
) -> MetricsResponse:
    """
    Global aggregated metrics over the last N hours.

    Returns retrieval quality, generation token usage, latency breakdown,
    estimated cost, and request counts for all users combined.

    Query params:
    - **hours**: lookback window (default 24, max 720)
    """
    try:
        data = await _aggregator.get_global_stats(hours=hours)
        return MetricsResponse(**data)
    except Exception as e:
        logger.error(f"Global metrics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/metrics/{user_id}", response_model=MetricsResponse)
async def get_user_metrics(
    user_id: str,
    days: int = Query(default=30, ge=1, le=365, description="Lookback window in days (max 365)")
) -> MetricsResponse:
    """
    Per-user aggregated metrics over the last N days.

    Returns the same breakdown as the global endpoint but scoped to a
    single user_id. Useful for session-level analysis.

    Query params:
    - **days**: lookback window (default 30, max 365)
    """
    try:
        user_id = user_id.strip()
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id is required"
            )
        data = await _aggregator.get_user_stats(user_id=user_id, days=days)
        return MetricsResponse(**data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User metrics error for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
