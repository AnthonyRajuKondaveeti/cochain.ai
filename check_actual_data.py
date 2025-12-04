"""
Check what data we actually have in the database
"""
from database.connection import supabase

print("=" * 80)
print("📊 CHECKING ACTUAL DATABASE DATA")
print("=" * 80)

tables_to_check = [
    ('users', 'Users'),
    ('user_profiles', 'User Profiles'),
    ('user_bookmarks', 'Bookmarks'),
    ('user_interactions', 'User Interactions'),
    ('user_queries', 'User Queries'),
    ('user_sessions', 'User Sessions'),
    ('recommendation_results', 'Recommendation Results'),
    ('github_references', 'GitHub Projects'),
    ('github_embeddings', 'GitHub Embeddings')
]

print("\n📋 DATA AVAILABLE:")
print("-" * 80)

for table_name, display_name in tables_to_check:
    try:
        result = supabase.table(table_name).select('*', count='exact').limit(0).execute()
        count = result.count if result.count is not None else 0
        status = "✅" if count > 0 else "❌"
        print(f"{status} {display_name:<30} {count:>6} records")
    except Exception as e:
        print(f"❌ {display_name:<30} ERROR: {str(e)[:40]}")

print("\n" + "=" * 80)
print("🎯 REINFORCEMENT LEARNING DATA NEEDED:")
print("=" * 80)
print("""
For Reinforcement Learning, we need to track:

1. ✅ USER INTERACTIONS (Rewards/Actions)
   - Click events (positive reward)
   - Bookmark events (strong positive reward)
   - Skip/ignore events (negative reward)
   - Time spent on project page (engagement metric)

2. ✅ RECOMMENDATION RESULTS (Actions taken)
   - Which projects were shown
   - Position in the list
   - Similarity score

3. ✅ USER QUERIES (Context/State)
   - User's search queries
   - User preferences
   - Project requirements

4. ✅ USER PROFILES (State features)
   - Skills, interests
   - Complexity preference
   - Learning goals

5. 📊 CLICK-THROUGH RATE (CTR) Metrics
   - Impressions (recommendations shown)
   - Clicks (user clicked on recommendation)
   - Position bias
   - Domain performance

""")

print("=" * 80)
print("🔧 WHAT TO KEEP IN ANALYTICS:")
print("=" * 80)
print("""
KEEP:
✅ Total Users (from users table)
✅ User Interactions (clicks, bookmarks from user_interactions)
✅ Click-Through Rate (from user_interactions + recommendation_results)
✅ Recommendation Performance (from recommendation_results)
✅ Top Projects (from user_interactions grouped by github_reference_id)
✅ Position Bias (CTR by position from user_interactions)
✅ Domain Performance (from github_references + user_interactions)

REMOVE (not tracking yet / not relevant):
❌ Daily Active Users (need to track user_sessions properly)
❌ Session Duration (not tracking in user_sessions)
❌ System Health metrics (CPU, Memory - not relevant for RL)
❌ API Performance metrics (not relevant for RL)
❌ Cache Hit Rate (not relevant for RL)
❌ Engagement Funnel (not tracking these stages)

""")
