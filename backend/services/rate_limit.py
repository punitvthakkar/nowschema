"""
Rate limiting service using Upstash Redis.
Implements sliding window rate limiting with tiered limits.
"""
from datetime import datetime, timezone
from typing import Optional, Tuple
from dataclasses import dataclass

try:
    from upstash_redis import Redis
    from upstash_ratelimit import Ratelimit, SlidingWindow
except ImportError:
    Redis = None
    Ratelimit = None
    SlidingWindow = None


# Rate limits by plan tier (requests per minute)
RATE_LIMITS = {
    "free": 10,
    "starter": 60,
    "professional": 300,
    "enterprise": 1000,
}

# Window duration in seconds
WINDOW_DURATION = 60


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    allowed: bool
    limit: int
    remaining: int
    reset_at: datetime
    retry_after: Optional[int] = None  # Seconds until reset if rate limited


class RateLimitService:
    """Service for rate limiting using Upstash Redis."""

    def __init__(self, redis_url: str, redis_token: str):
        """Initialize rate limit service."""
        if Redis is None:
            raise RuntimeError("upstash-redis not available")

        self.redis = Redis(url=redis_url, token=redis_token)
        self._limiters = {}

    def _get_limiter(self, plan_tier: str, custom_limit: int = None) -> "Ratelimit":
        """Get or create a rate limiter for a plan tier."""
        limit = custom_limit or RATE_LIMITS.get(plan_tier, RATE_LIMITS["free"])
        cache_key = f"{plan_tier}_{limit}"

        if cache_key not in self._limiters:
            if Ratelimit is None:
                raise RuntimeError("upstash-ratelimit not available")

            self._limiters[cache_key] = Ratelimit(
                redis=self.redis,
                limiter=SlidingWindow(max_requests=limit, window=WINDOW_DURATION),
                prefix=f"uniclass:ratelimit:{plan_tier}",
            )

        return self._limiters[cache_key]

    async def check(
        self,
        tenant_id: str,
        plan_tier: str,
        custom_limit: int = None,
    ) -> RateLimitResult:
        """
        Check if a request is allowed under rate limits.

        Args:
            tenant_id: The tenant making the request
            plan_tier: The tenant's subscription tier
            custom_limit: Optional per-key rate limit override

        Returns:
            RateLimitResult with allow/deny decision and metadata
        """
        limiter = self._get_limiter(plan_tier, custom_limit)
        limit = custom_limit or RATE_LIMITS.get(plan_tier, RATE_LIMITS["free"])

        try:
            result = limiter.limit(tenant_id)

            reset_at = datetime.fromtimestamp(result.reset / 1000, tz=timezone.utc)

            if result.allowed:
                return RateLimitResult(
                    allowed=True,
                    limit=limit,
                    remaining=result.remaining,
                    reset_at=reset_at,
                )
            else:
                retry_after = max(0, int((result.reset - datetime.now(timezone.utc).timestamp() * 1000) / 1000))
                return RateLimitResult(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset_at=reset_at,
                    retry_after=retry_after,
                )
        except Exception as e:
            # On error, allow the request but log
            print(f"Rate limit check error: {e}")
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit - 1,
                reset_at=datetime.now(timezone.utc),
            )

    async def get_usage(self, tenant_id: str, plan_tier: str) -> Tuple[int, int]:
        """
        Get current rate limit usage for a tenant.

        Returns:
            Tuple of (used, limit)
        """
        limit = RATE_LIMITS.get(plan_tier, RATE_LIMITS["free"])

        try:
            # Get current window usage from Redis
            key = f"uniclass:ratelimit:{plan_tier}:{tenant_id}"
            count = self.redis.get(key)
            used = int(count) if count else 0
            return used, limit
        except Exception:
            return 0, limit

    def get_headers(self, result: RateLimitResult) -> dict:
        """
        Generate rate limit response headers.

        Returns headers dict to include in API response.
        """
        headers = {
            "X-RateLimit-Limit": str(result.limit),
            "X-RateLimit-Remaining": str(result.remaining),
            "X-RateLimit-Reset": str(int(result.reset_at.timestamp())),
        }

        if not result.allowed and result.retry_after:
            headers["Retry-After"] = str(result.retry_after)

        return headers


class InMemoryRateLimitService:
    """
    Fallback in-memory rate limiter for when Redis is unavailable.
    Not suitable for production with multiple instances.
    """

    def __init__(self):
        """Initialize in-memory rate limiter."""
        self._windows = {}  # tenant_id -> (window_start, count)

    async def check(
        self,
        tenant_id: str,
        plan_tier: str,
        custom_limit: int = None,
    ) -> RateLimitResult:
        """Check rate limit using in-memory storage."""
        limit = custom_limit or RATE_LIMITS.get(plan_tier, RATE_LIMITS["free"])
        now = datetime.now(timezone.utc)
        window_start = now.replace(second=0, microsecond=0)

        key = tenant_id
        if key in self._windows:
            stored_start, count = self._windows[key]
            if stored_start == window_start:
                if count >= limit:
                    reset_at = window_start.replace(second=WINDOW_DURATION)
                    retry_after = int((reset_at - now).total_seconds())
                    return RateLimitResult(
                        allowed=False,
                        limit=limit,
                        remaining=0,
                        reset_at=reset_at,
                        retry_after=retry_after,
                    )
                self._windows[key] = (window_start, count + 1)
                return RateLimitResult(
                    allowed=True,
                    limit=limit,
                    remaining=limit - count - 1,
                    reset_at=window_start.replace(second=WINDOW_DURATION),
                )

        # New window
        self._windows[key] = (window_start, 1)
        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=limit - 1,
            reset_at=window_start.replace(second=WINDOW_DURATION),
        )

    async def get_usage(self, tenant_id: str, plan_tier: str) -> Tuple[int, int]:
        """Get current usage."""
        limit = RATE_LIMITS.get(plan_tier, RATE_LIMITS["free"])
        now = datetime.now(timezone.utc)
        window_start = now.replace(second=0, microsecond=0)

        if tenant_id in self._windows:
            stored_start, count = self._windows[tenant_id]
            if stored_start == window_start:
                return count, limit

        return 0, limit

    def get_headers(self, result: RateLimitResult) -> dict:
        """Generate rate limit headers."""
        headers = {
            "X-RateLimit-Limit": str(result.limit),
            "X-RateLimit-Remaining": str(result.remaining),
            "X-RateLimit-Reset": str(int(result.reset_at.timestamp())),
        }

        if not result.allowed and result.retry_after:
            headers["Retry-After"] = str(result.retry_after)

        return headers
