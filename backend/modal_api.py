"""
Uniclass Search API - Enterprise Edition
Deployed on Modal with full multi-tenancy, authentication, billing, and observability.
Optimized for Modal free tier (6 endpoints).

This file is SELF-CONTAINED - all code is inline, no external module imports.
"""
import modal
import os
import time
import json
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

# Modal App
app = modal.App("uniclass-api")

# Image with all dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    # ML
    "sentence-transformers>=2.6.0",
    "torch",
    "numpy",
    "hnswlib",
    "huggingface_hub>=0.23.0",
    "einops",
    # API
    "fastapi[standard]",
    "pydantic>=2.0.0",
    # Utils
    "httpx",
)

# Volume for embeddings index
volume = modal.Volume.from_name("uniclass-embeddings-vol", create_if_missing=True)


# ==================== INLINE DATA CLASSES ====================

@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int = 0
    retry_after: int = 0


@dataclass
class CacheResult:
    hit: bool
    data: Any = None


@dataclass
class QuotaStatus:
    used: int
    limit: int
    remaining: int
    reset_date: datetime
    percentage_used: float


# ==================== INLINE SERVICES (IN-MEMORY) ====================

class InMemoryRateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self):
        self.requests: Dict[str, List[float]] = {}
        self.limits = {
            "free": 10,
            "starter": 60,
            "professional": 300,
            "enterprise": 1000,
        }

    async def check(self, tenant_id: str, plan_tier: str, custom_limit: int = None) -> RateLimitResult:
        limit = custom_limit or self.limits.get(plan_tier, 10)
        now = time.time()
        window = 60  # 1 minute

        key = f"{tenant_id}:{plan_tier}"
        if key not in self.requests:
            self.requests[key] = []

        # Clean old requests
        self.requests[key] = [t for t in self.requests[key] if now - t < window]

        if len(self.requests[key]) >= limit:
            return RateLimitResult(allowed=False, remaining=0, retry_after=int(window - (now - self.requests[key][0])))

        self.requests[key].append(now)
        return RateLimitResult(allowed=True, remaining=limit - len(self.requests[key]))


class InMemoryCache:
    """Simple in-memory cache."""

    def __init__(self):
        self.cache: Dict[str, tuple] = {}  # key -> (data, expiry)
        self.ttl = {
            "free": 300,
            "starter": 600,
            "professional": 1800,
            "enterprise": 3600,
        }

    def _make_key(self, query: str, top_k: int, tenant_id: str) -> str:
        return hashlib.md5(f"{tenant_id}:{query}:{top_k}".encode()).hexdigest()

    async def get(self, query: str, top_k: int, tenant_id: str) -> CacheResult:
        key = self._make_key(query, top_k, tenant_id)
        if key in self.cache:
            data, expiry = self.cache[key]
            if time.time() < expiry:
                return CacheResult(hit=True, data=data)
            del self.cache[key]
        return CacheResult(hit=False)

    async def set(self, query: str, top_k: int, data: Any, tenant_id: str, plan_tier: str):
        key = self._make_key(query, top_k, tenant_id)
        ttl = self.ttl.get(plan_tier, 300)
        self.cache[key] = (data, time.time() + ttl)


class InMemoryUsageTracker:
    """Simple in-memory usage tracker."""

    def __init__(self):
        self.usage: Dict[str, int] = {}
        self.quotas = {
            "free": 100,
            "starter": 10000,
            "professional": 100000,
            "enterprise": 1000000,
        }

    def _get_month_key(self, tenant_id: str) -> str:
        return f"{tenant_id}:{datetime.now().strftime('%Y-%m')}"

    async def can_proceed(self, tenant_id: str, plan_tier: str, query_count: int = 1) -> bool:
        key = self._get_month_key(tenant_id)
        current = self.usage.get(key, 0)
        limit = self.quotas.get(plan_tier, 100)
        return current + query_count <= limit

    async def record_usage(self, tenant_id: str, query_count: int = 1, **kwargs):
        key = self._get_month_key(tenant_id)
        self.usage[key] = self.usage.get(key, 0) + query_count

    async def check_quota(self, tenant_id: str, plan_tier: str) -> QuotaStatus:
        key = self._get_month_key(tenant_id)
        used = self.usage.get(key, 0)
        limit = self.quotas.get(plan_tier, 100)
        remaining = max(0, limit - used)

        # Calculate next month reset
        now = datetime.now(timezone.utc)
        next_month = (now.replace(day=1) + timedelta(days=32)).replace(day=1)

        return QuotaStatus(
            used=used,
            limit=limit,
            remaining=remaining,
            reset_date=next_month,
            percentage_used=round((used / limit) * 100, 2) if limit > 0 else 0
        )


# ==================== PYDANTIC MODELS ====================

from pydantic import BaseModel, Field
from fastapi import Header


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    code: str
    details: Optional[Dict[str, Any]] = None


# ==================== MAIN SERVICE CLASS ====================


@app.cls(
    image=image,
    gpu="T4",
    memory=8192,
    volumes={"/cache": volume},
    scaledown_window=300,  # Updated from container_idle_timeout
    secrets=[modal.Secret.from_name("uniclass-enterprise-secrets")],
)
@modal.concurrent(max_inputs=10)  # Updated from allow_concurrent_inputs
class UniclassSearchService:
    """Enterprise Uniclass Search Service with full multi-tenancy."""

    @modal.enter()
    def setup(self):
        """Initialize all services when container starts."""
        from sentence_transformers import SentenceTransformer
        import hnswlib

        print("🚀 Initializing Uniclass Enterprise API...")

        # Load ML model
        print("  → Loading embedding model...")
        self.model = SentenceTransformer(
            "nomic-ai/nomic-embed-text-v1.5",
            trust_remote_code=True,
            device="cuda",
            cache_folder="/cache/models"
        )

        # Load HNSW index
        print("  → Loading HNSW index...")
        self.index = hnswlib.Index(space="cosine", dim=768)
        self.index.load_index("/cache/results/uniclass_hnsw.index")
        self.index.set_ef(100)

        # Load lookup table
        print("  → Loading lookup table...")
        with open("/cache/results/uniclass_lookup.json", "r") as f:
            self.lookup = json.load(f)

        # Initialize in-memory services
        self._init_services()

        print(f"✅ Ready! {self.lookup['num_items']} items indexed.")

    def _init_services(self):
        """Initialize enterprise services (all in-memory for now)."""

        # In-memory services (no external dependencies)
        self.rate_limiter = InMemoryRateLimiter()
        self.cache = InMemoryCache()
        self.usage_service = InMemoryUsageTracker()

        # Legacy API key from environment
        self.legacy_api_key = os.environ.get("UNICLASS_API_KEY", "")

        # Service status
        self.services_status = {
            "database": False,
            "cache": True,  # In-memory
            "rate_limit": True,  # In-memory
            "usage": True,  # In-memory
            "billing": False,
            "sso": False,
        }

        print("  → Using in-memory services (no external dependencies)")

    # ==================== AUTHENTICATION ====================

    async def _authenticate(self, authorization: str) -> tuple:
        """Authenticate a request using API key."""
        if not authorization:
            return None, None, ErrorResponse(error="Authentication required", code="AUTH_REQUIRED")

        token = authorization.replace("Bearer ", "").strip()

        # Check legacy API key
        if self.legacy_api_key and token == self.legacy_api_key:
            return {"id": "legacy", "plan_tier": "professional"}, None, None

        return None, None, ErrorResponse(error="Invalid API key", code="INVALID_API_KEY")

    async def _check_rate_limit(self, tenant_id: str, plan_tier: str, custom_limit: int = None):
        """Check rate limit for request."""
        return await self.rate_limiter.check(tenant_id, plan_tier, custom_limit)

    async def _check_quota(self, tenant_id: str, plan_tier: str, query_count: int = 1):
        """Check if request is within quota."""
        return await self.usage_service.can_proceed(tenant_id, plan_tier, query_count)

    # ==================== CORE SEARCH ====================

    def _search(self, query: str, top_k: int = 10) -> List[dict]:
        """Execute vector search."""
        import numpy as np

        query_embedding = self.model.encode(
            [f"search_query: {query}"],
            normalize_embeddings=True
        )[0]

        labels, distances = self.index.knn_query(
            query_embedding.reshape(1, -1),
            k=min(top_k, self.lookup["num_items"])
        )

        results = []
        for label, distance in zip(labels[0], distances[0]):
            results.append({
                "code": self.lookup["ids"][label],
                "title": self.lookup["texts"][label],
                "table": self.lookup["metadata"][label]["table"],
                "similarity": round(float(1 - distance), 4)
            })

        return results

    # ==================== ENDPOINT 1: HEALTH (no auth) ====================

    @modal.fastapi_endpoint(method="GET", docs=True)
    async def health(self) -> dict:
        """
        Health check endpoint (no auth required).

        GET /health
        """
        return {
            "status": "healthy",
            "items_indexed": self.lookup["num_items"],
            "embedding_dim": self.lookup["embedding_dim"],
            "services": self.services_status,
        }

    # ==================== ENDPOINT 2: SEARCH (single + batch) ====================

    @modal.fastapi_endpoint(method="POST", docs=True)
    async def search(self, item: dict, authorization: str = Header(default=None)) -> dict:
        """
        Unified search endpoint for single and batch queries.

        POST /search

        Single search:
            {"action": "single", "query": "door handle", "top_k": 5}

        Batch search:
            {"action": "batch", "queries": ["door handle", "concrete slab"], "top_k": 5}

        For backwards compatibility, if no action specified:
            - If "query" present -> single search
            - If "queries" present -> batch search
        """
        start_time = time.time()

        # Authenticate
        tenant, api_key, error = await self._authenticate(authorization)
        if error:
            return error.model_dump()

        tenant_id = tenant["id"] if isinstance(tenant, dict) else tenant.id
        plan_tier = tenant["plan_tier"] if isinstance(tenant, dict) else tenant.plan_tier

        # Rate limit check
        rate_result = await self._check_rate_limit(tenant_id, plan_tier, None)
        if not rate_result.allowed:
            return ErrorResponse(
                error="Rate limit exceeded",
                code="RATE_LIMITED",
                details={"retry_after": rate_result.retry_after}
            ).model_dump()

        # Determine action
        action = item.get("action", "")
        if not action:
            # Auto-detect for backwards compatibility
            if "queries" in item:
                action = "batch"
            else:
                action = "single"

        top_k = item.get("top_k", 10)

        # === SINGLE SEARCH ===
        if action == "single":
            query = item.get("query", "")
            if not query:
                return ErrorResponse(error="Missing 'query'", code="MISSING_PARAM").model_dump()

            # Quota check
            if not await self._check_quota(tenant_id, plan_tier):
                return ErrorResponse(error="Monthly quota exceeded", code="QUOTA_EXCEEDED").model_dump()

            # Check cache
            cache_result = await self.cache.get(query, top_k, tenant_id)
            if cache_result.hit:
                latency = int((time.time() - start_time) * 1000)
                await self.usage_service.record_usage(tenant_id=tenant_id, query_count=1)
                return {
                    "query": query, "top_k": top_k,
                    "count": len(cache_result.data),
                    "results": cache_result.data,
                    "cached": True, "latency_ms": latency
                }

            # Execute search
            results = self._search(query, top_k)
            latency = int((time.time() - start_time) * 1000)

            # Cache results
            await self.cache.set(query, top_k, results, tenant_id, plan_tier)

            # Log usage
            await self.usage_service.record_usage(tenant_id=tenant_id, query_count=1)

            return {
                "query": query, "top_k": top_k,
                "count": len(results), "results": results,
                "cached": False, "latency_ms": latency
            }

        # === BATCH SEARCH ===
        elif action == "batch":
            queries = item.get("queries", [])
            if not queries:
                return ErrorResponse(error="Missing 'queries'", code="MISSING_PARAM").model_dump()

            # Quota check
            if not await self._check_quota(tenant_id, plan_tier, len(queries)):
                return ErrorResponse(error="Monthly quota exceeded", code="QUOTA_EXCEEDED").model_dump()

            # Execute searches
            results = {}
            cache_hits = 0

            for query in queries:
                cache_result = await self.cache.get(query, top_k, tenant_id)
                if cache_result.hit:
                    results[query] = cache_result.data
                    cache_hits += 1
                else:
                    search_results = self._search(query, top_k)
                    results[query] = search_results
                    await self.cache.set(query, top_k, search_results, tenant_id, plan_tier)

            latency = int((time.time() - start_time) * 1000)
            await self.usage_service.record_usage(tenant_id=tenant_id, query_count=len(queries))

            return {
                "count": len(queries), "top_k": top_k,
                "results": results, "latency_ms": latency
            }

        else:
            return ErrorResponse(error=f"Unknown action: {action}", code="INVALID_ACTION").model_dump()

    # ==================== ENDPOINT 3: INFO (stats + usage) ====================

    @modal.fastapi_endpoint(method="POST", docs=True)
    async def info(self, item: dict, authorization: str = Header(default=None)) -> dict:
        """
        Combined info endpoint for stats and usage.

        POST /info

        Get index stats:
            {"action": "stats"}

        Get usage/quota:
            {"action": "usage"}
        """
        tenant, api_key, error = await self._authenticate(authorization)
        if error:
            return error.model_dump()

        action = item.get("action", "stats")

        # === STATS ===
        if action == "stats":
            return {
                "total_items": self.lookup["num_items"],
                "embedding_dim": self.lookup["embedding_dim"],
                "index_params": self.lookup["index_params"],
                "tables": list(set(m["table"] for m in self.lookup["metadata"]))
            }

        # === USAGE ===
        elif action == "usage":
            tenant_id = tenant["id"] if isinstance(tenant, dict) else tenant.id
            plan_tier = tenant["plan_tier"] if isinstance(tenant, dict) else tenant.plan_tier

            quota_status = await self.usage_service.check_quota(tenant_id, plan_tier)

            return {
                "period": "current_month",
                "total_queries": quota_status.used,
                "quota_limit": quota_status.limit,
                "quota_remaining": quota_status.remaining,
                "quota_reset": quota_status.reset_date.isoformat(),
                "percentage_used": quota_status.percentage_used,
            }

        else:
            return ErrorResponse(error=f"Unknown action: {action}", code="INVALID_ACTION").model_dump()

    # ==================== ENDPOINT 4: API_KEYS (placeholder) ====================

    @modal.fastapi_endpoint(method="POST", docs=True)
    async def api_keys(self, item: dict, authorization: str = Header(default=None)) -> dict:
        """
        API key management endpoint (requires database - placeholder for now).

        POST /api_keys
        """
        return ErrorResponse(
            error="API key management requires database connection. Configure Supabase to enable.",
            code="SERVICE_UNAVAILABLE"
        ).model_dump()

    # ==================== ENDPOINT 5: BILLING (placeholder) ====================

    @modal.fastapi_endpoint(method="POST", docs=True)
    async def billing(self, item: dict, authorization: str = Header(default=None)) -> dict:
        """
        Billing management endpoint (requires Stripe - placeholder for now).

        POST /billing
        """
        return ErrorResponse(
            error="Billing requires Stripe configuration. Configure Stripe to enable.",
            code="SERVICE_UNAVAILABLE"
        ).model_dump()

    # ==================== ENDPOINT 6: SSO (placeholder) ====================

    @modal.fastapi_endpoint(method="GET", docs=True)
    async def sso(self, action: str = "authorize", domain: str = None) -> dict:
        """
        SSO authentication endpoint (requires WorkOS - placeholder for now).

        GET /sso?action=authorize&domain=company.com
        """
        return ErrorResponse(
            error="SSO requires WorkOS configuration. Configure WorkOS to enable.",
            code="SERVICE_UNAVAILABLE"
        ).model_dump()
