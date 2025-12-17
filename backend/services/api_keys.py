"""
API Key management service.
Handles generation, validation, and management of API keys.
"""
import secrets
import hashlib
from datetime import datetime, timezone
from typing import Optional, Tuple
from dataclasses import dataclass

from .database import DatabaseService, APIKey, Tenant


# API key format: uc_{environment}_{random}
# Example: uc_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
KEY_PREFIX_LIVE = "uc_live_"
KEY_PREFIX_TEST = "uc_test_"
KEY_LENGTH = 32  # Random part length


@dataclass
class APIKeyValidation:
    """Result of API key validation."""
    valid: bool
    api_key: Optional[APIKey] = None
    tenant: Optional[Tenant] = None
    error: Optional[str] = None


class APIKeyService:
    """Service for API key operations."""

    def __init__(self, db: DatabaseService, is_production: bool = True):
        """Initialize API key service."""
        self.db = db
        self.is_production = is_production
        self.prefix = KEY_PREFIX_LIVE if is_production else KEY_PREFIX_TEST

    def generate_key(self) -> Tuple[str, str, str]:
        """
        Generate a new API key.

        Returns:
            Tuple of (full_key, key_hash, key_prefix)

        The full_key should be shown to the user ONCE and never stored.
        Only store the key_hash in the database.
        """
        # Generate random part
        random_part = secrets.token_urlsafe(KEY_LENGTH)

        # Full key with prefix
        full_key = f"{self.prefix}{random_part}"

        # Hash for storage
        key_hash = self._hash_key(full_key)

        # Prefix for identification (first 12 chars including prefix)
        key_prefix = full_key[:12]

        return full_key, key_hash, key_prefix

    def _hash_key(self, key: str) -> str:
        """Hash an API key using SHA-256."""
        return hashlib.sha256(key.encode()).hexdigest()

    async def create_key(
        self,
        tenant_id: str,
        user_id: str,
        name: str,
        scopes: list = None,
        rate_limit_override: int = None,
        expires_at: datetime = None,
    ) -> Tuple[str, APIKey]:
        """
        Create a new API key for a tenant.

        Returns:
            Tuple of (raw_key, api_key_record)

        The raw_key is returned ONLY ONCE and should be shown to the user.
        """
        full_key, key_hash, key_prefix = self.generate_key()

        api_key = await self.db.create_api_key(
            tenant_id=tenant_id,
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=scopes or ["search"],
            rate_limit_override=rate_limit_override,
            expires_at=expires_at,
        )

        return full_key, api_key

    async def validate_key(self, raw_key: str) -> APIKeyValidation:
        """
        Validate an API key and return associated tenant info.

        This is the main authentication method for API requests.
        """
        # Check key format
        if not raw_key:
            return APIKeyValidation(valid=False, error="No API key provided")

        if not (raw_key.startswith(KEY_PREFIX_LIVE) or raw_key.startswith(KEY_PREFIX_TEST)):
            return APIKeyValidation(valid=False, error="Invalid API key format")

        # Check environment match
        if self.is_production and raw_key.startswith(KEY_PREFIX_TEST):
            return APIKeyValidation(valid=False, error="Test key used in production")

        if not self.is_production and raw_key.startswith(KEY_PREFIX_LIVE):
            return APIKeyValidation(valid=False, error="Live key used in test environment")

        # Hash and lookup
        key_hash = self._hash_key(raw_key)
        api_key = await self.db.get_api_key_by_hash(key_hash)

        if not api_key:
            return APIKeyValidation(valid=False, error="Invalid API key")

        if not api_key.is_active:
            return APIKeyValidation(valid=False, error="API key has been revoked")

        # Check expiration
        if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
            return APIKeyValidation(valid=False, error="API key has expired")

        # Get tenant
        tenant = await self.db.get_tenant(api_key.tenant_id)
        if not tenant:
            return APIKeyValidation(valid=False, error="Tenant not found")

        # Check tenant subscription status
        if tenant.subscription_status in ["canceled", "past_due"]:
            return APIKeyValidation(
                valid=False,
                error=f"Subscription {tenant.subscription_status}. Please update payment."
            )

        # Update last used timestamp (fire and forget)
        await self.db.update_api_key_last_used(api_key.id)

        return APIKeyValidation(valid=True, api_key=api_key, tenant=tenant)

    async def list_keys(self, tenant_id: str) -> list:
        """List all API keys for a tenant (without exposing hashes)."""
        keys = await self.db.get_tenant_api_keys(tenant_id)
        return [
            {
                "id": key.id,
                "name": key.name,
                "prefix": key.key_prefix,
                "scopes": key.scopes,
                "is_active": key.is_active,
                "created_at": key.created_at.isoformat(),
                "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                "expires_at": key.expires_at.isoformat() if key.expires_at else None,
            }
            for key in keys
        ]

    async def revoke_key(self, key_id: str, tenant_id: str) -> bool:
        """
        Revoke an API key.

        Returns True if successful, False if key not found or doesn't belong to tenant.
        """
        keys = await self.db.get_tenant_api_keys(tenant_id)
        key = next((k for k in keys if k.id == key_id), None)

        if not key:
            return False

        await self.db.revoke_api_key(key_id)
        return True

    async def rotate_key(
        self,
        key_id: str,
        tenant_id: str,
        user_id: str,
    ) -> Optional[Tuple[str, APIKey]]:
        """
        Rotate an API key (revoke old, create new with same settings).

        Returns new (raw_key, api_key) if successful, None if key not found.
        """
        keys = await self.db.get_tenant_api_keys(tenant_id)
        old_key = next((k for k in keys if k.id == key_id), None)

        if not old_key:
            return None

        # Revoke old key
        await self.db.revoke_api_key(key_id)

        # Create new key with same settings
        return await self.create_key(
            tenant_id=tenant_id,
            user_id=user_id,
            name=f"{old_key.name} (rotated)",
            scopes=old_key.scopes,
            rate_limit_override=old_key.rate_limit_override,
            expires_at=old_key.expires_at,
        )

    def extract_key_from_header(self, authorization: str) -> Optional[str]:
        """Extract API key from Authorization header."""
        if not authorization:
            return None

        # Support both "Bearer <key>" and just "<key>"
        if authorization.startswith("Bearer "):
            return authorization[7:].strip()

        return authorization.strip()
