"""
Configuration management for Uniclass API.
Loads settings from Modal secrets or environment variables.
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Application configuration loaded from environment."""

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""

    # Upstash Redis
    upstash_redis_url: str = ""
    upstash_redis_token: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id_starter: str = ""
    stripe_price_id_professional: str = ""
    stripe_price_id_enterprise: str = ""

    # WorkOS
    workos_api_key: str = ""
    workos_client_id: str = ""

    # Grafana
    grafana_api_key: str = ""
    grafana_endpoint: str = ""

    # App settings
    environment: str = "development"
    api_version: str = "v1"

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            # Supabase
            supabase_url=os.environ.get("SUPABASE_URL", ""),
            supabase_anon_key=os.environ.get("SUPABASE_ANON_KEY", ""),
            supabase_service_key=os.environ.get("SUPABASE_SERVICE_KEY", ""),

            # Upstash Redis
            upstash_redis_url=os.environ.get("UPSTASH_REDIS_URL", ""),
            upstash_redis_token=os.environ.get("UPSTASH_REDIS_TOKEN", ""),

            # Stripe
            stripe_secret_key=os.environ.get("STRIPE_SECRET_KEY", ""),
            stripe_webhook_secret=os.environ.get("STRIPE_WEBHOOK_SECRET", ""),
            stripe_price_id_starter=os.environ.get("STRIPE_PRICE_ID_STARTER", ""),
            stripe_price_id_professional=os.environ.get("STRIPE_PRICE_ID_PROFESSIONAL", ""),
            stripe_price_id_enterprise=os.environ.get("STRIPE_PRICE_ID_ENTERPRISE", ""),

            # WorkOS
            workos_api_key=os.environ.get("WORKOS_API_KEY", ""),
            workos_client_id=os.environ.get("WORKOS_CLIENT_ID", ""),

            # Grafana
            grafana_api_key=os.environ.get("GRAFANA_API_KEY", ""),
            grafana_endpoint=os.environ.get("GRAFANA_ENDPOINT", ""),

            # App settings
            environment=os.environ.get("ENVIRONMENT", "development"),
            api_version=os.environ.get("API_VERSION", "v1"),
        )

    def is_production(self) -> bool:
        return self.environment == "production"

    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)

    def has_redis(self) -> bool:
        return bool(self.upstash_redis_url and self.upstash_redis_token)

    def has_stripe(self) -> bool:
        return bool(self.stripe_secret_key)

    def has_workos(self) -> bool:
        return bool(self.workos_api_key and self.workos_client_id)


# Global config instance (loaded on import)
config: Optional[Config] = None


def get_config() -> Config:
    """Get or create the global config instance."""
    global config
    if config is None:
        config = Config.from_env()
    return config
