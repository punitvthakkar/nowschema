# Uniclass Auto-Tagger Project

## 🎯 Recent Update (Dec 2025)

✅ **Supabase Integration Complete!**
- Database connection successfully established between Modal and Supabase
- All tables and functions migrated (tenants, users, api_keys, usage_logs, etc.)
- Persistent API key management now working
- Health endpoint confirms: `"database": true`

🚀 **Next: Revit Plugin Development**

---

## Overview

This project automates the translation of natural language element names to Uniclass 2015 classification codes for MEP contractors in the UK construction industry.

### The Problem

MEP (Mechanical, Electrical, Plumbing) contractors receive drawings from architects with natural language element names. They must tag these elements with standardized Uniclass codes for compliance and interoperability. Currently, this requires hiring consultants to manually translate each element name—a costly and time-consuming process.

### The Solution

An AI-powered semantic search system that instantly matches natural language descriptions to the correct Uniclass 2015 codes, eliminating manual lookup and consultant fees.

---

## Current State: Enterprise Backend ✅

### What's Working

| Feature | Status | Notes |
|---------|--------|-------|
| Core Search API | ✅ Working | Single + batch search on Modal with T4 GPU |
| Health Endpoint | ✅ Working | No auth required |
| Legacy API Key Auth | ✅ Working | Uses `UNICLASS_API_KEY` env var |
| **Supabase Database** | ✅ **Connected** | Successfully connected to PostgreSQL backend |
| **Persistent API Keys** | ✅ **Ready** | Can create/list/revoke keys via `/api-keys` endpoint |
| Database Schema | ✅ Working | All tables & functions migrated successfully |
| In-Memory Rate Limiting | ✅ Working | Per-plan limits (free: 10/min, pro: 300/min) |
| In-Memory Caching | ✅ Working | Reduces duplicate query latency |
| In-Memory Usage Tracking | ✅ Working | Quota enforcement |
| HNSW Vector Index | ✅ Working | 19,022 items indexed |

### What's Not Implemented Yet

| Feature | Status | Notes |
|---------|--------|-------|
| Stripe Billing | ⏸️ Placeholder | Returns SERVICE_UNAVAILABLE |
| WorkOS SSO | ⏸️ Placeholder | Returns SERVICE_UNAVAILABLE |
| Admin Dashboard | ⏸️ Built | Frontend exists but not deployed to Vercel |

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
- `usage_logs` - API usage tracking per tenant
- `billing_events` - Stripe webhook events
- `plan_config` - Plan tier configuration (free/starter/professional/enterprise)

### Debugging Tools
Created for troubleshooting Modal-Supabase connection:
- `test_supabase_connection.py` - Local script to verify Supabase connection
- `debug_connection.md` - Comprehensive troubleshooting guide
- `infra/supabase/migrations/000_cleanup.sql` - Database reset script

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
│           ├── 000_cleanup.sql         # Database reset script
│           ├── 001_initial_schema.sql  # Core tables and schema
│           └── 002_admin_functions.sql # Admin functions and views
├── .github/
│   └── workflows/
│       ├── deploy-backend.yml    # Deploys to Modal
│       ├── deploy-frontend.yml   # Deploys to Vercel (not configured)
│       └── setup-secrets.yml     # Sets up Modal secrets
├── test_supabase_connection.py   # Local Supabase connection test
├── debug_connection.md           # Troubleshooting guide
└── claude.md                     # This file
```

---

## Next Steps (Priority Order)

### 1. 🚀 Create Revit Plugin (CURRENT PRIORITY)
**Goal**: Build a Revit plugin that allows MEP contractors to automatically tag elements with Uniclass codes.

**Requirements**:
- Plugin should integrate into Revit's UI
- Allow users to:
  - Select elements in a Revit model
  - Query the Uniclass API with element names
  - Apply returned Uniclass codes as parameters to elements
  - Batch process multiple elements at once
- Authentication via API key
- Error handling for API failures
- Progress indicator for batch operations

**Technical Approach**:
- Language: C# (.NET Framework - Revit API requirement)
- Use Revit API for element access and parameter modification
- HTTP client to call Modal endpoints:
  - `/search` for single element lookups
  - `/search` with `action: batch` for bulk operations
- Store API key securely (encrypted in user settings)

**Deliverables**:
1. Revit add-in (.addin manifest file)
2. Plugin DLL with UI and API integration
3. Installer/deployment instructions
4. User documentation

---

### 2. Deploy Admin Frontend
- Configure Vercel deployment
- Set up environment variables
- Connect to backend API
- Enable tenant/user management UI

### 3. Add Stripe Billing (Later)
- Create Stripe account
- Set up products/prices for free/starter/professional/enterprise tiers
- Implement checkout flow
- Handle webhooks for subscription lifecycle

### 4. Add WorkOS SSO (Later)
- Create WorkOS account
- Configure SAML/OIDC providers
- Implement SSO flow for enterprise customers

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
```bash
# In Supabase SQL Editor, run these in order:
# 1. infra/supabase/migrations/001_initial_schema.sql
# 2. infra/supabase/migrations/002_admin_functions.sql

# To reset database (WARNING: deletes all data):
# Run infra/supabase/migrations/000_cleanup.sql first
```

### Test Supabase Connection Locally
```bash
# Install dependencies
pip install supabase

# Run test script (will prompt for credentials)
python test_supabase_connection.py

# Or with environment variables
SUPABASE_URL="https://your-project.supabase.co" \
SUPABASE_SERVICE_KEY="your-service-key" \
python test_supabase_connection.py
```

### Test API
```bash
# Health check (should show "database": true)
curl "https://punitvthakkar--uniclass-api-uniclasssearchservice-health.modal.run"

# Create a new API key (using legacy key for auth)
curl -X POST "https://punitvthakkar--uniclass-api-uniclasssearchservice-api-keys.modal.run" \
  -H "Authorization: Bearer YGib3sbjtUFXrAHP0CxAnxoIRSNtZasewweaDasda" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create",
    "tenant_name": "My Company",
    "tenant_slug": "my-company",
    "user_email": "admin@mycompany.com",
    "key_name": "Production API Key"
  }'

# Search with API key
curl -X POST "https://punitvthakkar--uniclass-api-uniclasssearchservice-search.modal.run" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "concrete slab", "top_k": 5}'

# Check usage stats
curl -X POST "https://punitvthakkar--uniclass-api-uniclasssearchservice-info.modal.run" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"action": "usage"}'
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
