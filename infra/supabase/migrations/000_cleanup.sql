-- Uniclass API - Complete Database Reset
-- Run this in Supabase SQL Editor to clean everything before re-running migrations
-- WARNING: This will DELETE ALL DATA

-- Drop materialized views first
DROP MATERIALIZED VIEW IF EXISTS daily_usage_stats CASCADE;

-- Drop regular views
DROP VIEW IF EXISTS monthly_usage_summary CASCADE;
DROP VIEW IF EXISTS active_subscriptions CASCADE;

-- Drop functions
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
DROP FUNCTION IF EXISTS get_monthly_query_count(UUID) CASCADE;
DROP FUNCTION IF EXISTS check_tenant_quota(UUID, INTEGER) CASCADE;
DROP FUNCTION IF EXISTS create_tenant_with_owner(VARCHAR, VARCHAR, VARCHAR, VARCHAR) CASCADE;
DROP FUNCTION IF EXISTS get_tenant_usage_stats(UUID, TIMESTAMPTZ, TIMESTAMPTZ) CASCADE;
DROP FUNCTION IF EXISTS change_tenant_plan(UUID, VARCHAR, VARCHAR) CASCADE;
DROP FUNCTION IF EXISTS cleanup_old_usage_logs(INTEGER) CASCADE;
DROP FUNCTION IF EXISTS refresh_daily_usage_stats() CASCADE;
DROP FUNCTION IF EXISTS get_top_queries(UUID, INTEGER, INTEGER) CASCADE;

-- Drop tables (in reverse dependency order)
DROP TABLE IF EXISTS billing_events CASCADE;
DROP TABLE IF EXISTS usage_logs CASCADE;
DROP TABLE IF EXISTS api_keys CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS plan_config CASCADE;
DROP TABLE IF EXISTS tenants CASCADE;

-- Optionally remove the UUID extension (only if not used elsewhere)
-- DROP EXTENSION IF EXISTS "uuid-ossp";

-- Verify cleanup
SELECT
    tablename
FROM
    pg_tables
WHERE
    schemaname = 'public'
    AND tablename IN ('tenants', 'users', 'api_keys', 'usage_logs', 'billing_events', 'plan_config');
