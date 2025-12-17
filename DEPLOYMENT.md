# Uniclass API Enterprise - Deployment Guide

This guide walks you through deploying the Uniclass API with all enterprise features.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Modal account (for API hosting)
- Service accounts (see below)

## Required Service Accounts

Create accounts and obtain credentials for:

| Service | Purpose | Free Tier | Sign Up |
|---------|---------|-----------|---------|
| **Modal** | API Hosting | $30/month credits | [modal.com](https://modal.com) |
| **Supabase** | Database | 500MB, 50K rows | [supabase.com](https://supabase.com) |
| **Upstash** | Redis Cache | 10K commands/day | [upstash.com](https://upstash.com) |
| **Stripe** | Payments | Pay-as-you-go | [stripe.com](https://stripe.com) |
| **WorkOS** | Enterprise SSO | 1M users | [workos.com](https://workos.com) |
| **Grafana Cloud** | Observability | 10K series | [grafana.com](https://grafana.com) |

## Step 1: Database Setup (Supabase)

1. Create a new Supabase project
2. Go to SQL Editor and run the migrations:

```bash
# Run these SQL files in order:
infra/supabase/migrations/001_initial_schema.sql
infra/supabase/migrations/002_admin_functions.sql
```

3. Get your credentials from Project Settings > API:
   - Project URL
   - `anon` public key
   - `service_role` secret key

## Step 2: Redis Setup (Upstash)

1. Create a new Redis database at [console.upstash.com](https://console.upstash.com)
2. Copy the REST URL and REST Token from the database details

## Step 3: Configure Modal Secrets

Create a Modal secret with all your credentials:

```bash
modal secret create uniclass-enterprise-secrets \
  SUPABASE_URL="https://xxx.supabase.co" \
  SUPABASE_ANON_KEY="eyJ..." \
  SUPABASE_SERVICE_KEY="eyJ..." \
  UPSTASH_REDIS_URL="https://xxx.upstash.io" \
  UPSTASH_REDIS_TOKEN="AX..." \
  STRIPE_SECRET_KEY="sk_live_..." \
  STRIPE_WEBHOOK_SECRET="whsec_..." \
  STRIPE_PRICE_ID_STARTER="price_..." \
  STRIPE_PRICE_ID_PROFESSIONAL="price_..." \
  STRIPE_PRICE_ID_ENTERPRISE="price_..." \
  WORKOS_API_KEY="sk_..." \
  WORKOS_CLIENT_ID="client_..." \
  GRAFANA_API_KEY="glc_..." \
  GRAFANA_ENDPOINT="https://xxx.grafana.net" \
  JWT_SECRET="your-secure-random-string" \
  ENVIRONMENT="production"
```

**Tip:** Use the Admin Frontend's "Copy Modal Secret Command" button to generate this command automatically.

## Step 4: Deploy Backend

```bash
cd backend

# Install Modal CLI
pip install modal

# Authenticate with Modal
modal token set --token-id "ak-xxx" --token-secret "as-xxx"

# Deploy the API
modal deploy modal_api.py
```

After deployment, you'll see URLs like:
- `https://punitvthakkar--uniclass-api-uniclasssearchservice-health.modal.run`
- `https://punitvthakkar--uniclass-api-uniclasssearchservice-search-get.modal.run`

## Step 5: Deploy Frontend

```bash
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

# Deploy to your hosting provider (Vercel, Netlify, etc.)
# Or run locally:
npm run start
```

### Deploy to Vercel (Recommended)

```bash
npm install -g vercel
vercel
```

## Step 6: Configure Stripe Webhooks

1. Go to Stripe Dashboard > Developers > Webhooks
2. Add endpoint: `https://your-modal-url/stripe_webhook`
3. Select events:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.paid`
   - `invoice.payment_failed`
4. Copy the webhook signing secret to Modal secrets

## Step 7: Configure WorkOS (Optional - Enterprise SSO)

1. Go to WorkOS Dashboard
2. Create an organization
3. Configure SSO connection (SAML or OIDC)
4. Set redirect URI: `https://your-modal-url/sso_callback`

## Verification

Test your deployment:

```bash
# Health check
curl https://your-modal-url-health.modal.run

# Search (requires API key)
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://your-modal-url-search-get.modal.run?q=door+handle"
```

## Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Supabase project URL | Yes |
| `SUPABASE_ANON_KEY` | Supabase anon key | Yes |
| `SUPABASE_SERVICE_KEY` | Supabase service key | Yes |
| `UPSTASH_REDIS_URL` | Upstash REST URL | Yes |
| `UPSTASH_REDIS_TOKEN` | Upstash REST token | Yes |
| `STRIPE_SECRET_KEY` | Stripe secret key | No* |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook secret | No* |
| `STRIPE_PRICE_ID_STARTER` | Stripe price ID | No* |
| `STRIPE_PRICE_ID_PROFESSIONAL` | Stripe price ID | No* |
| `STRIPE_PRICE_ID_ENTERPRISE` | Stripe price ID | No* |
| `WORKOS_API_KEY` | WorkOS API key | No** |
| `WORKOS_CLIENT_ID` | WorkOS client ID | No** |
| `GRAFANA_API_KEY` | Grafana Cloud API key | No |
| `GRAFANA_ENDPOINT` | Grafana Cloud endpoint | No |
| `JWT_SECRET` | JWT signing secret | Yes |
| `ENVIRONMENT` | production/development | Yes |

\* Required for billing features
\** Required for SSO features

## Troubleshooting

### API returns 500 errors
- Check Modal logs: `modal app logs uniclass-api`
- Verify all secrets are configured correctly

### Database connection fails
- Ensure Supabase project is active
- Check service key has correct permissions
- Verify RLS policies allow service role access

### Rate limiting not working
- Verify Upstash credentials
- Check Redis connection in health endpoint

### Billing webhooks not received
- Verify webhook URL is accessible
- Check Stripe webhook logs for errors
- Ensure webhook secret matches

## Support

For issues and questions:
- GitHub Issues: [github.com/punitvthakkar/nowschema](https://github.com/punitvthakkar/nowschema)
- Documentation: See `claude.md` and `futurestack.md`
