"""
Pydantic models for API requests/responses
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime


class ScrapeRequest(BaseModel):
    """Request to scrape and index website content"""
    url: Optional[str] = Field(None, description="Website URL to scrape (optional, defaults to configured URL)")


class ScrapeResponse(BaseModel):
    """Response from scrape operation"""
    success: bool
    message: str
    documents_indexed: int = 0


class QueryRequest(BaseModel):
    """Request to ask a question"""
    user_id: str = Field(..., description="Unique user identifier")
    question: str = Field(..., description="User's question")


class QueryResponse(BaseModel):
    """Response with answer and sources"""
    user_id: str
    question: str
    answer: str
    sources: List[Dict] = Field(default_factory=list)
    timestamp: datetime


class Message(BaseModel):
    """Conversation message"""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: datetime


class HistoryResponse(BaseModel):
    """User's conversation history"""
    user_id: str
    messages: List[Message]


class ClearHistoryResponse(BaseModel):
    """Response from clear history operation"""
    success: bool
    message: str


class StatsResponse(BaseModel):
    """Statistics about indexed content"""
    vector_store: str
    document_count: int
    embedding_model: str
    vector_dimension: int
    supabase_url: str


class MetricsResponse(BaseModel):
    """
    Aggregated metrics response for GET /api/metrics and GET /api/metrics/{user_id}.
    All numeric values are pre-computed aggregates over the requested time window.
    """
    period: Dict = Field(..., description="Time range covered: {from, to}")
    requests: Dict = Field(..., description="Request counts and success rate")
    users: Dict = Field(..., description="Unique users and avg requests/user")
    business_metrics: Dict = Field(..., description="Deflection rate, cost comparison, ROI metrics")
    latency_ms: Dict = Field(..., description="Avg/min/max latency breakdown by phase")
    tokens: Dict = Field(..., description="Token usage totals and per-request averages")
    costs: Dict = Field(..., description="Total and per-request estimated USD cost")
    retrieval: Dict = Field(..., description="Relevance scores, quality distribution, MMR usage")
    insights: Dict = Field(..., description="Top keywords, trending queries")
