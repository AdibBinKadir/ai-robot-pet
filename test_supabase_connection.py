#!/usr/bin/env python3
"""
Test Supabase connection and storage permissions
"""
import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv('my-app/src/backend/.env')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')

print("🔧 Testing Supabase Connection...")
print(f"URL: {SUPABASE_URL}")
print(f"Service Key: {SUPABASE_SERVICE_ROLE_KEY[:20]}..." if SUPABASE_SERVICE_ROLE_KEY else "Service Key: NOT SET")
print(f"Anon Key: {SUPABASE_ANON_KEY[:20]}..." if SUPABASE_ANON_KEY else "Anon Key: NOT SET")

if not all([SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY]):
    print("❌ Missing required environment variables!")
    exit(1)

try:
    # Test with service role key
    print("\n🔍 Testing service role connection...")
    supabase_service = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    
    # Test database access
    print("📊 Testing database access...")
    result = supabase_service.table('photos').select('count').execute()
    print("✅ Database access successful!")
    
    # Test storage access
    print("💾 Testing storage access...")
    buckets = supabase_service.storage.list_buckets()
    print(f"✅ Found buckets: {[b.name for b in buckets]}")
    
    # Test specific bucket access
    print("🗂️ Testing 'images' bucket access...")
    try:
        files = supabase_service.storage.from_('images').list()
        print(f"✅ Images bucket accessible! Found {len(files)} files")
    except Exception as e:
        print(f"❌ Images bucket error: {e}")
    
    print("\n🎉 All tests passed! Your backend should work.")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("\n🔧 Possible fixes:")
    print("1. Double-check your service role key in Supabase Dashboard")
    print("2. Make sure the key hasn't expired")
    print("3. Check if storage policies allow service role access")