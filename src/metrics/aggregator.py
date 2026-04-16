"""
MetricsAggregator: Queries metrics_requests from Supabase and returns
pre-computed aggregations for the /api/metrics endpoints.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MetricsAggregator:
    """
    Reads from metrics_requests table and computes aggregated statistics.
    All Supabase queries are sync and executed via asyncio.to_thread.
    """

    def _client(self):
        from supabase import create_client
        from src.config import settings
        return create_client(settings.supabase_url, settings.supabase_service_role_key)

    async def get_global_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        Return aggregated metrics for ALL users over the last N hours.

        Args:
            hours: Lookback window in hours (default 24)

        Returns:
            Aggregated metrics dict
        """
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

        def _query():
            return (
                self._client()
                .table("metrics_requests")
                .select("*")
                .gte("timestamp", since)
                .order("timestamp", desc=True)
                .execute()
                .data or []
            )

        records = await asyncio.to_thread(_query)
        return self._aggregate(records)

    async def get_user_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Return aggregated metrics for a single user over the last N days.

        Args:
            user_id: Target user
            days: Lookback window in days (default 30)

        Returns:
            Aggregated metrics dict scoped to user
        """
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()

        def _query():
            return (
                self._client()
                .table("metrics_requests")
                .select("*")
                .eq("user_id", user_id)
                .gte("timestamp", since)
                .order("timestamp", desc=True)
                .execute()
                .data or []
            )

        records = await asyncio.to_thread(_query)
        return self._aggregate(records, user_id=user_id)

    def _aggregate(
        self, records: list, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Compute aggregate statistics from a list of raw metric records."""
        if not records:
            return self._empty(user_id)

        total = len(records)
        successful = [r for r in records if r.get("success", True)]

        # ── Deflection Rate: successful queries with medium+ context quality ────
        deflected = [
            r for r in successful
            if r.get("context_quality", "none") in ["high", "medium"]
        ]
        deflection_rate = round(len(deflected) / total, 4) if total > 0 else 0.0

        # ── Latency ────────────────────────────────────────────
        total_lats = [r.get("total_latency_ms", 0.0) for r in records]
        retr_lats = [r.get("retrieval_latency_ms", 0.0) for r in records]
        gen_lats = [r.get("generation_latency_ms", 0.0) for r in records]

        # ── Tokens ─────────────────────────────────────────────
        total_input = sum(r.get("input_tokens", 0) for r in records)
        total_output = sum(r.get("output_tokens", 0) for r in records)
        total_tokens = sum(r.get("total_tokens", 0) for r in records)

        # ── Cost ───────────────────────────────────────────────
        total_cost = sum(r.get("estimated_cost_usd", 0.0) for r in records)

        # ── Cost Comparison: RAG vs Human ──────────────────────
        human_cost_per_query = 9.0  # USD per human-handled query
        total_human_cost = total * human_cost_per_query
        total_savings_usd = total_human_cost - total_cost
        avg_rag_cost_per_query = round(total_cost / total, 8) if total > 0 else 0.0

        # ── Context quality distribution ───────────────────────
        quality_counts: Dict[str, int] = {"high": 0, "medium": 0, "low": 0, "none": 0}
        for r in records:
            q = r.get("context_quality", "none")
            if q in quality_counts:
                quality_counts[q] += 1

        # ── Retrieval relevance ────────────────────────────────
        avg_scores = [
            r["retrieval_avg_score"]
            for r in records
            if r.get("retrieval_avg_score") is not None
        ]

        # ── Top Keywords from queries ──────────────────────────
        top_keywords = self._extract_top_keywords([r.get("query_text", "") for r in records])

        unique_users = len({r.get("user_id", "") for r in records})

        def safe_avg(lst: list) -> float:
            return round(sum(lst) / len(lst), 2) if lst else 0.0

        return {
            "period": {
                "from": min(r.get("timestamp", "") for r in records),
                "to": max(r.get("timestamp", "") for r in records),
            },
            "requests": {
                "total": total,
                "successful": len(successful),
                "failed": total - len(successful),
                "success_rate": round(len(successful) / total, 4) if total > 0 else 0.0,
            },
            "users": {
                "unique": unique_users,
                "scoped_user_id": user_id,
                "avg_requests_per_user": (
                    round(total / unique_users, 2) if unique_users > 0 else 0.0
                ),
            },
            "business_metrics": {
                "deflection_rate": deflection_rate,
                "deflected_cases": len(deflected),
                "cost_comparison": {
                    "rag_total_usd": round(total_cost, 6),
                    "human_total_usd": round(total_human_cost, 2),
                    "savings_total_usd": round(total_savings_usd, 2),
                    "rag_per_query_usd": avg_rag_cost_per_query,
                    "human_per_query_usd": human_cost_per_query,
                },
            },
            "latency_ms": {
                "avg_total": safe_avg(total_lats),
                "avg_retrieval": safe_avg(retr_lats),
                "avg_generation": safe_avg(gen_lats),
                "max_total": round(max(total_lats), 2) if total_lats else 0.0,
                "min_total": round(min(total_lats), 2) if total_lats else 0.0,
            },
            "tokens": {
                "total_input": total_input,
                "total_output": total_output,
                "total": total_tokens,
                "avg_input_per_request": (
                    round(total_input / total, 1) if total > 0 else 0.0
                ),
                "avg_output_per_request": (
                    round(total_output / total, 1) if total > 0 else 0.0
                ),
                "avg_total_per_request": (
                    round(total_tokens / total, 1) if total > 0 else 0.0
                ),
            },
            "costs": {
                "total_usd": round(total_cost, 6),
                "avg_per_request_usd": (
                    round(total_cost / total, 8) if total > 0 else 0.0
                ),
            },
            "retrieval": {
                "avg_relevance_score": safe_avg(avg_scores),
                "context_quality_distribution": {
                    k: round(v / total, 4) if total > 0 else 0.0
                    for k, v in quality_counts.items()
                },
                "mmr_applied_count": sum(
                    1 for r in records if r.get("mmr_applied", False)
                ),
            },
            "insights": {
                "top_keywords": top_keywords,
            },
        }

    @staticmethod
    def _empty(user_id: Optional[str] = None) -> Dict[str, Any]:
        return {
            "period": {"from": None, "to": None},
            "requests": {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "success_rate": 0.0,
            },
            "users": {
                "unique": 0,
                "scoped_user_id": user_id,
                "avg_requests_per_user": 0.0,
            },
            "business_metrics": {
                "deflection_rate": 0.0,
                "deflected_cases": 0,
                "cost_comparison": {
                    "rag_total_usd": 0.0,
                    "human_total_usd": 0.0,
                    "savings_total_usd": 0.0,
                    "rag_per_query_usd": 0.0,
                    "human_per_query_usd": 9.0,
                },
            },
            "latency_ms": {
                "avg_total": 0.0,
                "avg_retrieval": 0.0,
                "avg_generation": 0.0,
                "max_total": 0.0,
                "min_total": 0.0,
            },
            "tokens": {
                "total_input": 0,
                "total_output": 0,
                "total": 0,
                "avg_input_per_request": 0.0,
                "avg_output_per_request": 0.0,
                "avg_total_per_request": 0.0,
            },
            "costs": {"total_usd": 0.0, "avg_per_request_usd": 0.0},
            "retrieval": {
                "avg_relevance_score": 0.0,
                "context_quality_distribution": {
                    "high": 0.0,
                    "medium": 0.0,
                    "low": 0.0,
                    "none": 0.0,
                },
                "mmr_applied_count": 0,
            },
            "insights": {
                "top_keywords": [],
            },
        }

    @staticmethod
    def _extract_top_keywords(queries: list, top_n: int = 10) -> list:
        """
        Extract top keywords from a list of queries.
        Filters out common stopwords and returns word frequency ranking.

        Args:
            queries: List of query strings
            top_n: Number of top keywords to return

        Returns:
            List of dicts with {"keyword": str, "count": int, "frequency": float}
        """
        import re
        from collections import Counter

        # Common stopwords in Spanish and English
        stopwords = {
            "el", "la", "de", "que", "y", "a", "en", "un", "es", "se", "los", "las",
            "una", "por", "con", "no", "una", "su", "al", "o", "este", "sí", "porque",
            "esta", "son", "está", "fue", "ha", "hay", "como", "más", "pero", "sus",
            "the", "a", "an", "and", "or", "of", "in", "to", "is", "be", "are", "was",
            "were", "been", "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "can", "for", "if", "as", "on", "at",
            "me", "what", "which", "who", "how", "why", "cuando", "donde", "como",
        }

        # Extract and clean words
        words = []
        for query in queries:
            if not query:
                continue
            # Convert to lowercase and split by non-word characters
            cleaned = re.findall(r"\b\w+\b", query.lower())
            # Filter stopwords and short words
            filtered = [w for w in cleaned if w not in stopwords and len(w) > 2]
            words.extend(filtered)

        if not words:
            return []

        # Count frequency
        word_counts = Counter(words)
        top_keywords = word_counts.most_common(top_n)

        total_words = sum(word_counts.values())
        return [
            {
                "keyword": keyword,
                "count": count,
                "frequency": round(count / total_words, 4),
            }
            for keyword, count in top_keywords
        ]
