"""
Database service using Supabase.
Handles all database operations with connection pooling.
"""
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import hashlib

# Will be available in Modal environment
try:
    from supabase import create_client, Client
except ImportError:
    Client = None


@dataclass
class Tenant:
    """Tenant/Organization model."""
    id: str
    name: str
    slug: str
    stripe_customer_id: Optional[str]
    stripe_subscription_id: Optional[str]
    plan_tier: str  # free, starter, professional, enterprise
    subscription_status: str  # active, past_due, canceled, trialing
    sso_enabled: bool
    sso_provider: Optional[str]
    sso_domain: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class User:
    """User model."""
    id: str
    tenant_id: str
    email: str
    password_hash: Optional[str]
    auth_provider: str  # email, google, microsoft, sso
    workos_user_id: Optional[str]
    role: str  # owner, admin, member
    status: str  # active, invited, suspended
    created_at: datetime
    updated_at: datetime


@dataclass
class APIKey:
    """API Key model."""
    id: str
    tenant_id: str
    user_id: str
    name: str
    key_hash: str
    key_prefix: str  # First 8 chars for identification
    scopes: List[str]
    rate_limit_override: Optional[int]
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    is_active: bool
    created_at: datetime


class DatabaseService:
    """Service for database operations using Supabase."""

    def __init__(self, supabase_url: str, supabase_key: str):
        """Initialize database connection."""
        if Client is None:
            raise RuntimeError("Supabase client not available")
        self.client: Client = create_client(supabase_url, supabase_key)

    # ==================== TENANT OPERATIONS ====================

    async def create_tenant(
        self,
        name: str,
        slug: str,
        plan_tier: str = "free"
    ) -> Tenant:
        """Create a new tenant/organization."""
        data = {
            "name": name,
            "slug": slug,
            "plan_tier": plan_tier,
            "subscription_status": "active" if plan_tier == "free" else "trialing",
            "sso_enabled": False,
        }
        result = self.client.table("tenants").insert(data).execute()
        return self._row_to_tenant(result.data[0])

    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID."""
        result = self.client.table("tenants").select("*").eq("id", tenant_id).execute()
        if result.data:
            return self._row_to_tenant(result.data[0])
        return None

    async def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """Get tenant by slug."""
        result = self.client.table("tenants").select("*").eq("slug", slug).execute()
        if result.data:
            return self._row_to_tenant(result.data[0])
        return None

    async def get_tenant_by_domain(self, domain: str) -> Optional[Tenant]:
        """Get tenant by SSO domain."""
        result = self.client.table("tenants").select("*").eq("sso_domain", domain).execute()
        if result.data:
            return self._row_to_tenant(result.data[0])
        return None

    async def update_tenant(self, tenant_id: str, updates: Dict[str, Any]) -> Tenant:
        """Update tenant details."""
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = self.client.table("tenants").update(updates).eq("id", tenant_id).execute()
        return self._row_to_tenant(result.data[0])

    async def update_tenant_subscription(
        self,
        tenant_id: str,
        stripe_customer_id: str,
        stripe_subscription_id: str,
        plan_tier: str,
        status: str
    ) -> Tenant:
        """Update tenant subscription details."""
        return await self.update_tenant(tenant_id, {
            "stripe_customer_id": stripe_customer_id,
            "stripe_subscription_id": stripe_subscription_id,
            "plan_tier": plan_tier,
            "subscription_status": status,
        })

    # ==================== USER OPERATIONS ====================

    async def create_user(
        self,
        tenant_id: str,
        email: str,
        password_hash: Optional[str] = None,
        auth_provider: str = "email",
        role: str = "member",
        workos_user_id: Optional[str] = None,
    ) -> User:
        """Create a new user."""
        data = {
            "tenant_id": tenant_id,
            "email": email.lower(),
            "password_hash": password_hash,
            "auth_provider": auth_provider,
            "role": role,
            "status": "active",
            "workos_user_id": workos_user_id,
        }
        result = self.client.table("users").insert(data).execute()
        return self._row_to_user(result.data[0])

    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        result = self.client.table("users").select("*").eq("id", user_id).execute()
        if result.data:
            return self._row_to_user(result.data[0])
        return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = self.client.table("users").select("*").eq("email", email.lower()).execute()
        if result.data:
            return self._row_to_user(result.data[0])
        return None

    async def get_user_by_workos_id(self, workos_user_id: str) -> Optional[User]:
        """Get user by WorkOS user ID."""
        result = self.client.table("users").select("*").eq("workos_user_id", workos_user_id).execute()
        if result.data:
            return self._row_to_user(result.data[0])
        return None

    async def get_tenant_users(self, tenant_id: str) -> List[User]:
        """Get all users for a tenant."""
        result = self.client.table("users").select("*").eq("tenant_id", tenant_id).execute()
        return [self._row_to_user(row) for row in result.data]

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> User:
        """Update user details."""
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = self.client.table("users").update(updates).eq("id", user_id).execute()
        return self._row_to_user(result.data[0])

    # ==================== API KEY OPERATIONS ====================

    async def create_api_key(
        self,
        tenant_id: str,
        user_id: str,
        name: str,
        key_hash: str,
        key_prefix: str,
        scopes: List[str] = None,
        rate_limit_override: Optional[int] = None,
        expires_at: Optional[datetime] = None,
    ) -> APIKey:
        """Create a new API key."""
        data = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "name": name,
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            "scopes": scopes or ["search"],
            "rate_limit_override": rate_limit_override,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "is_active": True,
        }
        result = self.client.table("api_keys").insert(data).execute()
        return self._row_to_api_key(result.data[0])

    async def get_api_key_by_hash(self, key_hash: str) -> Optional[APIKey]:
        """Get API key by its hash."""
        result = self.client.table("api_keys").select("*").eq("key_hash", key_hash).eq("is_active", True).execute()
        if result.data:
            return self._row_to_api_key(result.data[0])
        return None

    async def get_tenant_api_keys(self, tenant_id: str) -> List[APIKey]:
        """Get all API keys for a tenant."""
        result = self.client.table("api_keys").select("*").eq("tenant_id", tenant_id).execute()
        return [self._row_to_api_key(row) for row in result.data]

    async def update_api_key_last_used(self, key_id: str) -> None:
        """Update the last_used_at timestamp for an API key."""
        self.client.table("api_keys").update({
            "last_used_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", key_id).execute()

    async def revoke_api_key(self, key_id: str) -> None:
        """Revoke (deactivate) an API key."""
        self.client.table("api_keys").update({"is_active": False}).eq("id", key_id).execute()

    # ==================== USAGE LOGGING ====================

    async def log_usage(
        self,
        tenant_id: str,
        api_key_id: str,
        endpoint: str,
        query_count: int,
        cache_hit: bool,
        latency_ms: int,
        status_code: int,
    ) -> None:
        """Log an API usage event."""
        data = {
            "tenant_id": tenant_id,
            "api_key_id": api_key_id,
            "endpoint": endpoint,
            "query_count": query_count,
            "cache_hit": cache_hit,
            "latency_ms": latency_ms,
            "status_code": status_code,
        }
        self.client.table("usage_logs").insert(data).execute()

    async def get_tenant_usage(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get usage statistics for a tenant within a date range."""
        result = self.client.table("usage_logs").select(
            "endpoint, query_count, cache_hit, latency_ms, status_code, created_at"
        ).eq("tenant_id", tenant_id).gte(
            "created_at", start_date.isoformat()
        ).lte(
            "created_at", end_date.isoformat()
        ).execute()

        total_queries = sum(row["query_count"] for row in result.data)
        cache_hits = sum(1 for row in result.data if row["cache_hit"])
        avg_latency = sum(row["latency_ms"] for row in result.data) / len(result.data) if result.data else 0

        return {
            "total_requests": len(result.data),
            "total_queries": total_queries,
            "cache_hit_rate": cache_hits / len(result.data) if result.data else 0,
            "avg_latency_ms": avg_latency,
            "by_endpoint": self._group_by_endpoint(result.data),
        }

    async def get_monthly_query_count(self, tenant_id: str) -> int:
        """Get the total query count for the current month."""
        now = datetime.now(timezone.utc)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        result = self.client.table("usage_logs").select(
            "query_count"
        ).eq("tenant_id", tenant_id).gte(
            "created_at", start_of_month.isoformat()
        ).execute()

        return sum(row["query_count"] for row in result.data)

    # ==================== BILLING EVENTS ====================

    async def log_billing_event(
        self,
        event_id: str,
        event_type: str,
        payload: Dict[str, Any]
    ) -> None:
        """Log a billing webhook event."""
        data = {
            "event_id": event_id,
            "event_type": event_type,
            "payload": json.dumps(payload),
            "processed": False,
        }
        self.client.table("billing_events").insert(data).execute()

    async def mark_billing_event_processed(self, event_id: str) -> None:
        """Mark a billing event as processed."""
        self.client.table("billing_events").update({
            "processed": True
        }).eq("event_id", event_id).execute()

    # ==================== HELPER METHODS ====================

    def _row_to_tenant(self, row: Dict[str, Any]) -> Tenant:
        """Convert database row to Tenant object."""
        return Tenant(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            stripe_customer_id=row.get("stripe_customer_id"),
            stripe_subscription_id=row.get("stripe_subscription_id"),
            plan_tier=row["plan_tier"],
            subscription_status=row["subscription_status"],
            sso_enabled=row.get("sso_enabled", False),
            sso_provider=row.get("sso_provider"),
            sso_domain=row.get("sso_domain"),
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00")),
        )

    def _row_to_user(self, row: Dict[str, Any]) -> User:
        """Convert database row to User object."""
        return User(
            id=row["id"],
            tenant_id=row["tenant_id"],
            email=row["email"],
            password_hash=row.get("password_hash"),
            auth_provider=row["auth_provider"],
            workos_user_id=row.get("workos_user_id"),
            role=row["role"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00")),
        )

    def _row_to_api_key(self, row: Dict[str, Any]) -> APIKey:
        """Convert database row to APIKey object."""
        return APIKey(
            id=row["id"],
            tenant_id=row["tenant_id"],
            user_id=row["user_id"],
            name=row["name"],
            key_hash=row["key_hash"],
            key_prefix=row["key_prefix"],
            scopes=row.get("scopes", []),
            rate_limit_override=row.get("rate_limit_override"),
            expires_at=datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00")) if row.get("expires_at") else None,
            last_used_at=datetime.fromisoformat(row["last_used_at"].replace("Z", "+00:00")) if row.get("last_used_at") else None,
            is_active=row["is_active"],
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
        )

    def _group_by_endpoint(self, rows: List[Dict[str, Any]]) -> Dict[str, int]:
        """Group usage data by endpoint."""
        by_endpoint = {}
        for row in rows:
            endpoint = row["endpoint"]
            by_endpoint[endpoint] = by_endpoint.get(endpoint, 0) + row["query_count"]
        return by_endpoint


# Global database instance
_db: Optional[DatabaseService] = None


def get_db() -> Optional[DatabaseService]:
    """Get the global database instance."""
    return _db


def init_db(supabase_url: str, supabase_key: str) -> DatabaseService:
    """Initialize the global database instance."""
    global _db
    _db = DatabaseService(supabase_url, supabase_key)
    return _db
