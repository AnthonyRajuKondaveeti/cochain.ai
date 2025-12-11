from database.connection import supabase
import sys

print("=" * 60)
print("CHECKING ADMIN ACCESS AND DATA STORAGE")
print("=" * 60)

# 1. Check users in database
print("\n1. CHECKING USERS IN DATABASE:")
print("-" * 60)
try:
    result = supabase.table('users').select('id,email,full_name,created_at').execute()
    print(f"✅ Total users in database: {len(result.data)}")
    if result.data:
        print("\nUsers found:")
        for user in result.data[:10]:
            print(f"  - Email: {user['email']}")
            print(f"    ID: {user['id']}")
            print(f"    Name: {user.get('full_name', 'N/A')}")
            print()
    else:
        print("⚠️  No users found in database!")
except Exception as e:
    print(f"❌ Error checking users: {e}")

# 2. Check user profiles
print("\n2. CHECKING USER PROFILES:")
print("-" * 60)
try:
    result = supabase.table('user_profiles').select('user_id,areas_of_interest,profile_completed').execute()
    print(f"✅ Total profiles: {len(result.data)}")
    if result.data:
        print("\nProfiles found:")
        for profile in result.data[:5]:
            print(f"  - User ID: {profile['user_id']}")
            print(f"    Completed: {profile.get('profile_completed', False)}")
            print(f"    Interests: {profile.get('areas_of_interest', [])}")
            print()
    else:
        print("⚠️  No user profiles found!")
except Exception as e:
    print(f"❌ Error checking profiles: {e}")

# 3. Check admin emails in code
print("\n3. CHECKING ADMIN CONFIGURATION:")
print("-" * 60)
from app import ADMIN_EMAILS
print(f"Admin emails configured: {ADMIN_EMAILS}")

# 4. Check if current session user is admin
print("\n4. CHECKING CURRENT USER SESSION:")
print("-" * 60)
# This will show if there's an active session
try:
    user = supabase.auth.get_user()
    if user:
        print(f"✅ Authenticated user: {user.user.email if hasattr(user, 'user') else 'Unknown'}")
        is_admin = user.user.email in ADMIN_EMAILS if hasattr(user, 'user') else False
        print(f"Is Admin: {is_admin}")
    else:
        print("⚠️  No active session (this is expected when running from command line)")
except Exception as e:
    print(f"⚠️  No active session: {e}")

# 5. Check user interactions (analytics data)
print("\n5. CHECKING ANALYTICS DATA:")
print("-" * 60)
try:
    # User interactions
    result = supabase.table('user_interactions').select('count', count='exact').execute()
    print(f"✅ User interactions: {result.count}")
    
    # User queries
    result = supabase.table('user_queries').select('count', count='exact').execute()
    print(f"✅ User queries: {result.count}")
    
    # User bookmarks
    result = supabase.table('user_bookmarks').select('count', count='exact').execute()
    print(f"✅ User bookmarks: {result.count}")
    
    # User sessions
    result = supabase.table('user_sessions').select('count', count='exact').execute()
    print(f"✅ User sessions: {result.count}")
    
except Exception as e:
    print(f"❌ Error checking analytics data: {e}")

# 6. Check github references
print("\n6. CHECKING GITHUB DATA:")
print("-" * 60)
try:
    result = supabase.table('github_references').select('count', count='exact').execute()
    print(f"✅ GitHub references: {result.count}")
    
    result = supabase.table('github_embeddings').select('count', count='exact').execute()
    print(f"✅ GitHub embeddings: {result.count}")
except Exception as e:
    print(f"❌ Error checking GitHub data: {e}")

print("\n" + "=" * 60)
print("CHECK COMPLETE")
print("=" * 60)
