from database.connection import supabase_admin

print("=" * 60)
print("Raw Data Check for benisonjac@gmail.com")
print("=" * 60)

# Get user ID
user = supabase_admin.table('users').select('*').eq('email', 'benisonjac@gmail.com').execute()
if not user.data:
    print("User not found!")
    exit()

user_id = user.data[0]['id']
print(f"\nUser ID: {user_id}")
print(f"Name: {user.data[0].get('full_name', 'N/A')}")

# Check all sessions for this user
print("\n" + "=" * 60)
print("ALL SESSIONS")
print("=" * 60)
sessions = supabase_admin.table('user_sessions').select('*').eq('user_id', user_id).execute()
print(f"Total sessions: {len(sessions.data)}\n")

total_minutes = 0
total_github_views = 0
total_github_clicks = 0
total_pages = 0

for i, session in enumerate(sessions.data, 1):
    minutes = session.get('total_minutes', 0) or 0
    views = session.get('github_recommendations_viewed', 0) or 0
    clicks = session.get('github_projects_clicked', 0) or 0
    pages = session.get('pages_visited', 0) or 0
    
    total_minutes += minutes
    total_github_views += views
    total_github_clicks += clicks
    total_pages += pages
    
    print(f"Session {i}:")
    print(f"   ID: {session['id']}")
    print(f"   Login: {session.get('login_time', 'N/A')}")
    print(f"   Last Activity: {session.get('last_activity', 'N/A')}")
    print(f"   Duration: {minutes} minutes")
    print(f"   GitHub Views: {views}")
    print(f"   GitHub Clicks: {clicks}")
    print(f"   Pages Visited: {pages}")
    print()

print("=" * 60)
print("SESSION TOTALS")
print("=" * 60)
print(f"Total Duration: {total_minutes} minutes")
print(f"Total GitHub Views: {total_github_views}")
print(f"Total GitHub Clicks (from sessions): {total_github_clicks}")
print(f"Total Pages Visited: {total_pages}")

# Check user_interactions for clicks
print("\n" + "=" * 60)
print("USER INTERACTIONS (CLICKS)")
print("=" * 60)
interactions = supabase_admin.table('user_interactions').select('*').eq('user_id', user_id).eq('interaction_type', 'click').execute()
print(f"Total clicks in user_interactions: {len(interactions.data)}\n")

for i, interaction in enumerate(interactions.data, 1):
    print(f"Click {i}:")
    print(f"   Time: {interaction.get('interaction_time', 'N/A')}")
    print(f"   Result ID: {interaction.get('result_id', 'N/A')}")
    print(f"   Session ID: {interaction.get('session_id', 'N/A')}")
    print()

# Check user_interactions for views
print("=" * 60)
print("USER INTERACTIONS (VIEWS)")
print("=" * 60)
view_interactions = supabase_admin.table('user_interactions').select('*').eq('user_id', user_id).eq('interaction_type', 'view').execute()
print(f"Total views in user_interactions: {len(view_interactions.data)}\n")

for i, interaction in enumerate(view_interactions.data, 1):
    print(f"View {i}:")
    print(f"   Time: {interaction.get('interaction_time', 'N/A')}")
    print(f"   Result ID: {interaction.get('result_id', 'N/A')}")
    print(f"   Session ID: {interaction.get('session_id', 'N/A')}")
    print()

print("=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Sessions Table:")
print(f"   Total Clicks: {total_github_clicks}")
print(f"   Total Views: {total_github_views}")
print(f"\nUser Interactions Table:")
print(f"   Total Clicks: {len(interactions.data)}")
print(f"   Total Views: {len(view_interactions.data)}")
print(f"\n⚠️  Discrepancy:")
print(f"   Click difference: {len(interactions.data) - total_github_clicks}")
print(f"   View difference: {len(view_interactions.data) - total_github_views}")
