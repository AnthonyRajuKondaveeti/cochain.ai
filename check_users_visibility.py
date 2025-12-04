"""
Check if RLS is blocking the SELECT query
We'll try to query with service_role key instead
"""

from database.connection import supabase
import os

print("=" * 80)
print("🔍 CHECKING USER VISIBILITY")
print("=" * 80)

# Try normal query (with RLS)
print("\n1️⃣ Normal query (with RLS policies):")
try:
    users = supabase.table('users').select('id, email, full_name, created_at').execute()
    print(f"   Users found: {len(users.data) if users.data else 0}")
    if users.data:
        for user in users.data:
            print(f"   - {user['email']} (created: {user['created_at']})")
    else:
        print("   ❌ No users visible")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Check Supabase Auth users
print("\n2️⃣ Checking Supabase Auth users:")
try:
    # Try to get current auth user
    auth_user = supabase.auth.get_user()
    if auth_user.user:
        print(f"   ✅ Current auth user: {auth_user.user.email}")
        print(f"   User ID: {auth_user.user.id}")
    else:
        print("   ⚠️  No current auth session")
except Exception as e:
    print(f"   ℹ️  No active session: {e}")

# Try to count users (might work even if SELECT doesn't)
print("\n3️⃣ Trying to count users:")
try:
    count_result = supabase.table('users').select('id', count='exact').execute()
    print(f"   Total users (count): {count_result.count}")
except Exception as e:
    print(f"   ❌ Error counting: {e}")

print("\n" + "=" * 80)
print("💡 ANALYSIS:")
print("=" * 80)
print("""
If you see "No users visible" above but you successfully registered:

🔴 PROBLEM: The RLS SELECT policy is too restrictive!

The current policy only allows users to see their OWN data:
   USING (auth.uid() = id)

But when you run this script, there's no authenticated session,
so auth.uid() returns NULL and no rows are visible.

🔧 FIX NEEDED: Add an admin-accessible policy or adjust the existing one.

For now, your login should still work because the login function
uses an authenticated session from Supabase Auth.
""")

print("\n🎯 IMMEDIATE SOLUTION:")
print("=" * 80)
print("1. Go to: http://localhost:5000/logout")
print("2. Login again with: tonykondaveetijmj98@gmail.com")
print("3. Access: http://localhost:5000/admin/analytics")
print("\nThis should work because during login, the session is authenticated")
print("and your email will be stored in session['user_email']")
print("=" * 80)
