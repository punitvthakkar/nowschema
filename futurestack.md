# FUTURESTACK: Enterprise Backend Transformation Skill

## Purpose

This skill enables an AI agent to transform a basic serverless vector embedding API (running on Modal) into a fully enterprise-ready backend with authentication, billing, multi-tenancy, observability, and operational automation. The transformation preserves the existing core functionality while adding the infrastructure required to serve paying customers at scale.

## When to Use This Skill

Use this skill when:
- A developer has a working proof-of-concept API on Modal (or similar serverless platform)
- The API needs to be transformed into a multi-tenant SaaS product
- Enterprise features like SSO, billing, and usage tracking are required
- The solution must remain low-cost using free tiers where possible
- Maximum automation is desired to minimize manual operations

## Guiding Principles

1. **Preserve What Works**: The existing vector search logic is the core value. Wrap it with enterprise infrastructure without modifying the core algorithm.

2. **Free Tier First**: Use services with generous free tiers. Only recommend paid services when free alternatives are inadequate.

3. **Automate Everything**: Every manual task is a failure. Design systems that self-provision, self-heal, and self-report.

4. **Tenant Isolation by Default**: Every piece of data, every API call, every log entry must be attributable to a specific tenant.

5. **Fail Gracefully**: Enterprise features (logging, metrics, billing) should never break the core API. If observability fails, the search must still work.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ENTRY POINTS                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐│
│  │ Web App     │  │ Revit Plugin│  │ Excel Add-in│  │ Direct API Calls    ││
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AUTHENTICATION LAYER                              │
│  ┌─────────────────────────────┐  ┌─────────────────────────────────────┐  │
│  │ Standard Auth               │  │ Enterprise SSO                      │  │
│  │ • Email/Password            │  │ • SAML 2.0                          │  │
│  │ • OAuth (Google, Microsoft) │  │ • Azure AD / Okta / Google Workspace│  │
│  │ • Magic Links               │  │ • SCIM Provisioning                 │  │
│  └─────────────────────────────┘  └─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            API GATEWAY LAYER                                │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌─────────────┐  │
│  │ API Key       │  │ Rate          │  │ Request       │  │ Tenant      │  │
│  │ Validation    │  │ Limiting      │  │ Validation    │  │ Resolution  │  │
│  └───────────────┘  └───────────────┘  └───────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             CACHING LAYER                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Query Result Cache                                                   │   │
│  │ • Hash of (query + parameters) → cached results                      │   │
│  │ • TTL-based expiration (24 hours recommended for stable embeddings)  │   │
│  │ • Cache hit = skip embedding computation = cost savings              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          APPLICATION LAYER                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Core Vector Search Service (Your Existing Modal Functions)           │   │
│  │ • Load embeddings                                                    │   │
│  │ • Encode query with model                                            │   │
│  │ • Similarity search                                                  │   │
│  │ • Return ranked results                                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             DATA LAYER                                      │
│  ┌───────────────────────┐  ┌───────────────────────┐  ┌─────────────────┐ │
│  │ Tenant Database       │  │ Vector Storage        │  │ Cache Store     │ │
│  │ • Tenants             │  │ • Pre-computed        │  │ • Query results │ │
│  │ • Users               │  │   embeddings          │  │ • Rate counters │ │
│  │ • API Keys            │  │ • Model artifacts     │  │ • Auth tokens   │ │
│  │ • Usage Logs          │  │                       │  │                 │ │
│  │ • Subscriptions       │  │                       │  │                 │ │
│  └───────────────────────┘  └───────────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OBSERVABILITY LAYER                                 │
│  ┌───────────────────┐  ┌───────────────────┐  ┌─────────────────────────┐ │
│  │ Metrics           │  │ Logging           │  │ Alerting                │ │
│  │ • Request count   │  │ • Structured logs │  │ • Error rate threshold  │ │
│  │ • Latency (p50,   │  │ • Per-tenant      │  │ • Latency threshold     │ │
│  │   p95, p99)       │  │   attribution     │  │ • Quota exhaustion      │ │
│  │ • Cache hit rate  │  │ • Error tracking  │  │ • Payment failures      │ │
│  │ • Error rate      │  │                   │  │                         │ │
│  └───────────────────┘  └───────────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BILLING LAYER                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Subscription Management                                              │   │
│  │ • Plan tiers (Free, Pro, Enterprise)                                 │   │
│  │ • Usage-based billing (optional)                                     │   │
│  │ • Self-service upgrade/downgrade                                     │   │
│  │ • Invoice generation                                                 │   │
│  │ • Payment failure handling                                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Specifications

### 1. Multi-Tenancy System

#### What It Does
Isolates customers from each other so that one customer's data, usage, and configuration never leaks to another. Every API request is associated with exactly one tenant.

#### Data Model

**Tenants Table**
- Unique identifier (UUID)
- Organization name
- URL-safe slug for subdomains/URLs
- Billing identifiers (links to payment provider)
- Subscription status and plan tier
- Plan limits (quota, rate limits, feature flags)
- SSO configuration (if enterprise)
- Active/inactive status
- Timestamps (created, updated)

**Users Table**
- Unique identifier
- Foreign key to tenant
- Authentication provider identifiers (standard auth ID, SSO provider ID)
- Email and profile information
- Role within tenant (owner, admin, member)
- Status and login tracking

**API Keys Table**
- Unique identifier
- Foreign key to tenant
- Foreign key to creating user
- Key hash (never store plaintext keys)
- Key prefix (for identification without exposing full key)
- Display version (masked, e.g., "uc_live_****xxxx")
- Scopes (which endpoints this key can access)
- Rate limit override (optional per-key limit)
- Active status and expiration
- Last used timestamp

#### Jobs to Be Done

1. **Tenant Provisioning**
   - When a new user signs up, automatically create a tenant record
   - Generate a URL-safe slug from the organization name
   - Set default plan limits based on the free tier
   - Create the user record linked to the new tenant with "owner" role
   - Generate the first API key automatically
   - Store the raw API key in a one-time-viewable location (user metadata or secure session)

2. **Tenant Resolution**
   - On every API request, extract the API key from the Authorization header
   - Hash the API key and look up the corresponding tenant
   - Cache the lookup result to avoid database queries on every request
   - Inject tenant context into the request for downstream use

3. **User Management Within Tenants**
   - Allow tenant owners/admins to invite additional users
   - Support multiple authentication methods for users in the same tenant
   - Enforce that users can only access their own tenant's data

4. **API Key Lifecycle**
   - Generate cryptographically secure keys with identifiable prefixes
   - Hash keys before storage using SHA-256
   - Support key rotation (create new, deprecate old)
   - Allow key revocation (immediate deactivation)
   - Track key usage for security auditing

#### Automation Requirements

- Tenant creation must be fully automatic on signup (database trigger or application logic)
- API key generation must require zero human intervention
- Key validation must be cached to minimize database load
- Tenant deactivation must immediately block all API access

---

### 2. Authentication System

#### What It Does
Verifies the identity of users accessing the web dashboard and validates API keys for programmatic access. Supports both standard authentication (email/password, OAuth) and enterprise SSO (SAML, OIDC).

#### Authentication Flows

**Standard Authentication (for web dashboard)**
- Email and password with secure hashing
- OAuth providers (Google, Microsoft, GitHub)
- Magic link (passwordless email)
- Email verification for new accounts
- Password reset flow

**API Key Authentication (for API access)**
- Bearer token in Authorization header
- Format: `Authorization: Bearer uc_live_xxxxx`
- Keys are hashed and validated against the database
- No session management needed (stateless)

**Enterprise SSO (for enterprise customers)**
- SAML 2.0 for traditional enterprise identity providers
- OIDC for modern providers
- Just-in-time user provisioning (create user on first SSO login)
- Domain-based SSO detection (if email domain matches, redirect to SSO)

#### Jobs to Be Done

1. **Standard Auth Setup**
   - Configure authentication provider with email/password and OAuth options
   - Set up email templates for verification, password reset, and magic links
   - Create signup flow that triggers tenant provisioning
   - Implement secure session management for web dashboard

2. **API Key Validation**
   - Accept API key from Authorization header
   - Validate format (must start with expected prefix)
   - Hash and lookup in database
   - Check key is active, not expired, and tenant is active
   - Check tenant subscription allows API access
   - Return tenant context or reject with appropriate error

3. **SSO Integration**
   - Integrate with SSO provider service (handles SAML/OIDC complexity)
   - Create endpoint to check if email domain has SSO configured
   - Create authorization URL generator for SSO redirect
   - Create callback handler for SSO response
   - Implement just-in-time provisioning for new SSO users
   - Map SSO user to existing tenant based on domain

4. **SSO Configuration for Enterprise Tenants**
   - Create SSO organization in provider when enterprise tenant activates SSO
   - Generate setup URL for customer's IT admin
   - Store SSO configuration (organization ID, domain, provider type)
   - Enable domain-based SSO detection once configured

#### Automation Requirements

- Standard signup must automatically create tenant and API key
- SSO login must automatically create user if not exists
- SSO domain detection must be automatic (no manual routing)
- Session tokens must be self-expiring (no manual cleanup)

---

### 3. Billing and Subscription System

#### What It Does
Manages customer subscriptions, processes payments, enforces plan limits, and provides self-service billing management. Revenue collection must be fully automated.

#### Plan Structure

| Plan | Monthly Price | Monthly Quota | Rate Limit | Batch Size | SSO | Support |
|------|---------------|---------------|------------|------------|-----|---------|
| Free | $0 | 1,000 queries | 20/min | 10 | No | Community |
| Pro | $49 | 50,000 queries | 100/min | 50 | No | Email |
| Enterprise | $299 | 500,000 queries | 500/min | 200 | Yes | Priority |

#### Billing Events

**Subscription Lifecycle**
- Checkout completed (new subscription)
- Subscription created
- Subscription updated (plan change)
- Subscription canceled
- Subscription renewed

**Payment Events**
- Invoice paid
- Invoice payment failed
- Payment method updated

#### Jobs to Be Done

1. **Plan Configuration**
   - Create products and prices in payment provider
   - Create local mapping table (price ID → plan features)
   - Configure customer portal for self-service management

2. **Checkout Flow**
   - Create checkout session with tenant ID as reference
   - Include correct price ID for selected plan
   - Set success and cancel redirect URLs
   - Enable promotion codes if desired

3. **Webhook Processing**
   - Create webhook endpoint to receive payment provider events
   - Verify webhook signatures for security
   - Log all events for debugging and audit
   - Process each event type appropriately

4. **Subscription Sync**
   - On checkout completion, link payment customer ID to tenant
   - On subscription update, sync plan limits to tenant record
   - On subscription cancellation, downgrade to free tier
   - On payment failure, mark subscription as past due

5. **Access Enforcement**
   - During API key validation, check subscription status
   - Allow access if: active subscription, in trial, or free tier
   - Block access if: canceled, past due beyond grace period
   - Return appropriate error messages with upgrade prompts

6. **Customer Portal**
   - Generate portal session URL on demand
   - Customer can update payment method, view invoices, cancel subscription
   - Portal handles all billing UI (no custom development needed)

7. **Trial Management**
   - Set trial end date on tenant creation (e.g., 14 days)
   - Allow full access during trial period
   - Send reminder emails before trial ends (via payment provider or custom)
   - Convert to free tier if trial expires without subscription

#### Automation Requirements

- Subscription changes must sync to database automatically via webhooks
- Plan limits must update automatically when subscription changes
- Payment failures must automatically restrict access (with grace period)
- No manual intervention required for any billing operation

---

### 4. Rate Limiting System

#### What It Does
Prevents abuse by limiting how many requests a tenant can make per minute. Protects the API from overload and ensures fair usage across all customers.

#### Rate Limiting Strategy

**Algorithm**: Sliding window counter
- Divide time into fixed windows (1 minute)
- Count requests per tenant per window
- Reject requests when count exceeds limit

**Limits by Tier**
- Free: 20 requests per minute
- Pro: 100 requests per minute
- Enterprise: 500 requests per minute

**Headers to Return**
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Unix timestamp when window resets

#### Jobs to Be Done

1. **Counter Implementation**
   - On each request, increment counter for tenant + current minute window
   - Set counter expiration to 60 seconds on first increment
   - Retrieve current count and compare to limit

2. **Limit Lookup**
   - Get tenant's rate limit from cached auth context
   - Support per-API-key override if configured

3. **Request Handling**
   - If count <= limit: allow request, return remaining count in headers
   - If count > limit: reject with 429 status, return retry-after header

4. **Batch Request Handling**
   - Batch endpoints count as 1 request for rate limiting
   - But may count each query for quota purposes

#### Automation Requirements

- Rate limit counters must auto-expire (no cleanup jobs needed)
- Limit values must come from tenant config (auto-updated on plan change)
- No manual rate limit management required

---

### 5. Usage Quota System

#### What It Does
Tracks and enforces monthly query quotas. Prevents customers from exceeding their plan allocation and provides usage data for billing and analytics.

#### Quota Strategy

**Tracking**: Monthly counters
- Key format: `quota:{tenant_id}:{YYYY-MM}`
- Increment by query count on each request
- Reset automatically on month boundary (via key expiration)

**Quotas by Tier**
- Free: 1,000 queries per month
- Pro: 50,000 queries per month
- Enterprise: 500,000 queries per month

#### Jobs to Be Done

1. **Counter Implementation**
   - On each request, increment counter by number of queries
   - For single search: increment by 1
   - For batch search: increment by number of queries in batch
   - Set counter expiration to ~32 days on first increment (ensures cleanup)

2. **Quota Check**
   - Before processing request, check current usage against quota
   - If under quota: proceed
   - If over quota: reject with 429 and quota-specific error message

3. **Usage Reporting**
   - Provide endpoint for customers to check their usage
   - Return: queries used, quota limit, remaining, reset date

4. **Overage Handling** (optional future enhancement)
   - Option 1: Hard block (current)
   - Option 2: Allow overage with per-query billing
   - Option 3: Allow overage up to limit with warning emails

#### Automation Requirements

- Quotas must reset automatically each month (key expiration)
- Quota limits must update automatically on plan change
- No manual quota management required

---

### 6. Caching System

#### What It Does
Stores results of previous queries to serve repeat requests instantly without recomputing embeddings. Reduces latency, reduces cost, and improves user experience.

#### Caching Strategy

**Cache Key**: Hash of query + parameters
- Input: `{query_text}:{top_k}:{any_other_params}`
- Hash algorithm: MD5 (fast, collision-resistant enough for cache keys)
- Key format: `search:{md5_hash}`

**Cache Value**: Serialized search results
- Full response object (query, results, count)
- Serialized as JSON

**TTL**: 24 hours
- Uniclass codes don't change frequently
- Balance between freshness and hit rate
- Adjust based on data update frequency

#### Jobs to Be Done

1. **Cache Key Generation**
   - Normalize query (lowercase, trim whitespace)
   - Combine with parameters
   - Generate hash

2. **Cache Lookup**
   - Before search, check cache for key
   - If hit: return cached result, mark response as cached
   - If miss: proceed with search

3. **Cache Population**
   - After successful search, store result in cache
   - Set TTL on cache entry

4. **Cache Metrics**
   - Track cache hits vs misses
   - Report cache hit rate in observability

5. **Cache Invalidation** (if needed)
   - If underlying data changes, invalidate all cache entries
   - Simplest approach: let TTL handle invalidation
   - Advanced: prefix-based invalidation or versioned keys

#### Automation Requirements

- Cache entries must self-expire (no cleanup jobs)
- Cache population must be automatic on every cache miss
- No manual cache management required

---

### 7. Usage Logging System

#### What It Does
Records every API request for billing, analytics, debugging, and security auditing. Provides the data foundation for usage-based billing and customer analytics.

#### Log Schema

**Fields per Request**
- Tenant ID
- API Key ID
- Endpoint name
- Query count (1 for single, N for batch)
- Cache hit (boolean)
- Latency (milliseconds)
- HTTP status code
- Error message (if applicable)
- Timestamp

#### Jobs to Be Done

1. **Log Capture**
   - At end of each request, create log entry
   - Include all relevant fields
   - Do not block request on logging failure

2. **Async Logging**
   - Logging should not add latency to requests
   - Use fire-and-forget pattern
   - Accept occasional log loss over request delays

3. **Log Storage**
   - Store in database for queryability
   - Consider retention policy (e.g., 90 days detailed, aggregated forever)

4. **Log Aggregation**
   - Create views/queries for common aggregations
   - Daily usage per tenant
   - Monthly usage per tenant
   - Endpoint breakdown
   - Error rate trends

#### Automation Requirements

- Logging must be automatic on every request
- Log storage must handle volume without intervention
- Aggregations must be queryable without manual processing

---

### 8. Observability System

#### What It Does
Provides visibility into system health, performance, and usage patterns. Enables proactive issue detection and incident response.

#### Metrics to Collect

**Request Metrics**
- Request count (by endpoint, tenant tier, status code)
- Request latency (p50, p95, p99)
- Cache hit rate
- Error rate

**Business Metrics**
- Active tenants (made request in last 24h)
- Queries processed (total, by tier)
- Revenue by tier (derived from tenant counts)

**System Metrics**
- Container cold starts
- Memory usage
- Database connection pool

#### Alerting Rules

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Error rate | > 5% for 5 minutes | Alert to Slack/Email |
| p99 latency | > 2000ms for 5 minutes | Alert to Slack/Email |
| Database connection failures | Any | Alert immediately |
| Webhook processing failures | Any | Alert immediately |

#### Jobs to Be Done

1. **Metrics Collection**
   - Instrument every API endpoint with timing
   - Send metrics to time-series database
   - Include relevant dimensions (endpoint, tier, status, cached)

2. **Dashboard Creation**
   - Request rate over time
   - Latency percentiles over time
   - Error rate over time
   - Cache hit rate
   - Top tenants by usage

3. **Alert Configuration**
   - Set up alert rules for critical conditions
   - Configure notification channels (email, Slack)
   - Define escalation policies

4. **Health Endpoint**
   - Create public health check endpoint
   - Check database connectivity
   - Check cache connectivity
   - Return overall health status

#### Automation Requirements

- Metrics must be collected automatically on every request
- Alerts must fire automatically based on thresholds
- Dashboards must update in real-time
- No manual monitoring required

---

### 9. Webhook System

#### What It Does
Receives and processes events from external services (payment provider, SSO provider) to keep the system in sync with external state changes.

#### Webhook Sources

**Payment Provider Webhooks**
- Subscription lifecycle events
- Payment events
- Customer events

**SSO Provider Webhooks** (optional)
- User provisioning events (SCIM)
- Organization events

#### Jobs to Be Done

1. **Endpoint Security**
   - Verify webhook signatures to prevent spoofing
   - Use constant-time comparison for signatures
   - Reject requests with invalid signatures

2. **Idempotency**
   - Store event IDs to detect duplicates
   - Skip processing if event already handled
   - Return success even for duplicates (webhook retries)

3. **Event Processing**
   - Parse event type and payload
   - Route to appropriate handler
   - Update database based on event

4. **Error Handling**
   - Log all webhook events (success and failure)
   - Return appropriate status codes
   - Alert on repeated failures

5. **Event Logging**
   - Store all received events for debugging
   - Include raw payload for troubleshooting

#### Automation Requirements

- All webhook processing must be automatic
- Database updates must be automatic based on events
- No manual sync required between external services and database

---

## Service Selection Guide

### Recommended Stack (Free Tier Optimized)

| Component | Service | Free Tier | Why This Choice |
|-----------|---------|-----------|-----------------|
| **API Hosting** | Modal | $30/month credits | Already in use, serverless, auto-scaling |
| **Database** | Supabase | 500MB, 50K rows | PostgreSQL, built-in auth, instant API, RLS |
| **Cache** | Upstash Redis | 10K commands/day | Serverless Redis, no connection management |
| **Auth (Standard)** | Supabase Auth | 50K MAU | Included with Supabase, OAuth built-in |
| **Auth (SSO)** | WorkOS | 1M users | Enterprise SSO specialist, generous free tier |
| **Payments** | Stripe | Pay as you go | Industry standard, excellent webhooks |
| **Metrics** | Grafana Cloud | 10K series | Dashboards, alerts, free tier |
| **Uptime Monitoring** | Better Stack | 10 monitors | Simple, free, Slack integration |

### Alternative Options

| Component | Alternative | Trade-off |
|-----------|-------------|-----------|
| Database | PlanetScale | MySQL instead of PostgreSQL, better branching |
| Database | Neon | PostgreSQL, serverless, but newer |
| Cache | Redis Cloud | More features, but connection-based |
| Auth | Clerk | Better DX, but costs scale faster |
| Auth | Auth0 | More features, but complex and expensive |
| Payments | Paddle | Handles tax/VAT, but higher fees |
| Payments | LemonSqueezy | Simpler, but less mature |

---

## Implementation Sequence

### Phase 1: Foundation

**Objective**: Establish multi-tenancy and basic security

1. Set up database service
   - Create project
   - Run schema creation script (tenants, users, API keys, usage logs)
   - Create indexes and functions
   - Enable row-level security

2. Configure authentication
   - Enable email/password authentication
   - Configure OAuth providers (Google, Microsoft)
   - Set up email templates
   - Create signup trigger for automatic tenant provisioning

3. Update API endpoints
   - Add API key extraction from headers
   - Add API key validation logic
   - Add tenant context injection
   - Add basic error responses for auth failures

4. Create secrets configuration
   - Set up secrets management in Modal
   - Store all service credentials securely

### Phase 2: Protection

**Objective**: Add rate limiting, quotas, and caching

1. Set up cache service
   - Create Redis instance
   - Configure connection credentials

2. Implement rate limiting
   - Add rate limit check before request processing
   - Add rate limit headers to responses
   - Add 429 responses when exceeded

3. Implement quota tracking
   - Add quota check before request processing
   - Add quota increment after successful requests
   - Add quota error responses when exceeded

4. Implement query caching
   - Add cache lookup before search
   - Add cache population after search
   - Add cache hit indicator to responses

### Phase 3: Monetization

**Objective**: Add billing and subscription management

1. Configure payment provider
   - Create account and products
   - Configure customer portal
   - Set up webhook endpoint

2. Create checkout flow
   - Add function to create checkout sessions
   - Link checkout to tenant ID

3. Implement webhook handler
   - Create webhook endpoint
   - Verify signatures
   - Process subscription events
   - Sync plan limits to database

4. Create billing portal integration
   - Add function to create portal sessions
   - Allow customers to manage subscriptions

5. Enforce subscription status
   - Update API key validation to check subscription
   - Block access for canceled/past due subscriptions

### Phase 4: Enterprise Features

**Objective**: Add SSO for enterprise customers

1. Configure SSO provider
   - Create account
   - Get API credentials
   - Configure redirect URIs

2. Implement SSO check
   - Create endpoint to detect SSO for email domain
   - Return authorization URL if SSO configured

3. Implement SSO callback
   - Create callback endpoint
   - Exchange code for user profile
   - Create or update user record
   - Generate session token

4. Create SSO setup flow
   - Create admin function to configure SSO for tenant
   - Generate setup URL for customer IT admin
   - Store SSO configuration in tenant record

### Phase 5: Observability

**Objective**: Add monitoring, logging, and alerting

1. Configure metrics service
   - Create account
   - Get push credentials

2. Instrument API endpoints
   - Add timing to all requests
   - Send metrics on each request
   - Include relevant dimensions

3. Create dashboards
   - Request rate
   - Latency percentiles
   - Error rate
   - Cache hit rate
   - Usage by tenant tier

4. Configure alerts
   - Error rate threshold
   - Latency threshold
   - Payment failure events

5. Set up uptime monitoring
   - Add health endpoint monitors
   - Configure alert notifications

---

## Database Schema Summary

### Tables

1. **tenants**: Organizations using the product
2. **users**: Individual people within tenants
3. **api_keys**: Authentication tokens for API access
4. **usage_logs**: Record of every API request
5. **billing_events**: Webhook events for debugging
6. **plan_config**: Maps payment provider prices to features

### Key Relationships

```
tenants (1) ←→ (N) users
tenants (1) ←→ (N) api_keys
tenants (1) ←→ (N) usage_logs
api_keys (1) ←→ (N) usage_logs
users (1) ←→ (N) api_keys (created_by)
```

### Critical Functions

1. **handle_new_signup**: Creates tenant + user + API key on signup
2. **validate_api_key**: Validates API key and returns tenant context
3. **sync_stripe_subscription**: Updates tenant when subscription changes
4. **get_sso_config_for_domain**: Checks if email domain has SSO
5. **generate_api_key**: Creates new API key for tenant

---

## API Endpoint Summary

### Public Endpoints (No Auth)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| /health | GET | Health check for monitoring |
| /sso/check | GET | Check if email domain has SSO |
| /sso/callback | GET | Handle SSO authentication response |
| /webhooks/stripe | POST | Receive Stripe webhook events |

### Protected Endpoints (API Key Required)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| /search | GET | Single query search |
| /search | POST | Single query search (body) |
| /batch-search | POST | Multiple queries in one request |
| /usage | GET | Get current usage statistics |

### Admin Endpoints (Internal/Dashboard)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| /checkout | POST | Create Stripe checkout session |
| /portal | POST | Create Stripe portal session |
| /api-keys | POST | Generate new API key |
| /api-keys/{id} | DELETE | Revoke API key |

---

## Error Response Standards

### Format

All errors should follow a consistent format:

```json
{
  "error": "Human readable message",
  "code": "MACHINE_READABLE_CODE",
  "status": 401
}
```

### Error Codes

| Code | Status | Meaning |
|------|--------|---------|
| INVALID_API_KEY | 401 | API key format is wrong |
| UNAUTHORIZED | 401 | API key not found or inactive |
| TENANT_INACTIVE | 403 | Tenant account is deactivated |
| SUBSCRIPTION_REQUIRED | 403 | Subscription canceled or past due |
| INSUFFICIENT_SCOPE | 403 | API key doesn't have required scope |
| RATE_LIMITED | 429 | Too many requests per minute |
| QUOTA_EXCEEDED | 429 | Monthly quota exhausted |
| INVALID_REQUEST | 400 | Request body/params invalid |
| BATCH_TOO_LARGE | 400 | Batch size exceeds tier limit |
| INTERNAL_ERROR | 500 | Unexpected server error |

---

## Security Checklist

### API Security
- [ ] API keys are hashed before storage (SHA-256)
- [ ] API keys are never logged or returned after creation
- [ ] API key validation is cached (but not too long)
- [ ] Rate limiting prevents brute force attacks
- [ ] Input validation on all endpoints

### Authentication Security
- [ ] Passwords hashed with bcrypt/argon2 (handled by auth provider)
- [ ] Session tokens are short-lived
- [ ] SSO signatures are verified
- [ ] HTTPS enforced on all endpoints

### Webhook Security
- [ ] Signatures verified on all webhooks
- [ ] Events logged for audit trail
- [ ] Idempotency prevents replay attacks

### Data Security
- [ ] Row-level security enforces tenant isolation
- [ ] Service role key never exposed to frontend
- [ ] Database backups enabled
- [ ] Sensitive data encrypted at rest

---

## Testing Strategy

### Endpoint Testing

For each endpoint, verify:
1. Valid request returns expected response
2. Missing API key returns 401
3. Invalid API key returns 401
4. Inactive tenant returns 403
5. Rate limit exceeded returns 429
6. Quota exceeded returns 429
7. Invalid input returns 400

### Integration Testing

Verify flows:
1. Signup → tenant created → API key generated → can make API calls
2. Checkout → webhook received → plan updated → limits increased
3. Subscription canceled → webhook received → downgraded to free
4. SSO login → user created → added to correct tenant

### Load Testing

Verify:
1. Rate limiting works under load
2. Cache hit rate is acceptable
3. Latency percentiles meet targets
4. No errors under sustained load

---

## Operational Runbooks

### New Customer Onboarding
**Trigger**: Customer signs up
**Automated Actions**: 
- Tenant created with free tier
- API key generated
- Welcome email sent (if configured)
**Manual Actions**: None required

### Customer Upgrade
**Trigger**: Customer completes checkout
**Automated Actions**:
- Webhook updates subscription status
- Plan limits synced to database
- Confirmation email sent (by Stripe)
**Manual Actions**: None required

### Customer Payment Failure
**Trigger**: Invoice payment fails
**Automated Actions**:
- Webhook updates status to past_due
- Dunning emails sent (by Stripe)
**Manual Actions**: 
- Monitor for repeated failures
- Reach out if high-value customer

### Enterprise SSO Setup
**Trigger**: Enterprise customer requests SSO
**Automated Actions**:
- Run admin function to create SSO org
- Setup URL generated
**Manual Actions**:
- Send setup URL to customer IT admin
- Verify SSO works after customer configures

### API Outage Response
**Trigger**: Error rate alert fires
**Actions**:
1. Check health endpoint
2. Check database connectivity
3. Check cache connectivity
4. Check Modal dashboard for errors
5. Check recent deployments
6. Rollback if recent change caused issue

---

## Cost Optimization Tips

### Cache Aggressively
- Every cache hit saves an embedding computation
- 24-hour TTL is reasonable for stable data
- Monitor cache hit rate, aim for >70%

### Right-Size Rate Limits
- Free tier limits prevent abuse
- Don't make limits so high they allow cost attacks

### Batch Processing
- Batch search is more efficient than many single searches
- Encourage customers to use batch endpoint

### Cold Start Optimization
- Set container idle timeout appropriately (5 minutes)
- Frequently accessed endpoints stay warm
- Accept cold starts for rarely-used endpoints

### Database Query Optimization
- Cache API key validation results
- Use indexes on frequently queried columns
- Monitor slow queries

---

## Success Metrics

### Technical Metrics
- API latency p50 < 200ms (cached), p50 < 500ms (uncached)
- API latency p99 < 1000ms (cached), p99 < 2000ms (uncached)
- Error rate < 0.1%
- Cache hit rate > 70%
- Uptime > 99.9%

### Business Metrics
- Conversion rate (free to paid)
- Churn rate (paid to canceled)
- Revenue per tenant
- Customer lifetime value
- Support ticket volume

### Operational Metrics
- Mean time to detection (alerts)
- Mean time to resolution (incidents)
- Deployment frequency
- Change failure rate

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Initial | Complete enterprise transformation guide |

---

## References

### Service Documentation
- Modal: https://modal.com/docs
- Supabase: https://supabase.com/docs
- Upstash: https://upstash.com/docs
- Stripe: https://stripe.com/docs
- WorkOS: https://workos.com/docs
- Grafana: https://grafana.com/docs

### Standards
- OAuth 2.0: RFC 6749
- SAML 2.0: OASIS Standard
- SCIM 2.0: RFC 7643, RFC 7644

---

*This skill file provides a complete blueprint for enterprise transformation. An AI agent following this guide should be able to implement all components with appropriate service documentation and code generation capabilities.*
