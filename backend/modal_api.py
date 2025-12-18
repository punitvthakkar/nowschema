"""
Uniclass Search API - Enterprise Edition
Deployed on Modal with full multi-tenancy, authentication, billing, and observability.
Optimized for Modal free tier (6 endpoints).
"""
import modal
import os
import time
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

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
    "einops",  # Required by sentence-transformers models
    # API
    "fastapi[standard]",
    "pydantic>=2.0.0",
    # Database
    "supabase>=2.0.0",
    # Cache & Rate Limiting
    "upstash-redis>=1.0.0",
    "upstash-ratelimit>=1.0.0",
    # Auth
    "python-jose[cryptography]",
    "passlib[bcrypt]",
    "workos>=4.0.0",
    # Billing
    "stripe>=7.0.0",
    # Utils
    "httpx",
)

# Volume for embeddings index
volume = modal.Volume.from_name("uniclass-embeddings-vol", create_if_missing=True)


# ==================== PYDANTIC MODELS ====================

from pydantic import BaseModel, Field


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
    container_idle_timeout=300,
    allow_concurrent_inputs=10,
    secrets=[modal.Secret.from_name("uniclass-enterprise-secrets")],
)
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

        # Initialize enterprise services
        self._init_services()

        print(f"✅ Ready! {self.lookup['num_items']} items indexed.")

    def _init_services(self):
        """Initialize enterprise services (database, cache, rate limiting, etc.)."""
        from config import get_config
        from services.database import init_db, get_db
        from services.api_keys import APIKeyService
        from services.rate_limit import RateLimitService, InMemoryRateLimitService
        from services.cache import CacheService, InMemoryCacheService
        from services.usage import UsageService, InMemoryUsageService
        from services.billing import BillingService
        from services.sso import SSOService
        from services.auth import AuthService

        self.config = get_config()
        self.services_status = {}

        # Database (Supabase)
        if self.config.has_supabase():
            try:
                self.db = init_db(self.config.supabase_url, self.config.supabase_service_key)
                self.services_status["database"] = True
                print("  → Database connected")
            except Exception as e:
                print(f"  ⚠ Database unavailable: {e}")
                self.db = None
                self.services_status["database"] = False
        else:
            self.db = None
            self.services_status["database"] = False
            print("  → Database not configured")

        # Auth service
        jwt_secret = os.environ.get("JWT_SECRET", "")
        self.auth = AuthService(jwt_secret) if jwt_secret else None

        # API Key service
        if self.db:
            self.api_keys = APIKeyService(self.db, self.config.is_production())
        else:
            self.api_keys = None

        # Cache (Upstash Redis)
        if self.config.has_redis():
            try:
                self.cache = CacheService(
                    self.config.upstash_redis_url,
                    self.config.upstash_redis_token
                )
                self.services_status["cache"] = True
                print("  → Cache connected")
            except Exception as e:
                print(f"  ⚠ Cache unavailable: {e}")
                self.cache = InMemoryCacheService()
                self.services_status["cache"] = False
        else:
            self.cache = InMemoryCacheService()
            self.services_status["cache"] = False
            print("  → Using in-memory cache")

        # Rate limiting
        if self.config.has_redis():
            try:
                self.rate_limiter = RateLimitService(
                    self.config.upstash_redis_url,
                    self.config.upstash_redis_token
                )
                self.services_status["rate_limit"] = True
                print("  → Rate limiting enabled")
            except Exception as e:
                print(f"  ⚠ Rate limiting unavailable: {e}")
                self.rate_limiter = InMemoryRateLimitService()
                self.services_status["rate_limit"] = False
        else:
            self.rate_limiter = InMemoryRateLimitService()
            self.services_status["rate_limit"] = False
            print("  → Using in-memory rate limiting")

        # Usage tracking
        if self.db:
            self.usage_service = UsageService(self.db)
            self.services_status["usage"] = True
        else:
            self.usage_service = InMemoryUsageService()
            self.services_status["usage"] = False
            print("  → Using in-memory usage tracking")

        # Billing (Stripe)
        if self.config.has_stripe() and self.db:
            try:
                self.billing = BillingService(
                    db=self.db,
                    stripe_secret_key=self.config.stripe_secret_key,
                    stripe_webhook_secret=self.config.stripe_webhook_secret,
                    price_ids={
                        "starter": self.config.stripe_price_id_starter,
                        "professional": self.config.stripe_price_id_professional,
                        "enterprise": self.config.stripe_price_id_enterprise,
                    }
                )
                self.services_status["billing"] = True
                print("  → Billing enabled")
            except Exception as e:
                print(f"  ⚠ Billing unavailable: {e}")
                self.billing = None
                self.services_status["billing"] = False
        else:
            self.billing = None
            self.services_status["billing"] = False

        # SSO (WorkOS)
        if self.config.has_workos() and self.db:
            try:
                redirect_uri = os.environ.get("SSO_REDIRECT_URI", "")
                self.sso = SSOService(
                    db=self.db,
                    workos_api_key=self.config.workos_api_key,
                    workos_client_id=self.config.workos_client_id,
                    redirect_uri=redirect_uri,
                )
                self.services_status["sso"] = True
                print("  → SSO enabled")
            except Exception as e:
                print(f"  ⚠ SSO unavailable: {e}")
                self.sso = None
                self.services_status["sso"] = False
        else:
            self.sso = None
            self.services_status["sso"] = False

        # Legacy API key (for backwards compatibility during migration)
        self.legacy_api_key = os.environ.get("UNICLASS_API_KEY", "")

    # ==================== AUTHENTICATION ====================

    async def _authenticate(self, authorization: str) -> tuple:
        """Authenticate a request using API key or JWT."""
        if not authorization:
            return None, None, ErrorResponse(error="Authentication required", code="AUTH_REQUIRED")

        token = authorization.replace("Bearer ", "").strip()

        # Check legacy API key first (for migration)
        if self.legacy_api_key and token == self.legacy_api_key:
            return {"id": "legacy", "plan_tier": "professional"}, None, None

        # Validate with enterprise API key service
        if self.api_keys:
            validation = await self.api_keys.validate_key(token)
            if validation.valid:
                return validation.tenant, validation.api_key, None
            else:
                return None, None, ErrorResponse(error=validation.error, code="INVALID_API_KEY")

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

    @modal.web_endpoint(method="GET", docs=True)
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

    @modal.web_endpoint(method="POST", docs=True)
    async def search(self, item: dict, authorization: str = None) -> dict:
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
        rate_result = await self._check_rate_limit(
            tenant_id, plan_tier,
            api_key.rate_limit_override if api_key else None
        )
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
                if api_key:
                    await self.usage_service.record_usage(
                        tenant_id=tenant_id, api_key_id=api_key.id,
                        endpoint="search", query_count=1,
                        cache_hit=True, latency_ms=latency, status_code=200
                    )
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
            if api_key:
                await self.usage_service.record_usage(
                    tenant_id=tenant_id, api_key_id=api_key.id,
                    endpoint="search", query_count=1,
                    cache_hit=False, latency_ms=latency, status_code=200
                )

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

            if api_key:
                await self.usage_service.record_usage(
                    tenant_id=tenant_id, api_key_id=api_key.id,
                    endpoint="search_batch", query_count=len(queries),
                    cache_hit=cache_hits == len(queries),
                    latency_ms=latency, status_code=200
                )

            return {
                "count": len(queries), "top_k": top_k,
                "results": results, "latency_ms": latency
            }

        else:
            return ErrorResponse(error=f"Unknown action: {action}", code="INVALID_ACTION").model_dump()

    # ==================== ENDPOINT 3: INFO (stats + usage) ====================

    @modal.web_endpoint(method="POST", docs=True)
    async def info(self, item: dict, authorization: str = None) -> dict:
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

    # ==================== ENDPOINT 4: API_KEYS (create + list + revoke) ====================

    @modal.web_endpoint(method="POST", docs=True)
    async def api_keys(self, item: dict, authorization: str = None) -> dict:
        """
        API key management endpoint.

        POST /api_keys

        Create key:
            {"action": "create", "name": "Production Key", "scopes": ["search"]}

        List keys:
            {"action": "list"}

        Revoke key:
            {"action": "revoke", "key_id": "uuid-here"}
        """
        tenant, api_key, error = await self._authenticate(authorization)
        if error:
            return error.model_dump()

        if not self.api_keys:
            return ErrorResponse(error="API key management not available", code="SERVICE_UNAVAILABLE").model_dump()

        tenant_id = tenant["id"] if isinstance(tenant, dict) else tenant.id
        action = item.get("action", "list")

        # === CREATE ===
        if action == "create":
            user_id = api_key.user_id if api_key else "system"
            name = item.get("name", "API Key")
            scopes = item.get("scopes", ["search"])

            raw_key, new_key = await self.api_keys.create_key(
                tenant_id=tenant_id, user_id=user_id,
                name=name, scopes=scopes
            )

            return {
                "key": raw_key,
                "id": new_key.id,
                "name": new_key.name,
                "prefix": new_key.key_prefix,
                "scopes": new_key.scopes,
                "created_at": new_key.created_at.isoformat(),
                "warning": "Save this key! It will not be shown again."
            }

        # === LIST ===
        elif action == "list":
            keys = await self.api_keys.list_keys(tenant_id)
            return {"keys": keys}

        # === REVOKE ===
        elif action == "revoke":
            key_id = item.get("key_id")
            if not key_id:
                return ErrorResponse(error="Missing 'key_id'", code="MISSING_PARAM").model_dump()

            success = await self.api_keys.revoke_key(key_id, tenant_id)

            if success:
                return {"status": "revoked", "key_id": key_id}
            else:
                return ErrorResponse(error="Key not found", code="NOT_FOUND").model_dump()

        else:
            return ErrorResponse(error=f"Unknown action: {action}", code="INVALID_ACTION").model_dump()

    # ==================== ENDPOINT 5: BILLING (checkout + webhook) ====================

    @modal.web_endpoint(method="POST", docs=True)
    async def billing(self, item: dict, authorization: str = None) -> dict:
        """
        Billing management endpoint.

        POST /billing

        Create checkout session:
            {"action": "checkout", "plan": "starter", "success_url": "...", "cancel_url": "..."}

        Handle webhook (no auth):
            {"action": "webhook", "event": {...}}
        """
        action = item.get("action", "")

        # === WEBHOOK (no auth required - Stripe sends directly) ===
        if action == "webhook":
            if not self.billing:
                return {"received": True, "processed": False}

            try:
                event_data = item.get("event", item)
                await self.billing.handle_webhook(event_data)
                return {"received": True, "processed": True}
            except Exception as e:
                return {"received": True, "processed": False, "error": str(e)}

        # === CHECKOUT (auth required) ===
        tenant, api_key, error = await self._authenticate(authorization)
        if error:
            return error.model_dump()

        if action == "checkout":
            if not self.billing:
                return ErrorResponse(error="Billing not available", code="SERVICE_UNAVAILABLE").model_dump()

            plan = item.get("plan", "starter")
            success_url = item.get("success_url", "https://yourapp.com/success")
            cancel_url = item.get("cancel_url", "https://yourapp.com/cancel")

            tenant_obj = tenant if not isinstance(tenant, dict) else None
            if not tenant_obj:
                return ErrorResponse(error="Tenant not found", code="NOT_FOUND").model_dump()

            customer_id = await self.billing.get_or_create_customer(
                tenant_obj, email=f"billing@{tenant_obj.slug}.com"
            )

            checkout_url = await self.billing.create_checkout_session(
                tenant_id=tenant_obj.id, customer_id=customer_id,
                plan_tier=plan, success_url=success_url, cancel_url=cancel_url
            )

            return {"checkout_url": checkout_url}

        else:
            return ErrorResponse(error=f"Unknown action: {action}", code="INVALID_ACTION").model_dump()

    # ==================== ENDPOINT 6: SSO (authorize + callback) ====================

    @modal.web_endpoint(method="GET", docs=True)
    async def sso(self, action: str = "authorize", domain: str = None, email: str = None, code: str = None) -> dict:
        """
        SSO authentication endpoint.

        GET /sso?action=authorize&domain=company.com
        GET /sso?action=authorize&email=user@company.com
        GET /sso?action=callback&code=auth-code-here
        """
        if not self.sso:
            return ErrorResponse(error="SSO not available", code="SERVICE_UNAVAILABLE").model_dump()

        # === AUTHORIZE ===
        if action == "authorize":
            if email and not domain:
                domain = email.split("@")[1] if "@" in email else None

            if not domain:
                return ErrorResponse(error="Missing domain or email", code="MISSING_PARAM").model_dump()

            tenant = await self.sso.detect_sso_domain(f"user@{domain}")
            if not tenant:
                return ErrorResponse(error="SSO not configured for this domain", code="SSO_NOT_CONFIGURED").model_dump()

            auth_url = self.sso.get_authorization_url(domain=domain)
            return {"authorization_url": auth_url}

        # === CALLBACK ===
        elif action == "callback":
            if not code:
                return ErrorResponse(error="Missing authorization code", code="MISSING_PARAM").model_dump()

            try:
                profile, user, tenant = await self.sso.handle_callback(code)

                if not user and tenant:
                    user = await self.sso.provision_user(profile, tenant.id)

                if user and self.auth:
                    tokens = self.auth.create_token_pair(
                        user_id=user.id, tenant_id=user.tenant_id,
                        email=user.email, role=user.role
                    )
                    return {
                        "access_token": tokens.access_token,
                        "refresh_token": tokens.refresh_token,
                        "token_type": tokens.token_type,
                        "expires_in": tokens.expires_in,
                        "user": {"id": user.id, "email": user.email, "role": user.role}
                    }

                return ErrorResponse(error="Unable to authenticate", code="AUTH_FAILED").model_dump()

            except Exception as e:
                return ErrorResponse(error=f"SSO callback failed: {str(e)}", code="SSO_ERROR").model_dump()

        else:
            return ErrorResponse(error=f"Unknown action: {action}", code="INVALID_ACTION").model_dump()
