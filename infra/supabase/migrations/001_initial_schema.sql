-- Uniclass API Enterprise Schema
-- Migration 001: Initial Schema

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==================== TENANTS ====================
-- Organizations using the Uniclass API

CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,

    -- Stripe integration
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),

    -- Subscription
    plan_tier VARCHAR(50) NOT NULL DEFAULT 'free',
    subscription_status VARCHAR(50) NOT NULL DEFAULT 'active',

    -- SSO configuration
    sso_enabled BOOLEAN DEFAULT FALSE,
    sso_provider VARCHAR(50),
    sso_domain VARCHAR(255),

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_plan_tier CHECK (plan_tier IN ('free', 'starter', 'professional', 'enterprise')),
    CONSTRAINT valid_subscription_status CHECK (subscription_status IN ('active', 'past_due', 'canceled', 'trialing', 'incomplete'))
);

-- Index for domain-based SSO lookup
CREATE INDEX idx_tenants_sso_domain ON tenants(sso_domain) WHERE sso_domain IS NOT NULL;
CREATE INDEX idx_tenants_stripe_customer ON tenants(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;

-- ==================== USERS ====================
-- Individual users within tenants

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Identity
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255),

    -- Auth provider
    auth_provider VARCHAR(50) NOT NULL DEFAULT 'email',
    workos_user_id VARCHAR(255),

    -- Role & Status
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    status VARCHAR(50) NOT NULL DEFAULT 'active',

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_auth_provider CHECK (auth_provider IN ('email', 'google', 'microsoft', 'github', 'sso')),
    CONSTRAINT valid_role CHECK (role IN ('owner', 'admin', 'member')),
    CONSTRAINT valid_status CHECK (status IN ('active', 'invited', 'suspended')),
    CONSTRAINT unique_email_per_tenant UNIQUE (tenant_id, email)
);

-- Indexes
CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_workos ON users(workos_user_id) WHERE workos_user_id IS NOT NULL;

-- ==================== API KEYS ====================
-- API keys for authentication

CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Key details
    name VARCHAR(100) NOT NULL,
    key_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 hash
    key_prefix VARCHAR(12) NOT NULL,       -- First 12 chars for identification

    -- Permissions
    scopes TEXT[] NOT NULL DEFAULT ARRAY['search'],
    rate_limit_override INTEGER,           -- Per-key rate limit override

    -- Lifecycle
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_api_keys_tenant ON api_keys(tenant_id);
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash) WHERE is_active = TRUE;
CREATE INDEX idx_api_keys_user ON api_keys(user_id);

-- ==================== USAGE LOGS ====================
-- API usage tracking

CREATE TABLE usage_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    api_key_id UUID REFERENCES api_keys(id) ON DELETE SET NULL,

    -- Request details
    endpoint VARCHAR(100) NOT NULL,
    query_count INTEGER NOT NULL DEFAULT 1,

    -- Performance
    cache_hit BOOLEAN NOT NULL DEFAULT FALSE,
    latency_ms INTEGER NOT NULL,
    status_code INTEGER NOT NULL,

    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX idx_usage_logs_tenant_time ON usage_logs(tenant_id, created_at DESC);
CREATE INDEX idx_usage_logs_api_key ON usage_logs(api_key_id) WHERE api_key_id IS NOT NULL;

-- Partition by month for large-scale usage (optional optimization)
-- This would be enabled in production for better performance

-- ==================== BILLING EVENTS ====================
-- Stripe webhook event log

CREATE TABLE billing_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id VARCHAR(255) UNIQUE NOT NULL,  -- Stripe event ID
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    processed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for finding unprocessed events
CREATE INDEX idx_billing_events_unprocessed ON billing_events(processed) WHERE processed = FALSE;
CREATE INDEX idx_billing_events_type ON billing_events(event_type);

-- ==================== PLAN CONFIGURATION ====================
-- Maps Stripe price IDs to plan features

CREATE TABLE plan_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plan_tier VARCHAR(50) UNIQUE NOT NULL,
    stripe_price_id VARCHAR(255),

    -- Limits
    queries_per_month INTEGER NOT NULL,
    rate_limit_per_minute INTEGER NOT NULL,

    -- Features (as JSON for flexibility)
    features JSONB NOT NULL DEFAULT '[]',

    -- Pricing
    price_monthly_cents INTEGER NOT NULL DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Insert default plans
INSERT INTO plan_config (plan_tier, queries_per_month, rate_limit_per_minute, features, price_monthly_cents) VALUES
    ('free', 1000, 10, '["single_search", "basic_support"]', 0),
    ('starter', 10000, 60, '["single_search", "batch_search", "email_support"]', 2900),
    ('professional', 100000, 300, '["single_search", "batch_search", "priority_support", "analytics"]', 9900),
    ('enterprise', 1000000, 1000, '["single_search", "batch_search", "sso", "dedicated_support", "analytics", "sla"]', 49900);

-- ==================== FUNCTIONS ====================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to tenants
CREATE TRIGGER update_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply to users
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply to plan_config
CREATE TRIGGER update_plan_config_updated_at
    BEFORE UPDATE ON plan_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ==================== ROW LEVEL SECURITY ====================
-- Enable RLS for multi-tenant isolation

ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;

-- Service role can access everything (for API)
CREATE POLICY "Service role full access on tenants"
    ON tenants FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on users"
    ON users FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on api_keys"
    ON api_keys FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on usage_logs"
    ON usage_logs FOR ALL
    USING (auth.role() = 'service_role');

-- ==================== VIEWS ====================

-- Monthly usage summary view
CREATE VIEW monthly_usage_summary AS
SELECT
    tenant_id,
    DATE_TRUNC('month', created_at) AS month,
    SUM(query_count) AS total_queries,
    COUNT(*) AS total_requests,
    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)::FLOAT / COUNT(*) AS cache_hit_rate,
    AVG(latency_ms) AS avg_latency_ms
FROM usage_logs
GROUP BY tenant_id, DATE_TRUNC('month', created_at);

-- Active subscriptions view
CREATE VIEW active_subscriptions AS
SELECT
    t.id AS tenant_id,
    t.name AS tenant_name,
    t.plan_tier,
    t.subscription_status,
    pc.queries_per_month AS quota,
    pc.rate_limit_per_minute AS rate_limit,
    pc.price_monthly_cents / 100.0 AS price_monthly
FROM tenants t
JOIN plan_config pc ON t.plan_tier = pc.plan_tier
WHERE t.subscription_status IN ('active', 'trialing');
