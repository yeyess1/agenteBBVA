"""
Pydantic models for internal metrics data structures.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RetrievalMetrics(BaseModel):
    """Metrics captured during the document retrieval phase."""
    latency_ms: float = 0.0
    candidate_count: int = 0        # Documents fetched before threshold filter (2x over-fetch)
    document_count: int = 0         # Documents returned after threshold + MMR
    threshold_filtered: int = 0     # Documents removed by score threshold
    avg_score: float = 0.0          # Average cosine similarity of final docs
    top_score: float = 0.0          # Best cosine similarity score
    context_quality: str = "none"   # "high" | "medium" | "low" | "none"
    mmr_applied: bool = False        # Whether MMR reranking was executed


class GenerationMetrics(BaseModel):
    """Metrics captured during the LLM generation phase."""
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    model_used: str = ""
    estimated_cost_usd: float = 0.0


class RequestMetrics(BaseModel):
    """Complete metrics record for a single /ask request."""
    user_id: str
    session_id: str
    query_length: int = 0
    answer_length: int = 0
    total_latency_ms: float = 0.0
    retrieval: RetrievalMetrics = Field(default_factory=RetrievalMetrics)
    generation: GenerationMetrics = Field(default_factory=GenerationMetrics)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: Optional[str] = None
