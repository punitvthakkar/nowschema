"""
Usage tracking and quota management service.
Tracks API usage and enforces monthly quotas.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .database import DatabaseService


# Monthly query quotas by plan tier
QUERY_QUOTAS = {
    "free": 1000,
    "starter": 10000,
    "professional": 100000,
    "enterprise": 1000000,  # Effectively unlimited
}


@dataclass
class QuotaStatus:
    """Current quota status for a tenant."""
    used: int
    limit: int
    remaining: int
    percentage_used: float
    reset_date: datetime
    is_exceeded: bool


@dataclass
class UsageStats:
    """Usage statistics for a tenant."""
    total_requests: int
    total_queries: int
    cache_hit_rate: float
    avg_latency_ms: float
    by_endpoint: Dict[str, int]
    by_day: Dict[str, int]
    period_start: datetime
    period_end: datetime


class UsageService:
    """Service for tracking usage and managing quotas."""

    def __init__(self, db: DatabaseService):
        """Initialize usage service."""
        self.db = db

    async def check_quota(self, tenant_id: str, plan_tier: str) -> QuotaStatus:
        """
        Check if tenant has remaining quota.

        Args:
            tenant_id: The tenant ID
            plan_tier: The tenant's subscription tier

        Returns:
            QuotaStatus with current usage and limits
        """
        limit = QUERY_QUOTAS.get(plan_tier, QUERY_QUOTAS["free"])
        used = await self.db.get_monthly_query_count(tenant_id)

        # Calculate reset date (first of next month)
        now = datetime.now(timezone.utc)
        if now.month == 12:
            reset_date = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            reset_date = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)

        remaining = max(0, limit - used)
        percentage = (used / limit) * 100 if limit > 0 else 100

        return QuotaStatus(
            used=used,
            limit=limit,
            remaining=remaining,
            percentage_used=percentage,
            reset_date=reset_date,
            is_exceeded=used >= limit,
        )

    async def can_proceed(self, tenant_id: str, plan_tier: str, query_count: int = 1) -> bool:
        """
        Check if a request can proceed without exceeding quota.

        Args:
            tenant_id: The tenant ID
            plan_tier: The tenant's subscription tier
            query_count: Number of queries in this request

        Returns:
            True if request can proceed, False if quota would be exceeded
        """
        status = await self.check_quota(tenant_id, plan_tier)
        return status.remaining >= query_count

    async def record_usage(
        self,
        tenant_id: str,
        api_key_id: str,
        endpoint: str,
        query_count: int,
        cache_hit: bool,
        latency_ms: int,
        status_code: int,
    ) -> None:
        """
        Record an API usage event.

        Args:
            tenant_id: The tenant ID
            api_key_id: The API key used
            endpoint: The endpoint called
            query_count: Number of queries in this request
            cache_hit: Whether the result was cached
            latency_ms: Request latency in milliseconds
            status_code: HTTP status code of response
        """
        await self.db.log_usage(
            tenant_id=tenant_id,
            api_key_id=api_key_id,
            endpoint=endpoint,
            query_count=query_count,
            cache_hit=cache_hit,
            latency_ms=latency_ms,
            status_code=status_code,
        )

    async def get_usage_stats(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> UsageStats:
        """
        Get detailed usage statistics for a tenant.

        Args:
            tenant_id: The tenant ID
            start_date: Start of reporting period
            end_date: End of reporting period

        Returns:
            UsageStats with detailed breakdowns
        """
        stats = await self.db.get_tenant_usage(tenant_id, start_date, end_date)

        return UsageStats(
            total_requests=stats["total_requests"],
            total_queries=stats["total_queries"],
            cache_hit_rate=stats["cache_hit_rate"],
            avg_latency_ms=stats["avg_latency_ms"],
            by_endpoint=stats["by_endpoint"],
            by_day={},  # Would need additional query grouping
            period_start=start_date,
            period_end=end_date,
        )

    async def get_current_month_stats(self, tenant_id: str) -> UsageStats:
        """Get usage stats for the current month."""
        now = datetime.now(timezone.utc)
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return await self.get_usage_stats(tenant_id, start_date, now)

    def get_quota_headers(self, status: QuotaStatus) -> dict:
        """
        Generate quota response headers.

        Returns headers dict to include in API response.
        """
        return {
            "X-Quota-Limit": str(status.limit),
            "X-Quota-Remaining": str(status.remaining),
            "X-Quota-Reset": status.reset_date.isoformat(),
        }

    async def send_quota_warning(
        self,
        tenant_id: str,
        status: QuotaStatus,
        threshold: float = 80.0,
    ) -> bool:
        """
        Check if quota warning should be sent.

        Returns True if warning threshold exceeded (for notification system).
        """
        return status.percentage_used >= threshold

    def get_upgrade_suggestion(self, current_tier: str) -> Optional[str]:
        """
        Suggest an upgrade tier based on current usage.

        Returns the suggested tier or None if already at highest.
        """
        tier_order = ["free", "starter", "professional", "enterprise"]
        try:
            current_index = tier_order.index(current_tier)
            if current_index < len(tier_order) - 1:
                return tier_order[current_index + 1]
        except ValueError:
            return "starter"
        return None


class InMemoryUsageService:
    """
    Fallback in-memory usage tracking for when database is unavailable.
    Not suitable for production.
    """

    def __init__(self):
        """Initialize in-memory usage tracker."""
        self._usage = {}  # tenant_id -> monthly_count

    async def check_quota(self, tenant_id: str, plan_tier: str) -> QuotaStatus:
        """Check quota from memory."""
        limit = QUERY_QUOTAS.get(plan_tier, QUERY_QUOTAS["free"])
        used = self._usage.get(tenant_id, 0)

        now = datetime.now(timezone.utc)
        if now.month == 12:
            reset_date = now.replace(year=now.year + 1, month=1, day=1)
        else:
            reset_date = now.replace(month=now.month + 1, day=1)

        remaining = max(0, limit - used)
        percentage = (used / limit) * 100 if limit > 0 else 100

        return QuotaStatus(
            used=used,
            limit=limit,
            remaining=remaining,
            percentage_used=percentage,
            reset_date=reset_date,
            is_exceeded=used >= limit,
        )

    async def can_proceed(self, tenant_id: str, plan_tier: str, query_count: int = 1) -> bool:
        """Check if request can proceed."""
        status = await self.check_quota(tenant_id, plan_tier)
        return status.remaining >= query_count

    async def record_usage(
        self,
        tenant_id: str,
        api_key_id: str,
        endpoint: str,
        query_count: int,
        **kwargs,
    ) -> None:
        """Record usage in memory."""
        self._usage[tenant_id] = self._usage.get(tenant_id, 0) + query_count

    def get_quota_headers(self, status: QuotaStatus) -> dict:
        """Generate quota headers."""
        return {
            "X-Quota-Limit": str(status.limit),
            "X-Quota-Remaining": str(status.remaining),
            "X-Quota-Reset": status.reset_date.isoformat(),
        }
