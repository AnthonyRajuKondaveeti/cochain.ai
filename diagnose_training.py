"""
Check why RL training has no effect
Diagnoses data availability and training process
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import supabase, supabase_admin
from datetime import datetime, timedelta

print("=" * 70)
print("RL TRAINING DIAGNOSIS")
print("=" * 70)

# Check 1: User Interactions
print("\n1. USER INTERACTIONS DATA:")
print("-" * 70)
try:
    interactions = supabase_admin.table('user_interactions').select('*', count='exact').execute()
    print(f"✅ Total interactions: {interactions.count or 0}")
    
    if interactions.data:
        print(f"\nRecent interactions:")
        for i, interaction in enumerate(interactions.data[:5], 1):
            print(f"  {i}. Type: {interaction.get('interaction_type')}, "
                  f"User: {interaction.get('user_id')}, "
                  f"Project: {interaction.get('github_reference_id')}, "
                  f"Time: {interaction.get('interaction_time')}")
    else:
        print("⚠️  NO INTERACTIONS FOUND - This is why training has no effect!")
        print("   The RL system needs user interactions to learn from.")
except Exception as e:
    print(f"❌ Error checking interactions: {str(e)}")

# Check 2: Recommendation Results
print("\n2. RECOMMENDATION RESULTS:")
print("-" * 70)
try:
    recs = supabase_admin.table('recommendation_results').select('*', count='exact').execute()
    print(f"✅ Total recommendation results: {recs.count or 0}")
    
    if recs.count == 0:
        print("⚠️  No recommendations tracked - RL needs this for CTR calculation")
except Exception as e:
    print(f"❌ Error checking recommendations: {str(e)}")

# Check 3: Training History
print("\n3. TRAINING HISTORY:")
print("-" * 70)
try:
    training = supabase_admin.table('rl_training_history')\
        .select('*')\
        .order('training_date', desc=True)\
        .limit(5)\
        .execute()
    
    print(f"✅ Training records: {len(training.data) if training.data else 0}")
    
    if training.data:
        print("\nRecent training runs:")
        for i, record in enumerate(training.data, 1):
            print(f"  {i}. Date: {record.get('training_date')}, "
                  f"Pre-reward: {record.get('pre_avg_reward', 0):.2f}, "
                  f"Post-reward: {record.get('post_avg_reward', 0):.2f}, "
                  f"Improvement: {record.get('reward_improvement', 0):.2f}%")
    else:
        print("⚠️  No training history found")
        print("   This means training hasn't saved results to the database")
except Exception as e:
    print(f"❌ Error checking training history: {str(e)}")

# Check 4: User Sessions
print("\n4. USER SESSIONS:")
print("-" * 70)
try:
    sessions = supabase_admin.table('user_sessions').select('*', count='exact').execute()
    print(f"✅ Total sessions: {sessions.count or 0}")
    
    if sessions.data:
        active_sessions = [s for s in sessions.data if s.get('github_projects_clicked', 0) > 0]
        print(f"   Sessions with clicks: {len(active_sessions)}")
except Exception as e:
    print(f"❌ Error checking sessions: {str(e)}")

# Check 5: GitHub References
print("\n5. GITHUB REFERENCES (Projects):")
print("-" * 70)
try:
    projects = supabase_admin.table('github_references').select('id, title', count='exact').limit(5).execute()
    print(f"✅ Total projects: {projects.count or 0}")
    
    if projects.data:
        print("\nSample projects:")
        for i, proj in enumerate(projects.data, 1):
            print(f"  {i}. {proj.get('title', 'N/A')[:60]}")
except Exception as e:
    print(f"❌ Error checking projects: {str(e)}")

# Check 6: Users
print("\n6. USERS:")
print("-" * 70)
try:
    users = supabase_admin.table('users').select('id, email', count='exact').execute()
    print(f"✅ Total users: {users.count or 0}")
    
    if users.data:
        print(f"\nSample users:")
        for i, user in enumerate(users.data[:3], 1):
            print(f"  {i}. {user.get('email', 'N/A')}")
except Exception as e:
    print(f"❌ Error checking users: {str(e)}")

# Diagnosis
print("\n" + "=" * 70)
print("DIAGNOSIS:")
print("=" * 70)

try:
    interactions_count = supabase_admin.table('user_interactions').select('*', count='exact').execute().count or 0
    recs_count = supabase_admin.table('recommendation_results').select('*', count='exact').execute().count or 0
    training_count = len(supabase_admin.table('rl_training_history').select('*').limit(1).execute().data or [])
    
    if interactions_count == 0:
        print("❌ PROBLEM: No user interactions to train on")
        print("\n   Why training had 0 reward:")
        print("   - RL system needs user clicks, views, bookmarks to learn")
        print("   - Currently: 0 interactions in database")
        print("   - Training processed 0 interactions = 0 reward")
        print("\n   SOLUTION:")
        print("   1. Use the platform and click on recommended projects")
        print("   2. Generate some test interactions (run script below)")
        print("   3. Wait for users to interact naturally")
        print("\n   Would you like to create test interactions? (y/n)")
    
    elif recs_count == 0:
        print("⚠️  WARNING: No recommendation results tracked")
        print("   CTR cannot be calculated without recommendation tracking")
    
    elif training_count == 0:
        print("⚠️  WARNING: Training runs but doesn't save to rl_training_history")
        print("   Graphs won't show data without training history records")
    
    else:
        print("✅ Data looks good! Training should work.")
        print(f"   - {interactions_count} interactions available")
        print(f"   - {recs_count} recommendations tracked")
        print(f"   - {training_count} training records saved")

except Exception as e:
    print(f"❌ Error in diagnosis: {str(e)}")

print("\n" + "=" * 70)
print("NEXT STEPS:")
print("=" * 70)
print("1. Generate interactions by using the platform normally")
print("2. Click 'View Project' buttons on recommendations")
print("3. After 5-10 interactions, trigger training again")
print("4. Training will then have data to process")
print("5. Graphs will populate with training history")
print("=" * 70)
