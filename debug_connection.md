# Debugging Modal-Supabase Connection

## Problem
Modal logs show "Using in-memory services (no external dependencies)" instead of "Supabase connected"

## Root Cause Analysis

The code in `modal_api.py:345-363` checks for these environment variables:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`

If BOTH are present and non-empty, it will try to connect. If either is missing/empty, it skips Supabase.

## Step-by-Step Debugging

### 1. Check Health Endpoint

Run this command to see which services are connected:

```bash
curl "https://punitvthakkar--uniclass-api-uniclasssearchservice-health.modal.run"
```

Look for the `services` object. If `database: false`, Supabase is NOT connected.

Expected when working:
```json
{
  "status": "healthy",
  "items_indexed": 19022,
  "embedding_dim": 768,
  "services": {
    "database": true,    // ← Should be true!
    "cache": true,
    "rate_limit": true,
    "usage": true,
    "billing": false,
    "sso": false
  }
}
```

### 2. Verify Modal Secrets Exist

```bash
# Install Modal CLI if not already installed
pip install modal

# Authenticate with Modal (if not already)
modal token set --token-id YOUR_TOKEN_ID --token-secret YOUR_TOKEN_SECRET

# List all secrets
modal secret list

# View the specific secret (values will be masked)
modal secret get uniclass-enterprise-secrets
```

You should see:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `SUPABASE_ANON_KEY`
- `UNICLASS_API_KEY`
- `JWT_SECRET`
- Others...

### 3. Check Secret Values Are Correct

The secrets must be EXACTLY:
- **Secret name in Modal**: `uniclass-enterprise-secrets` (matches line 285 in modal_api.py)
- **Environment variable names**:
  - `SUPABASE_URL` (NOT `SUPABASE_PROJECT_URL` or anything else)
  - `SUPABASE_SERVICE_KEY` (NOT `SUPABASE_KEY` or `SUPABASE_SERVICE_ROLE_KEY`)

### 4. Get Your Supabase Credentials

From your Supabase project dashboard:

1. Go to **Project Settings** → **API**
2. Copy these values:
   - **Project URL**: This is your `SUPABASE_URL`
   - **Project API keys** → **service_role** → **secret**: This is your `SUPABASE_SERVICE_KEY`

The URL should look like: `https://abcdefghijklmnop.supabase.co`

### 5. Update Modal Secrets

If secrets are missing or wrong, recreate them:

```bash
# Delete old secret
modal secret delete uniclass-enterprise-secrets

# Create new secret with correct values
modal secret create uniclass-enterprise-secrets \
  SUPABASE_URL="https://YOUR_PROJECT.supabase.co" \
  SUPABASE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  UNICLASS_API_KEY="YGib3sbjtUFXrAHP0CxAnxoIRSNtZasewweaDasda" \
  JWT_SECRET="$(openssl rand -hex 32)" \
  UPSTASH_REDIS_URL="" \
  UPSTASH_REDIS_TOKEN=""
```

**IMPORTANT**: Replace the placeholder values with your actual credentials!

### 6. Redeploy After Updating Secrets

After updating secrets, you MUST redeploy:

```bash
cd backend
modal deploy modal_api.py
```

Or trigger the GitHub Action: **Actions** → **Deploy Backend to Modal** → **Run workflow**

### 7. Verify Connection Again

Wait ~30 seconds for deployment, then check health again:

```bash
curl "https://punitvthakkar--uniclass-api-uniclasssearchservice-health.modal.run"
```

Now `"database": true` should appear!

### 8. Test Database Connection

Once connected, test creating a tenant and API key:

```bash
# Create a test tenant using the /api-keys endpoint
curl -X POST "https://punitvthakkar--uniclass-api-uniclasssearchservice-api-keys.modal.run" \
  -H "Authorization: Bearer YGib3sbjtUFXrAHP0CxAnxoIRSNtZasewweaDasda" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create",
    "tenant_name": "Test Company",
    "tenant_slug": "test-company",
    "user_email": "admin@test.com",
    "key_name": "Production API Key"
  }'
```

If working, you'll get back a new API key starting with `uc_live_...`

## Common Issues

### Issue: "Using in-memory services"
**Cause**: Secrets not loaded or empty
**Fix**: Check steps 2-6 above

### Issue: "Supabase connection failed: X"
**Cause**: Wrong credentials or network issue
**Fix**: Verify credentials in step 4, check Supabase is not paused

### Issue: Health shows database: false
**Cause**: Code skipped Supabase initialization
**Fix**: Check Modal logs during deployment for error messages

### Issue: Secrets exist but still not connecting
**Cause**: Deployment didn't pick up new secrets
**Fix**: Force redeploy with `modal deploy modal_api.py`

## Debug Logging

To see what's happening during initialization, check Modal logs:

```bash
modal app logs uniclass-api
```

Look for these lines:
- `🚀 Initializing Uniclass Enterprise API...`
- `→ Supabase connected` (GOOD!)
- `⚠ Supabase connection failed: ...` (shows error)
- `→ Supabase not configured (using legacy API key only)` (secrets missing)

## Next Steps After Connection Works

1. ✅ Create a test tenant and user
2. ✅ Generate an API key via `/api-keys` endpoint
3. ✅ Test search with the new database-backed API key
4. ✅ Verify `last_used_at` updates in Supabase after using the key
5. ✅ Check usage logs are being written to `usage_logs` table
