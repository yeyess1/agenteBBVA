"""
MetricsCollector: Captures and persists metrics for each /ask request.

Usage pattern in routes.py:
    collector = MetricsCollector(user_id)
    collector.set_query(question)

    with collector.retrieval_timer():
        documents = retriever.retrieve(question)
    collector.set_retrieval_stats(documents, ...)

    with collector.generation_timer():
        result = await generator.generate(...)
    collector.set_generation_stats(result.text, result.input_tokens, ...)

    asyncio.create_task(collector.save())  # fire-and-forget
"""

import asyncio
import logging
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Optional

from src.metrics.models import GenerationMetrics, RequestMetrics, RetrievalMetrics
from src.metrics.utils import estimate_gemini_cost

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects timing and outcome data throughout an /ask request lifecycle.

    All state is instance-level, so one collector per request is required.
    The save() method is fire-and-forget: errors are logged but never raised
    so metrics never block or break user-facing responses.
    """

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.session_id = str(uuid.uuid4())[:8]
        self._request_start = time.monotonic()

        self._retrieval_start: Optional[float] = None
        self._retrieval_end: Optional[float] = None
        self._generation_start: Optional[float] = None
        self._generation_end: Optional[float] = None

        self._retrieval_data: Optional[Dict] = None
        self._generation_data: Optional[Dict] = None

        self._query_length: int = 0
        self._answer_length: int = 0
        self._success: bool = True
        self._error_message: Optional[str] = None

    @contextmanager
    def retrieval_timer(self):
        """Context manager: records start/end time for the retrieval phase."""
        self._retrieval_start = time.monotonic()
        try:
            yield
        finally:
            self._retrieval_end = time.monotonic()

    @contextmanager
    def generation_timer(self):
        """Context manager: records start/end time for the generation phase."""
        self._generation_start = time.monotonic()
        try:
            yield
        finally:
            self._generation_end = time.monotonic()

    def set_query(self, query: str) -> None:
        self._query_length = len(query)

    def set_retrieval_stats(
        self,
        documents: List[Dict],
        context_quality: str,
        candidate_count: int,
        threshold_filtered: int,
        mmr_applied: bool,
    ) -> None:
        """Record retrieval outcome. Call after retriever.retrieve()."""
        scores = [d.get("distance", 0.0) for d in documents]
        self._retrieval_data = {
            "candidate_count": candidate_count,
            "document_count": len(documents),
            "threshold_filtered": threshold_filtered,
            "avg_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
            "top_score": round(scores[0], 4) if scores else 0.0,
            "context_quality": context_quality,
            "mmr_applied": mmr_applied,
        }

    def set_generation_stats(
        self,
        answer: str,
        input_tokens: int,
        output_tokens: int,
        model: str,
    ) -> None:
        """Record generation outcome. Call after generator.generate()."""
        self._answer_length = len(answer)
        self._generation_data = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "model_used": model,
            "estimated_cost_usd": estimate_gemini_cost(model, input_tokens, output_tokens),
        }

    def mark_error(self, error: str) -> None:
        """Mark the request as failed. Call in exception handlers."""
        self._success = False
        self._error_message = str(error)[:500]

    def _build(self) -> RequestMetrics:
        """Construct the final RequestMetrics from accumulated data."""
        now = time.monotonic()

        retrieval_latency = (
            (self._retrieval_end - self._retrieval_start) * 1000
            if self._retrieval_start is not None and self._retrieval_end is not None
            else 0.0
        )
        generation_latency = (
            (self._generation_end - self._generation_start) * 1000
            if self._generation_start is not None and self._generation_end is not None
            else 0.0
        )
        total_latency = (now - self._request_start) * 1000

        retrieval = RetrievalMetrics(
            latency_ms=round(retrieval_latency, 2),
            **(self._retrieval_data or {}),
        )
        generation = GenerationMetrics(
            latency_ms=round(generation_latency, 2),
            **(self._generation_data or {}),
        )

        return RequestMetrics(
            user_id=self.user_id,
            session_id=self.session_id,
            query_length=self._query_length,
            answer_length=self._answer_length,
            total_latency_ms=round(total_latency, 2),
            retrieval=retrieval,
            generation=generation,
            timestamp=datetime.utcnow(),
            success=self._success,
            error_message=self._error_message,
        )

    async def save(self) -> None:
        """
        Persist metrics to Supabase metrics_requests table.
        Non-critical: errors are logged only; exceptions are never raised.
        Designed to be called via asyncio.create_task() (fire-and-forget).
        """
        try:
            from supabase import create_client
            from src.config import settings

            metrics = self._build()

            record = {
                "user_id": metrics.user_id,
                "session_id": metrics.session_id,
                "query_length": metrics.query_length,
                "answer_length": metrics.answer_length,
                "total_latency_ms": metrics.total_latency_ms,
                "success": metrics.success,
                "error_message": metrics.error_message,
                # Retrieval fields
                "retrieval_latency_ms": metrics.retrieval.latency_ms,
                "retrieval_candidate_count": metrics.retrieval.candidate_count,
                "retrieval_document_count": metrics.retrieval.document_count,
                "retrieval_threshold_filtered": metrics.retrieval.threshold_filtered,
                "retrieval_avg_score": metrics.retrieval.avg_score,
                "retrieval_top_score": metrics.retrieval.top_score,
                "context_quality": metrics.retrieval.context_quality,
                "mmr_applied": metrics.retrieval.mmr_applied,
                # Generation fields
                "generation_latency_ms": metrics.generation.latency_ms,
                "input_tokens": metrics.generation.input_tokens,
                "output_tokens": metrics.generation.output_tokens,
                "total_tokens": metrics.generation.total_tokens,
                "model_used": metrics.generation.model_used,
                "estimated_cost_usd": metrics.generation.estimated_cost_usd,
                "timestamp": metrics.timestamp.isoformat(),
            }

            def _insert() -> None:
                client = create_client(
                    settings.supabase_url, settings.supabase_service_role_key
                )
                client.table("metrics_requests").insert(record).execute()

            await asyncio.to_thread(_insert)
            logger.info(
                "Metrics saved: user=%s total=%.0fms tokens=%d cost=$%.6f",
                self.user_id,
                metrics.total_latency_ms,
                metrics.generation.total_tokens,
                metrics.generation.estimated_cost_usd,
            )
        except Exception as exc:
            logger.warning("Metrics save failed (non-critical): %s", exc)
