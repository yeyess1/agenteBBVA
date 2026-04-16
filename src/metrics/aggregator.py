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
        }
