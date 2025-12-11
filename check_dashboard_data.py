"""
Test RL Dashboard Data - Check what the dashboard will display
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import supabase
from datetime import datetime, timedelta

print("=" * 70)
print("RL DASHBOARD DATA CHECK")
print("=" * 70)

# Check USE_RL_RECOMMENDATIONS in app.py
print("\n1. CHECKING APP CONFIGURATION")
print("-" * 70)

try:
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
        if 'USE_RL_RECOMMENDATIONS = True' in content:
            print("✅ USE_RL_RECOMMENDATIONS = True (RL ENABLED)")
        elif 'USE_RL_RECOMMENDATIONS = False' in content:
            print("❌ USE_RL_RECOMMENDATIONS = False (RL DISABLED)")
        else:
            print("⚠️  USE_RL_RECOMMENDATIONS not found in app.py")
except Exception as e:
    print(f"❌ Error reading app.py: {e}")

# Check for interactions in last 7 days
print("\n2. CHECKING INTERACTION DATA (Last 7 days)")
print("-" * 70)

try:
    since_date = (datetime.now() - timedelta(days=7)).isoformat()
    
    interactions = supabase.table('user_interactions')\
        .select('*')\
        .gte('interaction_time', since_date)\
        .execute()
    
    total = len(interactions.data) if interactions.data else 0
    print(f"Total interactions: {total}")
    
    if total > 0:
        # Count by type
        click_count = sum(1 for i in interactions.data if i.get('interaction_type') == 'click')
        view_count = sum(1 for i in interactions.data if i.get('interaction_type') == 'view')
        bookmark_count = sum(1 for i in interactions.data if i.get('interaction_type') == 'bookmark')
        
        print(f"  - Clicks: {click_count}")
        print(f"  - Views: {view_count}")
        print(f"  - Bookmarks: {bookmark_count}")
        
        # Calculate rewards
        total_reward = (click_count * 5.0) + (view_count * 1.0) + (bookmark_count * 10.0)
        avg_reward = total_reward / total
        positive_count = click_count + bookmark_count + (view_count if view_count > 0 else 0)
        positive_rate = (positive_count / total) * 100
        
        print(f"\nCalculated Metrics:")
        print(f"  - Total Reward: {total_reward:.2f}")
        print(f"  - Avg Reward: {avg_reward:.2f}")
        print(f"  - Positive Rate: {positive_rate:.1f}%")
    else:
        print("⚠️  No interactions found - Dashboard will show zeros (cold start)")

except Exception as e:
    print(f"❌ Error checking interactions: {e}")

# Check for top projects
print("\n3. CHECKING TOP PROJECTS")
print("-" * 70)

try:
    if total > 0 and interactions.data:
        # Count interactions per project
        project_stats = {}
        for interaction in interactions.data:
            project_id = interaction.get('github_reference_id')
            if project_id:
                if project_id not in project_stats:
                    project_stats[project_id] = {'clicks': 0, 'views': 0, 'total': 0}
                
                project_stats[project_id]['total'] += 1
                interaction_type = interaction.get('interaction_type', 'view')
                if interaction_type == 'click':
                    project_stats[project_id]['clicks'] += 1
                elif interaction_type == 'view':
                    project_stats[project_id]['views'] += 1
        
        # Sort by clicks and total
        sorted_projects = sorted(
            project_stats.items(),
            key=lambda x: (x[1]['clicks'], x[1]['total']),
            reverse=True
        )[:5]
        
        print(f"Top {len(sorted_projects)} Projects:")
        for idx, (project_id, stats) in enumerate(sorted_projects, 1):
            # Get project name
            project_result = supabase.table('github_references')\
                .select('title')\
                .eq('id', project_id)\
                .execute()
            
            title = project_result.data[0]['title'][:50] if project_result.data else 'Unknown'
            success_rate = (stats['clicks'] / max(stats['total'], 1)) * 100
            
            print(f"\n  {idx}. {title}")
            print(f"     - Total interactions: {stats['total']}")
            print(f"     - Clicks: {stats['clicks']}")
            print(f"     - Success rate: {success_rate:.1f}%")
    else:
        print("⚠️  No interaction data - Top projects will be empty")

except Exception as e:
    print(f"❌ Error checking top projects: {e}")

# Check training history
print("\n4. CHECKING TRAINING HISTORY")
print("-" * 70)

try:
    training = supabase.table('rl_training_history')\
        .select('*')\
        .order('training_date', desc=True)\
        .limit(5)\
        .execute()
    
    if training.data:
        print(f"Found {len(training.data)} training records:")
        for record in training.data:
            date = record.get('training_date', 'N/A')
            pre_reward = record.get('pre_avg_reward', 0)
            post_reward = record.get('post_avg_reward', 0)
            improvement = record.get('reward_improvement', 0)
            
            print(f"  - {date}: Pre={pre_reward:.2f}, Post={post_reward:.2f}, Improvement={improvement:+.2f}%")
    else:
        print("⚠️  No training history - Will show 'No training history available'")

except Exception as e:
    print(f"❌ Error checking training history: {e}")

# Recommendation results (for CTR calculation)
print("\n5. CHECKING RECOMMENDATION RESULTS")
print("-" * 70)

try:
    recs = supabase.table('recommendation_results')\
        .select('*', count='exact')\
        .gte('created_at', since_date)\
        .execute()
    
    rec_count = recs.count or 0
    print(f"Recommendations shown (last 7 days): {rec_count}")
    
    if rec_count > 0 and total > 0:
        ctr = (click_count / rec_count) * 100 if 'click_count' in locals() else 0
        print(f"Click-Through Rate: {ctr:.2f}%")
    else:
        print("⚠️  Not enough data to calculate CTR")

except Exception as e:
    print(f"❌ Error checking recommendations: {e}")

print("\n" + "=" * 70)
print("DASHBOARD PREVIEW")
print("=" * 70)

print("\nWhat the dashboard will show:")
print(f"✅ RL Status: {'ENABLED' if 'True' in content else 'DISABLED'}")
print(f"✅ Average Reward: {avg_reward:.2f}" if total > 0 else "⚠️  Average Reward: 0.00 (no data)")
print(f"✅ Positive Rate: {positive_rate:.1f}%" if total > 0 else "⚠️  Positive Rate: 0.0% (no data)")
print(f"✅ Training Examples: {total}")
print(f"✅ Top Projects: {len(sorted_projects)}" if total > 0 else "⚠️  Top Projects: 0 (no data)")
print(f"✅ Training History: {len(training.data) if training.data else 0} records")

if total == 0:
    print("\n" + "!" * 70)
    print("COLD START DETECTED")
    print("!" * 70)
    print("\nThe dashboard will show zeros because there's no interaction data yet.")
    print("This is normal for a new system. Data will populate as users:")
    print("  1. View recommendations")
    print("  2. Click on projects")
    print("  3. Bookmark projects")
    print("  4. Rate projects")
    print("\nThe RL system is ready and will start learning from these interactions!")

print("\n" + "=" * 70)
