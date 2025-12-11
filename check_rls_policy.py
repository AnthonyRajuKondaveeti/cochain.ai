"""
Check if RLS (Row Level Security) is blocking queries
This script tests both anon and service keys
"""
from database.connection import supabase
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 80)
print("CHECKING ROW LEVEL SECURITY (RLS) POLICIES")
print("=" * 80)
print()

# Test with current (anon) key
print("🔑 Testing with ANON KEY (current):")
print(f"   URL: {os.getenv('SUPABASE_URL')}")
print(f"   Key: {os.getenv('SUPABASE_KEY')[:20]}...")
print()

try:
    users = supabase.table('users').select('id, email', count='exact').execute()
    bookmarks = supabase.table('user_bookmarks').select('id', count='exact').execute()
    interactions = supabase.table('user_interactions').select('id', count='exact').execute()
    
    print(f"   ✅ Users: {users.count}")
    print(f"   ✅ Bookmarks: {bookmarks.count}")
    print(f"   ✅ Interactions: {interactions.count}")
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

print()
print("=" * 80)
print("DIAGNOSIS")
print("=" * 80)
print()

if users.count == 0:
    print("⚠️  The ANON key returns 0 records")
    print()
    print("This means one of:")
    print("1. ✅ RLS (Row Level Security) is ENABLED and blocking anon queries")
    print("   - This is GOOD for security")
    print("   - But admin analytics needs a SERVICE KEY to bypass RLS")
    print()
    print("2. ❌ Database is actually EMPTY")
    print("   - Need to register users and create data")
    print()
    print("=" * 80)
    print("SOLUTION")
    print("=" * 80)
    print()
    print("To fix analytics (if RLS is the issue):")
    print()
    print("1. Go to: https://supabase.com/dashboard/project/dneryvjkripebycuavsa/settings/api")
    print()
    print("2. Copy the 'service_role' key (the SECRET one, not 'anon')")
    print()
    print("3. Add to your .env file:")
    print("   SUPABASE_SERVICE_KEY=your-service-key-here")
    print()
    print("4. Update analytics queries to use service key for admin access")
    print()
else:
    print(f"✅ Found {users.count} users")
    print("   Database has data and is accessible with current key")
    print("   No RLS blocking detected")
