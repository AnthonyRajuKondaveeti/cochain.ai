"""
Test script to verify admin endpoints and database queries
"""
from database.connection import supabase_admin
import json

print("=" * 60)
print("Testing Admin Database Queries")
print("=" * 60)

# Test 1: Check if supabase_admin works
print("\n1. Testing supabase_admin connection...")
try:
    users_result = supabase_admin.table('users').select('id, email', count='exact').limit(5).execute()
    print(f"   ✅ Connection successful!")
    print(f"   Total users: {users_result.count}")
    print(f"   Sample users: {len(users_result.data)} fetched")
    for user in users_result.data:
        print(f"      - {user.get('email', 'N/A')}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Check user_engagement_summary view/table
print("\n2. Testing user_engagement_summary view...")
try:
    engagement_result = supabase_admin.table('user_engagement_summary')\
        .select('*')\
        .limit(5)\
        .execute()
    print(f"   ✅ View accessible!")
    print(f"   Records found: {len(engagement_result.data)}")
    if engagement_result.data:
        print(f"   Sample columns: {list(engagement_result.data[0].keys())}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    print(f"   Note: This view might not exist. Check if it needs to be created.")

# Test 3: Check user_bookmarks table
print("\n3. Testing user_bookmarks table...")
try:
    bookmarks_result = supabase_admin.table('user_bookmarks').select('id', count='exact').execute()
    print(f"   ✅ Table accessible!")
    print(f"   Total bookmarks: {bookmarks_result.count}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 4: Check user_interactions table
print("\n4. Testing user_interactions table...")
try:
    interactions_result = supabase_admin.table('user_interactions').select('id, interaction_type', count='exact').execute()
    print(f"   ✅ Table accessible!")
    print(f"   Total interactions: {interactions_result.count}")
    
    # Group by interaction type
    if interactions_result.data:
        types = {}
        for item in interactions_result.data:
            itype = item.get('interaction_type', 'unknown')
            types[itype] = types.get(itype, 0) + 1
        print(f"   Interaction types: {types}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 5: Check user_sessions table
print("\n5. Testing user_sessions table...")
try:
    sessions_result = supabase_admin.table('user_sessions').select('id', count='exact').execute()
    print(f"   ✅ Table accessible!")
    print(f"   Total sessions: {sessions_result.count}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("Test Complete!")
print("=" * 60)
