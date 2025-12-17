"""
Caching service using Upstash Redis.
Caches search results to reduce latency and GPU costs.
"""
import json
import hashlib
from datetime import datetime, timezone
from typing import Optional, Any, List
from dataclasses import dataclass

try:
    from upstash_redis import Redis
except ImportError:
    Redis = None


# Cache TTL by plan tier (seconds)
CACHE_TTL = {
    "free": 3600,       # 1 hour
    "starter": 86400,   # 24 hours
    "professional": 86400,  # 24 hours
    "enterprise": 86400,    # 24 hours
}

# Default TTL
DEFAULT_TTL = 3600


@dataclass
class CacheResult:
    """Result of cache lookup."""
    hit: bool
    data: Optional[Any] = None
    cached_at: Optional[datetime] = None


class CacheService:
    """Service for caching using Upstash Redis."""

    def __init__(self, redis_url: str, redis_token: str):
        """Initialize cache service."""
        if Redis is None:
            raise RuntimeError("upstash-redis not available")

        self.redis = Redis(url=redis_url, token=redis_token)

    def _make_key(self, query: str, top_k: int, tenant_id: str = None) -> str:
        """
        Generate a cache key for a search query.

        Keys are tenant-scoped to ensure isolation.
        """
        # Normalize query for better cache hits
        normalized_query = query.lower().strip()

        # Create hash of query parameters
        key_data = f"{normalized_query}:{top_k}"
        query_hash = hashlib.md5(key_data.encode()).hexdigest()[:16]

        if tenant_id:
            return f"uniclass:cache:{tenant_id}:{query_hash}"
        return f"uniclass:cache:global:{query_hash}"

    async def get(
        self,
        query: str,
        top_k: int,
        tenant_id: str = None,
    ) -> CacheResult:
        """
        Get cached search results.

        Args:
            query: The search query
            top_k: Number of results requested
            tenant_id: Optional tenant ID for scoped caching

        Returns:
            CacheResult with hit status and data if found
        """
        key = self._make_key(query, top_k, tenant_id)

        try:
            cached = self.redis.get(key)
            if cached:
                data = json.loads(cached)
                return CacheResult(
                    hit=True,
                    data=data.get("results"),
                    cached_at=datetime.fromisoformat(data.get("cached_at")),
                )
            return CacheResult(hit=False)
        except Exception as e:
            print(f"Cache get error: {e}")
            return CacheResult(hit=False)

    async def set(
        self,
        query: str,
        top_k: int,
        results: List[dict],
        tenant_id: str = None,
        plan_tier: str = "free",
    ) -> bool:
        """
        Cache search results.

        Args:
            query: The search query
            top_k: Number of results
            results: Search results to cache
            tenant_id: Optional tenant ID for scoped caching
            plan_tier: Tenant's plan tier (affects TTL)

        Returns:
            True if cached successfully, False otherwise
        """
        key = self._make_key(query, top_k, tenant_id)
        ttl = CACHE_TTL.get(plan_tier, DEFAULT_TTL)

        try:
            data = {
                "results": results,
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "query": query,
                "top_k": top_k,
            }
            self.redis.setex(key, ttl, json.dumps(data))
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False

    async def delete(self, query: str, top_k: int, tenant_id: str = None) -> bool:
        """Delete a specific cache entry."""
        key = self._make_key(query, top_k, tenant_id)
        try:
            self.redis.delete(key)
            return True
        except Exception:
            return False

    async def clear_tenant(self, tenant_id: str) -> int:
        """
        Clear all cache entries for a tenant.

        Returns number of keys deleted.
        """
        pattern = f"uniclass:cache:{tenant_id}:*"
        try:
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
            return len(keys) if keys else 0
        except Exception as e:
            print(f"Cache clear error: {e}")
            return 0

    async def get_stats(self, tenant_id: str = None) -> dict:
        """Get cache statistics."""
        try:
            if tenant_id:
                pattern = f"uniclass:cache:{tenant_id}:*"
            else:
                pattern = "uniclass:cache:*"

            keys = self.redis.keys(pattern)
            return {
                "cached_queries": len(keys) if keys else 0,
                "tenant_id": tenant_id,
            }
        except Exception:
            return {"cached_queries": 0, "tenant_id": tenant_id}


class InMemoryCacheService:
    """
    Fallback in-memory cache for when Redis is unavailable.
    Not suitable for production with multiple instances.
    """

    def __init__(self, max_size: int = 1000):
        """Initialize in-memory cache."""
        self._cache = {}
        self._max_size = max_size

    def _make_key(self, query: str, top_k: int, tenant_id: str = None) -> str:
        """Generate cache key."""
        normalized_query = query.lower().strip()
        key_data = f"{normalized_query}:{top_k}"
        query_hash = hashlib.md5(key_data.encode()).hexdigest()[:16]

        if tenant_id:
            return f"{tenant_id}:{query_hash}"
        return f"global:{query_hash}"

    async def get(
        self,
        query: str,
        top_k: int,
        tenant_id: str = None,
    ) -> CacheResult:
        """Get from in-memory cache."""
        key = self._make_key(query, top_k, tenant_id)

        if key in self._cache:
            entry = self._cache[key]
            # Check expiration
            if entry["expires_at"] > datetime.now(timezone.utc):
                return CacheResult(
                    hit=True,
                    data=entry["results"],
                    cached_at=entry["cached_at"],
                )
            else:
                del self._cache[key]

        return CacheResult(hit=False)

    async def set(
        self,
        query: str,
        top_k: int,
        results: List[dict],
        tenant_id: str = None,
        plan_tier: str = "free",
    ) -> bool:
        """Set in in-memory cache."""
        # Evict if at max size
        if len(self._cache) >= self._max_size:
            # Remove oldest entry
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]["cached_at"])
            del self._cache[oldest_key]

        key = self._make_key(query, top_k, tenant_id)
        ttl = CACHE_TTL.get(plan_tier, DEFAULT_TTL)
        now = datetime.now(timezone.utc)

        self._cache[key] = {
            "results": results,
            "cached_at": now,
            "expires_at": datetime.fromtimestamp(now.timestamp() + ttl, tz=timezone.utc),
        }
        return True

    async def delete(self, query: str, top_k: int, tenant_id: str = None) -> bool:
        """Delete from in-memory cache."""
        key = self._make_key(query, top_k, tenant_id)
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    async def clear_tenant(self, tenant_id: str) -> int:
        """Clear tenant's cache entries."""
        prefix = f"{tenant_id}:"
        keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
        for key in keys_to_delete:
            del self._cache[key]
        return len(keys_to_delete)

    async def get_stats(self, tenant_id: str = None) -> dict:
        """Get cache stats."""
        if tenant_id:
            count = sum(1 for k in self._cache if k.startswith(f"{tenant_id}:"))
        else:
            count = len(self._cache)
        return {"cached_queries": count, "tenant_id": tenant_id}
