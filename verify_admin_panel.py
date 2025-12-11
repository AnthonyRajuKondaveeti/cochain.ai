from database.connection import supabase_admin
from datetime import datetime, timedelta

print("=" * 60)
print("Admin Panel Data Verification")
print("=" * 60)

# 1. Check what the admin panel receives
print("\n📊 ADMIN PANEL USER LIST DATA")
print("-" * 60)

# This mimics what /api/admin/analytics/users endpoint returns
users_response = supabase_admin.table('user_engagement_summary').select('*').execute()

print(f"Total users: {len(users_response.data)}\n")

for user in users_response.data:
    print(f"Email: {user.get('email')}")
    print(f"   Name: {user.get('full_name', 'N/A')}")
    print(f"   Total Sessions: {user.get('total_sessions', 0)}")
    print(f"   Time on Platform: {user.get('total_minutes_on_platform', 0)} minutes")
    print(f"   GitHub Views: {user.get('github_views', 0)}")
    print(f"   GitHub Clicks: {user.get('github_clicks', 0)}")
    print(f"   Projects Created: {user.get('projects_created', 0)}")
    print(f"   Projects Joined: {user.get('projects_joined', 0)}")
    print()

# 2. Check summary statistics
print("\n📈 SUMMARY STATISTICS (Dashboard)")
print("-" * 60)

# Total users
total_users = len(users_response.data)
print(f"Total Users: {total_users}")

# Active users (last 24h, 7d, 30d)
now = datetime.now()
yesterday = (now - timedelta(days=1)).isoformat()
week_ago = (now - timedelta(days=7)).isoformat()
month_ago = (now - timedelta(days=30)).isoformat()

active_24h = supabase_admin.table('user_sessions').select('user_id', count='exact').gte('last_activity', yesterday).execute()
active_7d = supabase_admin.table('user_sessions').select('user_id', count='exact').gte('last_activity', week_ago).execute()
active_30d = supabase_admin.table('user_sessions').select('user_id', count='exact').gte('last_activity', month_ago).execute()

unique_24h = len(set([s['user_id'] for s in active_24h.data]))
unique_7d = len(set([s['user_id'] for s in active_7d.data]))
unique_30d = len(set([s['user_id'] for s in active_30d.data]))

print(f"Active Users (24h): {unique_24h}")
print(f"Active Users (7d): {unique_7d}")
print(f"Active Users (30d): {unique_30d}")

# New users (last 7d)
seven_days_ago = (now - timedelta(days=7)).isoformat()
new_users = supabase_admin.table('users').select('id', count='exact').gte('created_at', seven_days_ago).execute()
print(f"New Users (7d): {new_users.count}")

# Total interactions
all_interactions = supabase_admin.table('user_interactions').select('*', count='exact').execute()
print(f"Total Interactions: {all_interactions.count}")

# Total clicks
total_clicks = supabase_admin.table('user_interactions').select('*', count='exact').eq('interaction_type', 'click').execute()
print(f"Total Clicks: {total_clicks.count}")

# Click-through rate
all_sessions = supabase_admin.table('user_sessions').select('*').execute()
total_views = sum([s.get('github_recommendations_viewed', 0) or 0 for s in all_sessions.data])
ctr = (total_clicks.count / total_views * 100) if total_views > 0 else 0
print(f"Click-Through Rate: {ctr:.2f}%")

# Average session duration
total_minutes = sum([s.get('total_minutes', 0) or 0 for s in all_sessions.data])
avg_duration = total_minutes / len(all_sessions.data) if all_sessions.data else 0
print(f"Average Session Duration: {avg_duration:.1f} minutes")

# 3. Check if tracking is working properly
print("\n✅ TRACKING STATUS")
print("-" * 60)

issues = []

# Check if clicks are being recorded
if total_clicks.count == 0:
    issues.append("⚠️  No clicks recorded - click tracking may not be working")
else:
    print(f"✅ Clicks are being tracked ({total_clicks.count} total)")

# Check if time is being tracked
if total_minutes == 0:
    issues.append("⚠️  No session time recorded - duration tracking may not be working")
else:
    print(f"✅ Session time is being tracked ({total_minutes} minutes total)")

# Check if page views are being tracked
total_page_views = sum([s.get('pages_visited', 0) or 0 for s in all_sessions.data])
if total_page_views == 0:
    issues.append("⚠️  No page views recorded - page view tracking may not be working")
else:
    print(f"✅ Page views are being tracked ({total_page_views} total)")

# Check if GitHub views are being tracked
if total_views == 0:
    issues.append("⚠️  No GitHub views recorded - recommendation viewing may not be working")
else:
    print(f"✅ GitHub recommendation views are being tracked ({total_views} total)")

# Check if view aggregation is correct
if issues:
    print("\nIssues found:")
    for issue in issues:
        print(f"   {issue}")
else:
    print("\n🎉 All tracking mechanisms are working correctly!")

print("\n" + "=" * 60)
print("Verification Complete!")
print("=" * 60)
