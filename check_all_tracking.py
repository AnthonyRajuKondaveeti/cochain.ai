from database.connection import supabase_admin
from datetime import datetime, timedelta

print("=" * 60)
print("Comprehensive Tracking Diagnostics")
print("=" * 60)

# 1. Check clicks tracking
print("\n📊 1. CLICK TRACKING")
print("-" * 60)
clicks_response = supabase_admin.table('user_interactions').select('*').eq('interaction_type', 'click').execute()
total_clicks = len(clicks_response.data)
print(f"   Total clicks in user_interactions: {total_clicks}")

if total_clicks > 0:
    # Group by user
    clicks_by_user = {}
    for click in clicks_response.data:
        user_id = click.get('user_id', 'unknown')
        clicks_by_user[user_id] = clicks_by_user.get(user_id, 0) + 1
    
    print(f"   Clicks per user:")
    for user_id, count in clicks_by_user.items():
        print(f"      - {user_id[:8]}...: {count} clicks")

# 2. Check session tracking
print("\n⏱️  2. SESSION TRACKING")
print("-" * 60)
sessions_response = supabase_admin.table('user_sessions').select('*').execute()
total_sessions = len(sessions_response.data)
print(f"   Total sessions: {total_sessions}")

if total_sessions > 0:
    total_time = 0
    sessions_by_user = {}
    time_by_user = {}
    
    for session in sessions_response.data:
        user_id = session.get('user_id', 'unknown')
        duration = session.get('total_minutes', 0) or 0
        
        sessions_by_user[user_id] = sessions_by_user.get(user_id, 0) + 1
        time_by_user[user_id] = time_by_user.get(user_id, 0) + duration
        total_time += duration
    
    print(f"   Total time on platform: {total_time} minutes ({total_time/60:.1f} hours)")
    print(f"\n   Sessions per user:")
    for user_id, count in sessions_by_user.items():
        time = time_by_user.get(user_id, 0)
        print(f"      - {user_id[:8]}...: {count} sessions, {time} minutes ({time/60:.1f} hours)")

# 3. Check page views tracking
print("\n📄 3. PAGE VIEWS TRACKING")
print("-" * 60)
page_views = {}
pages_visited_count = {}

for session in sessions_response.data:
    user_id = session.get('user_id', 'unknown')
    pages = session.get('pages_visited', 0) or 0
    pages_visited_count[user_id] = pages_visited_count.get(user_id, 0) + pages

total_pages = sum(pages_visited_count.values())
print(f"   Total page views: {total_pages}")
print(f"   Page views per user:")
for user_id, count in pages_visited_count.items():
    print(f"      - {user_id[:8]}...: {count} pages")

# 4. Check GitHub recommendations viewed
print("\n🔍 4. GITHUB RECOMMENDATIONS VIEWED")
print("-" * 60)
github_views = {}

for session in sessions_response.data:
    user_id = session.get('user_id', 'unknown')
    views = session.get('github_recommendations_viewed', 0) or 0
    github_views[user_id] = github_views.get(user_id, 0) + views

total_github_views = sum(github_views.values())
print(f"   Total GitHub recommendations viewed: {total_github_views}")
print(f"   Views per user:")
for user_id, count in github_views.items():
    if count > 0:
        print(f"      - {user_id[:8]}...: {count} views")

# 5. Check active users
print("\n👥 5. ACTIVE USERS (Last 24 hours)")
print("-" * 60)
yesterday = (datetime.now() - timedelta(days=1)).isoformat()
active_sessions = supabase_admin.table('user_sessions').select('user_id, last_activity').gte('last_activity', yesterday).execute()
active_users = set([s['user_id'] for s in active_sessions.data])
print(f"   Active users in last 24h: {len(active_users)}")

# 6. Check user_engagement_summary view
print("\n📈 6. USER ENGAGEMENT SUMMARY VIEW")
print("-" * 60)
summary_response = supabase_admin.table('user_engagement_summary').select('*').execute()
print(f"   Total users in summary: {len(summary_response.data)}")

if summary_response.data:
    print(f"\n   Detailed metrics per user:")
    for user in summary_response.data:
        email = user.get('email', 'unknown')
        sessions = user.get('total_sessions', 0)
        time = user.get('total_minutes_on_platform', 0)
        clicks = user.get('github_clicks', 0)
        views = user.get('github_views', 0)
        projects = user.get('projects_created', 0)
        
        print(f"\n   {email}")
        print(f"      Sessions: {sessions}")
        print(f"      Time: {time} minutes ({time/60:.1f} hours)")
        print(f"      GitHub views: {views}")
        print(f"      GitHub clicks: {clicks}")
        print(f"      Projects created: {projects}")

# 7. Check for discrepancies
print("\n⚠️  7. DISCREPANCY CHECK")
print("-" * 60)

# Compare clicks in user_interactions vs user_engagement_summary
summary_clicks = {user['user_id']: user.get('github_clicks', 0) for user in summary_response.data}
interactions_clicks = {}

for click in clicks_response.data:
    user_id = click.get('user_id')
    interactions_clicks[user_id] = interactions_clicks.get(user_id, 0) + 1

print("   Comparing clicks between tables:")
all_users = set(list(summary_clicks.keys()) + list(interactions_clicks.keys()))
discrepancies = False

for user_id in all_users:
    summary_count = summary_clicks.get(user_id, 0)
    interactions_count = interactions_clicks.get(user_id, 0)
    
    if summary_count != interactions_count:
        discrepancies = True
        print(f"   ⚠️  User {user_id[:8]}...: Summary={summary_count}, Interactions={interactions_count}")

if not discrepancies:
    print("   ✅ All click counts match between tables!")

print("\n" + "=" * 60)
print("Diagnostics Complete!")
print("=" * 60)
