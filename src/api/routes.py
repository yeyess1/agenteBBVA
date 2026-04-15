"""
API routes for RAG Assistant
"""

import logging
from fastapi import APIRouter, HTTPException, status
from datetime import datetime

from src.api.models import (
    ScrapeRequest,
    ScrapeResponse,
    QueryRequest,
    QueryResponse,
    HistoryResponse,
    ClearHistoryResponse,
    StatsResponse,
)
from src.scraper.web_scraper import WebScraper
from src.vectorizer.embedding import EmbeddingManager
from src.rag.retriever import DocumentRetriever
from src.rag.generator import ResponseGenerator
from src.conversation.memory import ConversationMemory

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize components
scraper = WebScraper()
embedding_manager = EmbeddingManager()
retriever = DocumentRetriever()
generator = ResponseGenerator()
memory = ConversationMemory()


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
    Ask a question about bank information

    This endpoint:
    1. Retrieves relevant documents from vector store
    2. Generates response using Claude API with conversation history
    3. Stores the conversation for future context
    """
    try:
        user_id = request.user_id.strip()
        question = request.question.strip()

        if not user_id or not question:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id and question are required"
            )

        # Retrieve relevant documents
        documents = retriever.retrieve(question)
        context = retriever.format_context(documents)
        context_quality = retriever.assess_context_quality(documents)
        sources = retriever.get_sources(documents)

        # Get conversation history (last N messages)
        conversation_history = memory.get_messages(user_id)

        # Generate response (async generator)
        answer = await generator.generate(question, context, conversation_history, context_quality)

        # Store in conversation memory
        memory.add_message(user_id, "user", question)
        memory.add_message(user_id, "assistant", answer)

        return QueryResponse(
            user_id=user_id,
            question=question,
            answer=answer,
            sources=sources,
            timestamp=datetime.utcnow(),
        )
    except HTTPException:
        raise
    except Exception as e:
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
        stats = embedding_manager.get_stats()
        return StatsResponse(**stats)
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
