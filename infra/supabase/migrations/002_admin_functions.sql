-- Uniclass API Enterprise Schema
-- Migration 002: Admin Functions

-- ==================== ADMIN FUNCTIONS ====================

-- Function to get current month usage for a tenant
CREATE OR REPLACE FUNCTION get_monthly_query_count(p_tenant_id UUID)
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COALESCE(SUM(query_count), 0)
    INTO v_count
    FROM usage_logs
    WHERE tenant_id = p_tenant_id
    AND created_at >= DATE_TRUNC('month', CURRENT_TIMESTAMP);

    RETURN v_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if tenant is within quota
CREATE OR REPLACE FUNCTION check_tenant_quota(p_tenant_id UUID, p_query_count INTEGER DEFAULT 1)
RETURNS BOOLEAN AS $$
DECLARE
    v_plan_tier VARCHAR(50);
    v_quota INTEGER;
    v_used INTEGER;
BEGIN
    -- Get tenant's plan
    SELECT plan_tier INTO v_plan_tier
    FROM tenants
    WHERE id = p_tenant_id;

    IF v_plan_tier IS NULL THEN
        RETURN FALSE;
    END IF;

    -- Get quota for plan
    SELECT queries_per_month INTO v_quota
    FROM plan_config
    WHERE plan_tier = v_plan_tier;

    -- Get current usage
    v_used := get_monthly_query_count(p_tenant_id);

    RETURN (v_used + p_query_count) <= v_quota;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to create a new tenant with owner user
CREATE OR REPLACE FUNCTION create_tenant_with_owner(
    p_tenant_name VARCHAR(255),
    p_tenant_slug VARCHAR(100),
    p_owner_email VARCHAR(255),
    p_owner_password_hash VARCHAR(255) DEFAULT NULL
)
RETURNS TABLE(tenant_id UUID, user_id UUID) AS $$
DECLARE
    v_tenant_id UUID;
    v_user_id UUID;
BEGIN
    -- Create tenant
    INSERT INTO tenants (name, slug, plan_tier, subscription_status)
    VALUES (p_tenant_name, p_tenant_slug, 'free', 'active')
    RETURNING id INTO v_tenant_id;

    -- Create owner user
    INSERT INTO users (tenant_id, email, password_hash, role, status)
    VALUES (v_tenant_id, LOWER(p_owner_email), p_owner_password_hash, 'owner', 'active')
    RETURNING id INTO v_user_id;

    RETURN QUERY SELECT v_tenant_id, v_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get tenant usage statistics
CREATE OR REPLACE FUNCTION get_tenant_usage_stats(
    p_tenant_id UUID,
    p_start_date TIMESTAMPTZ DEFAULT DATE_TRUNC('month', CURRENT_TIMESTAMP),
    p_end_date TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
)
RETURNS TABLE(
    total_requests BIGINT,
    total_queries BIGINT,
    cache_hit_rate FLOAT,
    avg_latency_ms FLOAT,
    by_endpoint JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT AS total_requests,
        COALESCE(SUM(ul.query_count), 0)::BIGINT AS total_queries,
        CASE
            WHEN COUNT(*) > 0 THEN SUM(CASE WHEN ul.cache_hit THEN 1 ELSE 0 END)::FLOAT / COUNT(*)
            ELSE 0
        END AS cache_hit_rate,
        COALESCE(AVG(ul.latency_ms), 0) AS avg_latency_ms,
        COALESCE(
            jsonb_object_agg(ul.endpoint, ul.query_count),
            '{}'::JSONB
        ) AS by_endpoint
    FROM usage_logs ul
    WHERE ul.tenant_id = p_tenant_id
    AND ul.created_at BETWEEN p_start_date AND p_end_date;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to upgrade/downgrade tenant plan
CREATE OR REPLACE FUNCTION change_tenant_plan(
    p_tenant_id UUID,
    p_new_plan VARCHAR(50),
    p_stripe_subscription_id VARCHAR(255) DEFAULT NULL
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE tenants
    SET
        plan_tier = p_new_plan,
        stripe_subscription_id = COALESCE(p_stripe_subscription_id, stripe_subscription_id),
        subscription_status = CASE
            WHEN p_new_plan = 'free' THEN 'active'
            ELSE subscription_status
        END,
        updated_at = NOW()
    WHERE id = p_tenant_id;

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to cleanup old usage logs (for maintenance)
CREATE OR REPLACE FUNCTION cleanup_old_usage_logs(p_days_to_keep INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    v_deleted INTEGER;
BEGIN
    DELETE FROM usage_logs
    WHERE created_at < CURRENT_TIMESTAMP - (p_days_to_keep || ' days')::INTERVAL;

    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN v_deleted;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ==================== ANALYTICS VIEWS ====================

-- Daily usage aggregation (for dashboards)
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_usage_stats AS
SELECT
    tenant_id,
    DATE(created_at) AS date,
    COUNT(*) AS requests,
    SUM(query_count) AS queries,
    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) AS cache_hits,
    AVG(latency_ms)::INTEGER AS avg_latency,
    MAX(latency_ms) AS max_latency,
    SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) AS errors
FROM usage_logs
GROUP BY tenant_id, DATE(created_at);

-- Create index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_usage_stats_tenant_date
ON daily_usage_stats(tenant_id, date);

-- Function to refresh daily stats (call from cron)
CREATE OR REPLACE FUNCTION refresh_daily_usage_stats()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY daily_usage_stats;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Top queries per tenant (for analytics)
CREATE OR REPLACE FUNCTION get_top_queries(
    p_tenant_id UUID,
    p_limit INTEGER DEFAULT 10,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE(
    endpoint VARCHAR(100),
    total_queries BIGINT,
    avg_latency FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ul.endpoint,
        SUM(ul.query_count)::BIGINT AS total_queries,
        AVG(ul.latency_ms) AS avg_latency
    FROM usage_logs ul
    WHERE ul.tenant_id = p_tenant_id
    AND ul.created_at >= CURRENT_TIMESTAMP - (p_days || ' days')::INTERVAL
    GROUP BY ul.endpoint
    ORDER BY total_queries DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ==================== SCHEDULED JOBS ====================
-- Note: These would be set up in Supabase Dashboard or via pg_cron

-- Example: Daily stats refresh (run at 1am)
-- SELECT cron.schedule('refresh-daily-stats', '0 1 * * *', 'SELECT refresh_daily_usage_stats()');

-- Example: Monthly cleanup of old logs (run on 1st of month)
-- SELECT cron.schedule('cleanup-old-logs', '0 2 1 * *', 'SELECT cleanup_old_usage_logs(90)');
