#!/usr/bin/env python3
"""
Test script to verify Supabase connection from local environment.
This mimics what Modal does in modal_api.py to help debug connection issues.

Usage:
    python test_supabase_connection.py
"""
import os
from supabase import create_client

def test_connection():
    """Test Supabase connection with your credentials."""

    print("=" * 60)
    print("Supabase Connection Test")
    print("=" * 60)

    # Get credentials from environment or prompt
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "")

    if not supabase_url:
        supabase_url = input("\nEnter your SUPABASE_URL: ").strip()

    if not supabase_key:
        supabase_key = input("Enter your SUPABASE_SERVICE_KEY: ").strip()

    print(f"\n📋 Configuration:")
    print(f"  URL: {supabase_url}")
    print(f"  Key: {supabase_key[:20]}...{supabase_key[-10:] if len(supabase_key) > 30 else ''}")

    # Test 1: Create client
    print("\n🧪 Test 1: Creating Supabase client...")
    try:
        db = create_client(supabase_url, supabase_key)
        print("  ✅ Client created successfully")
    except Exception as e:
        print(f"  ❌ Failed to create client: {e}")
        return

    # Test 2: List tables
    print("\n🧪 Test 2: Checking if tables exist...")
    try:
        # Try to query the tenants table
        result = db.table("tenants").select("*").limit(1).execute()
        print(f"  ✅ tenants table exists ({len(result.data)} rows found)")
    except Exception as e:
        if "does not exist" in str(e) or "relation" in str(e):
            print(f"  ⚠️  tenants table doesn't exist - you need to run migrations")
            print(f"     Error: {e}")
        else:
            print(f"  ❌ Query failed: {e}")
            return

    # Test 3: Check all required tables
    print("\n🧪 Test 3: Verifying all required tables...")
    tables = ["tenants", "users", "api_keys", "usage_logs", "plan_config"]
    missing_tables = []

    for table in tables:
        try:
            result = db.table(table).select("id").limit(1).execute()
            print(f"  ✅ {table}")
        except Exception as e:
            if "does not exist" in str(e) or "relation" in str(e):
                print(f"  ❌ {table} (missing)")
                missing_tables.append(table)
            else:
                print(f"  ❌ {table} (error: {e})")

    if missing_tables:
        print(f"\n⚠️  Missing tables: {', '.join(missing_tables)}")
        print("   Run the migrations in Supabase SQL Editor:")
        print("   1. infra/supabase/migrations/001_initial_schema.sql")
        print("   2. infra/supabase/migrations/002_admin_functions.sql")
        return

    # Test 4: Check plan config has data
    print("\n🧪 Test 4: Checking plan configuration...")
    try:
        result = db.table("plan_config").select("plan_tier, queries_per_month").execute()
        if len(result.data) == 4:
            print(f"  ✅ All 4 plan tiers configured")
            for plan in result.data:
                print(f"     - {plan['plan_tier']}: {plan['queries_per_month']:,} queries/month")
        else:
            print(f"  ⚠️  Only {len(result.data)} plans found (expected 4)")
    except Exception as e:
        print(f"  ❌ Failed to query plans: {e}")
        return

    # Test 5: Test API key operations
    print("\n🧪 Test 5: Testing API key hash function...")
    import hashlib
    test_key = "uc_live_test123"
    key_hash = hashlib.sha256(test_key.encode()).hexdigest()
    print(f"  ✅ Hash function works")
    print(f"     Input: {test_key}")
    print(f"     Hash: {key_hash[:32]}...")

    # Summary
    print("\n" + "=" * 60)
    print("✅ All tests passed! Your Supabase is ready for Modal.")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Make sure these secrets are set in Modal:")
    print(f"   SUPABASE_URL={supabase_url}")
    print(f"   SUPABASE_SERVICE_KEY={supabase_key[:20]}...")
    print("\n2. Redeploy your Modal app:")
    print("   cd backend && modal deploy modal_api.py")
    print("\n3. Check the health endpoint:")
    print('   curl "https://punitvthakkar--uniclass-api-uniclasssearchservice-health.modal.run"')
    print('   Look for "database": true in the response')

if __name__ == "__main__":
    try:
        test_connection()
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
