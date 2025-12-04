"""
Check if clicks are being tracked properly
"""
from database.connection import supabase_admin

print("=" * 60)
print("Checking Click Tracking")
print("=" * 60)

# Check user_interactions for clicks
print("\n1. Checking user_interactions table for clicks...")
try:
    clicks = supabase_admin.table('user_interactions')\
        .select('user_id, interaction_type, interaction_time')\
        .eq('interaction_type', 'click')\
        .execute()
    
    print(f"   Total clicks in user_interactions: {len(clicks.data) if clicks.data else 0}")
    
    if clicks.data:
        # Count by user
        user_clicks = {}
        for click in clicks.data:
            user_id = click.get('user_id', 'unknown')
            user_clicks[user_id] = user_clicks.get(user_id, 0) + 1
        
        print(f"   Clicks per user:")
        for user_id, count in user_clicks.items():
            print(f"      - {user_id[:8]}...: {count} clicks")
    else:
        print(f"   No clicks found in user_interactions table")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Check user_sessions for github_projects_clicked
print("\n2. Checking user_sessions for github_projects_clicked...")
try:
    sessions = supabase_admin.table('user_sessions')\
        .select('user_id, github_projects_clicked')\
        .execute()
    
    print(f"   Total sessions: {len(sessions.data) if sessions.data else 0}")
    
    if sessions.data:
        # Sum clicks per user
        user_clicks = {}
        for session in sessions.data:
            user_id = session.get('user_id')
            clicks = session.get('github_projects_clicked', 0)
            if user_id:
                user_clicks[user_id] = user_clicks.get(user_id, 0) + clicks
        
        print(f"   GitHub clicks per user (from sessions):")
        for user_id, count in user_clicks.items():
            if count > 0:
                print(f"      - {user_id[:8]}...: {count} clicks")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Check user_engagement_summary view
print("\n3. Checking user_engagement_summary view...")
try:
    summary = supabase_admin.table('user_engagement_summary')\
        .select('user_id, email, github_clicks')\
        .execute()
    
    print(f"   Total users in summary: {len(summary.data) if summary.data else 0}")
    
    if summary.data:
        print(f"   GitHub clicks per user (from summary view):")
        for user in summary.data:
            email = user.get('email', 'N/A')
            clicks = user.get('github_clicks', 0)
            print(f"      - {email}: {clicks} clicks")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("Check Complete!")
print("=" * 60)
