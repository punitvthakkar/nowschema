# Uniclass Auto-Tagger Project

## Overview

This project automates the translation of natural language element names to Uniclass 2015 classification codes for MEP contractors in the UK construction industry.

### The Problem

MEP (Mechanical, Electrical, Plumbing) contractors receive drawings from architects with natural language element names. They must tag these elements with standardized Uniclass codes for compliance and interoperability. Currently, this requires hiring consultants to manually translate each element name—a costly and time-consuming process.

### The Solution

An AI-powered semantic search system that instantly matches natural language descriptions to the correct Uniclass 2015 codes, eliminating manual lookup and consultant fees.

---

## Current State: Enterprise Backend (In Progress)

### What's Working

| Feature | Status | Notes |
|---------|--------|-------|
| Core Search API | ✅ Working | Single + batch search on Modal with T4 GPU |
| Health Endpoint | ✅ Working | No auth required |
| Legacy API Key Auth | ✅ Working | Uses `UNICLASS_API_KEY` env var |
| In-Memory Rate Limiting | ✅ Working | Per-plan limits (free: 10/min, pro: 300/min) |
| In-Memory Caching | ✅ Working | Reduces duplicate query latency |
| In-Memory Usage Tracking | ✅ Working | Quota enforcement |
| HNSW Vector Index | ✅ Working | 19,022 items indexed |

### What's Not Working Yet

| Feature | Status | Issue |
|---------|--------|-------|
| Supabase Database | ❌ Not Connecting | Secrets exist in Modal but code shows "Using in-memory services" - needs debugging |
| Persistent API Keys | ❌ Blocked | Requires Supabase connection |
| Stripe Billing | ⏸️ Placeholder | Not implemented yet |
| WorkOS SSO | ⏸️ Placeholder | Not implemented yet |

---

## Live Endpoints

### Base URL Pattern
```
https://punitvthakkar--uniclass-api-uniclasssearchservice-<endpoint>.modal.run
```

### Available Endpoints (6 total - Modal free tier limit)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | None | Health check, shows service status |
| `/search` | POST | Bearer | Single or batch search |
| `/info` | POST | Bearer | Stats or usage info |
| `/api-keys` | POST | Bearer | Create/list/revoke keys (needs Supabase) |
| `/billing` | POST | Bearer | Placeholder - returns SERVICE_UNAVAILABLE |
| `/sso` | GET | None | Placeholder - returns SERVICE_UNAVAILABLE |

### Example: Search Request
```bash
curl -X POST "https://punitvthakkar--uniclass-api-uniclasssearchservice-search.modal.run" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "door handle", "top_k": 5}'
```

### Example: Batch Search
```bash
curl -X POST "https://punitvthakkar--uniclass-api-uniclasssearchservice-search.modal.run" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"action": "batch", "queries": ["door handle", "steel beam"], "top_k": 5}'
```

---

## Technical Architecture

### Backend Stack
- **Compute**: Modal.com (serverless GPU)
- **ML Model**: Nomic `nomic-embed-text-v1.5` (768-dim embeddings)
- **Vector Index**: HNSW via `hnswlib`
- **API Framework**: FastAPI (via Modal's `@modal.fastapi_endpoint`)
- **Database**: Supabase (PostgreSQL) - NOT CONNECTED YET
- **Secrets**: Modal Secrets (`uniclass-enterprise-secrets`)

### Modal Secrets Configuration
The following secrets are configured in Modal under `uniclass-enterprise-secrets`:
- `UNICLASS_API_KEY` - Legacy API key for authentication
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_KEY` - Supabase service role key
- `SUPABASE_ANON_KEY` - Supabase anon key (not used currently)
- `JWT_SECRET` - For future JWT auth
- `UPSTASH_REDIS_URL` - For future Redis caching
- `UPSTASH_REDIS_TOKEN` - For future Redis caching

### Supabase Database Schema
Tables created in Supabase:
- `tenants` - Organizations using the API
- `users` - Individual users within tenants
- `api_keys` - API keys with hash, prefix, scopes, expiry

---

## File Structure

```
nowschema/
├── backend/
│   ├── modal_api.py              # Main API (self-contained, no external imports)
│   └── services/                 # Service modules (NOT USED - kept for reference)
│       ├── database.py
│       ├── auth.py
│       ├── api_keys.py
│       ├── rate_limit.py
│       ├── cache.py
│       ├── usage.py
│       ├── billing.py
│       ├── sso.py
│       └── observability.py
├── frontend/                     # Next.js admin dashboard (not deployed)
│   ├── src/
│   │   ├── app/
│   │   └── components/
│   │       └── CredentialsDialog.tsx
│   └── package.json
├── infra/
│   └── supabase/
│       └── migrations/
│           ├── 001_initial_schema.sql
│           └── 002_admin_functions.sql
├── .github/
│   └── workflows/
│       ├── deploy-backend.yml    # Deploys to Modal
│       ├── deploy-frontend.yml   # Deploys to Vercel (not configured)
│       └── setup-secrets.yml     # Sets up Modal secrets
└── claude.md                     # This file
```

---

## Next Steps (Priority Order)

### 1. Debug Supabase Connection (CRITICAL)
**Problem**: Modal secrets are configured correctly but the API logs show "Using in-memory services (no external dependencies)" instead of connecting to Supabase.

**To Debug**:
1. Check Modal App Logs after fresh deployment
2. Look for "Supabase connected" or "Supabase connection failed: <error>"
3. Verify environment variables are being read in the container
4. May need to add debug logging to print env var existence (not values)

**Possible Issues**:
- Container caching (try stopping app before redeploy)
- Secret not being injected into container
- Supabase client initialization failing silently

### 2. Complete Supabase Integration
Once connected:
- Test API key creation via `/api-keys` endpoint
- Test API key validation (search with database-stored key)
- Verify `last_used_at` updates on key usage

### 3. Deploy Admin Frontend
- Configure Vercel deployment
- Set up environment variables
- Connect to backend API

### 4. Add Stripe Billing (Later)
- Create Stripe account
- Set up products/prices
- Implement checkout flow
- Handle webhooks

### 5. Add WorkOS SSO (Later)
- Create WorkOS account
- Configure SAML/OIDC
- Implement SSO flow

---

## Development Commands

### Deploy Backend
```bash
# Via GitHub Actions (recommended)
# Go to: GitHub → Actions → Deploy Backend to Modal → Run workflow

# Or locally with Modal CLI
cd backend
modal deploy modal_api.py
```

### Run Database Migration
```sql
-- In Supabase SQL Editor
-- Paste contents of infra/supabase/migrations/001_initial_schema.sql
```

### Test API
```bash
# Health check
curl "https://punitvthakkar--uniclass-api-uniclasssearchservice-health.modal.run"

# Search
curl -X POST "https://punitvthakkar--uniclass-api-uniclasssearchservice-search.modal.run" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "concrete slab", "top_k": 5}'
```

---

## API Key for Testing
Current legacy API key (stored in Modal secrets as `UNICLASS_API_KEY`):
```
YGib3sbjtUFXrAHP0CxAnxoIRSNtZasewweaDasda
```

---

## Performance

| Metric | Value |
|--------|-------|
| Cold start | ~20-30 seconds (loading model + index) |
| Warm request | ~500-800ms |
| Items indexed | 19,022 |
| Embedding dimension | 768 |
| GPU | NVIDIA T4 |

---

## Cost Estimates (Modal)

| Plan | Monthly Cost |
|------|-------------|
| Free tier | $30 credits |
| Current usage | ~$4.50 remaining |

---

## Notes

- Modal containers scale to zero when idle - first request after idle has cold start latency
- The `modal_api.py` file is self-contained with no external module imports (required for Modal deployment)
- All enterprise service modules in `backend/services/` are kept for reference but not used
- Frontend is built but not deployed - waiting for backend database integration
