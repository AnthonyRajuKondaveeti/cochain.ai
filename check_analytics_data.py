"""
Check all analytics data in Supabase
This script queries all relevant tables to verify data availability
"""
from database.connection import supabase
import json

def check_table_data(table_name, columns='*', limit=100):
    """Query a table and return data"""
    try:
        result = supabase.table(table_name).select(columns, count='exact').limit(limit).execute()
        return {
            'success': True,
            'count': result.count,
            'data': result.data if result.data else []
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

print("=" * 80)
print("SUPABASE DATABASE ANALYTICS DATA CHECK")
print("=" * 80)
print()

# 1. Check Users
print("1️⃣  USERS TABLE")
print("-" * 80)
users_result = check_table_data('users', 'id, email, full_name, created_at')
if users_result['success']:
    print(f"✅ Total users: {users_result['count']}")
    for user in users_result['data']:
        print(f"   - {user['email']} (ID: {user['id'][:8]}...)")
else:
    print(f"❌ Error: {users_result['error']}")
print()

# 2. Check User Bookmarks
print("2️⃣  USER_BOOKMARKS TABLE")
print("-" * 80)
bookmarks_result = check_table_data('user_bookmarks', 'id, user_id, github_reference_id, created_at')
if bookmarks_result['success']:
    print(f"✅ Total bookmarks: {bookmarks_result['count']}")
    
    # Group by user
    user_bookmark_counts = {}
    for bookmark in bookmarks_result['data']:
        user_id = bookmark['user_id']
        user_bookmark_counts[user_id] = user_bookmark_counts.get(user_id, 0) + 1
    
    print(f"   📊 Bookmarks by user:")
    for user_id, count in user_bookmark_counts.items():
        print(f"      User {user_id[:8]}...: {count} bookmarks")
else:
    print(f"❌ Error: {bookmarks_result['error']}")
print()

# 3. Check User Interactions
print("3️⃣  USER_INTERACTIONS TABLE")
print("-" * 80)
interactions_result = check_table_data('user_interactions', 'id, user_id, github_reference_id, interaction_type, created_at')
if interactions_result['success']:
    print(f"✅ Total interactions: {interactions_result['count']}")
    
    # Group by user and type
    user_interaction_counts = {}
    type_counts = {}
    for interaction in interactions_result['data']:
        user_id = interaction['user_id']
        int_type = interaction['interaction_type']
        
        if user_id not in user_interaction_counts:
            user_interaction_counts[user_id] = {}
        user_interaction_counts[user_id][int_type] = user_interaction_counts[user_id].get(int_type, 0) + 1
        type_counts[int_type] = type_counts.get(int_type, 0) + 1
    
    print(f"   📊 By interaction type:")
    for int_type, count in type_counts.items():
        print(f"      {int_type}: {count}")
    
    print(f"   📊 By user:")
    for user_id, types in user_interaction_counts.items():
        print(f"      User {user_id[:8]}...: {types}")
else:
    print(f"❌ Error: {interactions_result['error']}")
print()

# 4. Check Recommendation Results
print("4️⃣  RECOMMENDATION_RESULTS TABLE")
print("-" * 80)
recs_result = check_table_data('recommendation_results', 'id, github_reference_id, rank_position, similarity_score, created_at')
if recs_result['success']:
    print(f"✅ Total recommendation results: {recs_result['count']}")
    
    # Count by position
    position_counts = {}
    for rec in recs_result['data']:
        pos = rec['rank_position']
        position_counts[pos] = position_counts.get(pos, 0) + 1
    
    print(f"   📊 By rank position (top 5):")
    for pos in sorted(position_counts.keys())[:5]:
        print(f"      Position {pos}: {position_counts[pos]} recommendations")
else:
    print(f"❌ Error: {recs_result['error']}")
print()

# 5. Check User Queries
print("5️⃣  USER_QUERIES TABLE")
print("-" * 80)
queries_result = check_table_data('user_queries', 'id, user_id, created_at')
if queries_result['success']:
    print(f"✅ Total user queries: {queries_result['count']}")
    
    # Group by user
    user_query_counts = {}
    for query in queries_result['data']:
        user_id = query['user_id']
        if user_id:
            user_query_counts[user_id] = user_query_counts.get(user_id, 0) + 1
    
    print(f"   📊 Queries by user:")
    for user_id, count in user_query_counts.items():
        print(f"      User {user_id[:8]}...: {count} queries")
else:
    print(f"❌ Error: {queries_result['error']}")
print()

# 6. Check User Sessions
print("6️⃣  USER_SESSIONS TABLE")
print("-" * 80)
sessions_result = check_table_data('user_sessions', 'id, user_id, session_id, login_time, logout_time')
if sessions_result['success']:
    print(f"✅ Total user sessions: {sessions_result['count']}")
    
    # Group by user
    user_session_counts = {}
    for session in sessions_result['data']:
        user_id = session['user_id']
        user_session_counts[user_id] = user_session_counts.get(user_id, 0) + 1
    
    print(f"   📊 Sessions by user:")
    for user_id, count in user_session_counts.items():
        print(f"      User {user_id[:8]}...: {count} sessions")
else:
    print(f"❌ Error: {sessions_result['error']}")
print()

# 7. Check GitHub References
print("7️⃣  GITHUB_REFERENCES TABLE")
print("-" * 80)
github_result = check_table_data('github_references', 'id, title, domain', limit=10)
if github_result['success']:
    print(f"✅ Total GitHub projects: {github_result['count']}")
else:
    print(f"❌ Error: {github_result['error']}")
print()

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"✅ Users: {users_result.get('count', 0)}")
print(f"✅ Bookmarks: {bookmarks_result.get('count', 0)}")
print(f"✅ Interactions: {interactions_result.get('count', 0)}")
print(f"✅ Recommendation Results: {recs_result.get('count', 0)}")
print(f"✅ User Queries: {queries_result.get('count', 0)}")
print(f"✅ User Sessions: {sessions_result.get('count', 0)}")
print(f"✅ GitHub Projects: {github_result.get('count', 0)}")
print()

# Check for issues
print("=" * 80)
print("POTENTIAL ISSUES")
print("=" * 80)

if users_result.get('count', 0) > 1 and bookmarks_result.get('count', 0) > 0:
    # Check if bookmarks are from multiple users
    unique_bookmark_users = len(user_bookmark_counts) if bookmarks_result['success'] else 0
    if unique_bookmark_users == 1:
        print("⚠️  WARNING: All bookmarks are from only 1 user!")
        print(f"   Expected: {users_result.get('count', 0)} users")
        print(f"   Found: {unique_bookmark_users} user with bookmarks")
    else:
        print(f"✅ Bookmarks from {unique_bookmark_users} different users")
else:
    print("ℹ️  Only 1 user in system or no bookmarks yet")

if interactions_result.get('count', 0) > 0:
    unique_interaction_users = len(user_interaction_counts) if interactions_result['success'] else 0
    if unique_interaction_users == 1 and users_result.get('count', 0) > 1:
        print("⚠️  WARNING: All interactions are from only 1 user!")
        print(f"   Expected: {users_result.get('count', 0)} users")
        print(f"   Found: {unique_interaction_users} user with interactions")
    else:
        print(f"✅ Interactions from {unique_interaction_users} different users")
else:
    print("ℹ️  No interactions recorded yet")

print()
print("=" * 80)
print("ANALYTICS QUERY TEST")
print("=" * 80)

# Simulate the analytics query
try:
    # Count clicks
    clicks = supabase.table('user_interactions').select('id', count='exact').eq('interaction_type', 'click').execute()
    click_count = clicks.count or 0
    
    # Count bookmark interactions
    bookmark_adds = supabase.table('user_interactions').select('id', count='exact').eq('interaction_type', 'bookmark_add').execute()
    bookmark_add_count = bookmark_adds.count or 0
    
    bookmark_removes = supabase.table('user_interactions').select('id', count='exact').eq('interaction_type', 'bookmark_remove').execute()
    bookmark_remove_count = bookmark_removes.count or 0
    
    total_recs = recs_result.get('count', 0)
    ctr = (click_count / total_recs * 100) if total_recs > 0 else 0
    
    print(f"📊 Analytics Metrics:")
    print(f"   Total Recommendations: {total_recs}")
    print(f"   Total Clicks: {click_count}")
    print(f"   Total Bookmark Adds: {bookmark_add_count}")
    print(f"   Total Bookmark Removes: {bookmark_remove_count}")
    print(f"   Click-Through Rate (CTR): {ctr:.2f}%")
    
except Exception as e:
    print(f"❌ Error running analytics query: {str(e)}")

print()
