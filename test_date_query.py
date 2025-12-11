"""
Test date query to understand why training finds no interactions
"""

from datetime import datetime, timedelta
from database.connection import supabase_admin

supabase = supabase_admin

# Test different time ranges
days_to_test = [1, 7, 30, 90, 365]

print("=" * 70)
print("DATE QUERY TEST")
print("=" * 70)
print(f"\nCurrent time: {datetime.now()}")
print()

for days in days_to_test:
    since_date = (datetime.now() - timedelta(days=days)).isoformat()
    
    interactions = supabase.table('user_interactions')\
        .select('*')\
        .gte('interaction_time', since_date)\
        .execute()
    
    count = len(interactions.data) if interactions.data else 0
    
    print(f"Last {days:3d} days (since {since_date[:19]}): {count:3d} interactions")
    
    if count > 0 and count <= 5:
        print("  Sample interactions:")
        for i in interactions.data[:3]:
            print(f"    - {i['interaction_type']:15s} at {i['interaction_time']}")

# Get all interactions to see date range
print("\n" + "=" * 70)
print("ALL INTERACTIONS (checking date range)")
print("=" * 70)

all_interactions = supabase.table('user_interactions')\
    .select('interaction_time')\
    .order('interaction_time.desc')\
    .execute()

if all_interactions.data:
    dates = [i['interaction_time'] for i in all_interactions.data]
    print(f"\nTotal interactions: {len(dates)}")
    print(f"Newest: {dates[0]}")
    print(f"Oldest: {dates[-1]}")
    
    # Check timezone awareness
    newest = dates[0]
    print(f"\nDate format analysis:")
    print(f"  Has 'T': {('T' in newest)}")
    print(f"  Has 'Z': {('Z' in newest)}")
    print(f"  Has '+': {('+' in newest)}")
    
    # Try parsing
    try:
        parsed = datetime.fromisoformat(newest.replace('Z', '+00:00'))
        print(f"  Parsed successfully: {parsed}")
        print(f"  Timezone aware: {parsed.tzinfo is not None}")
    except Exception as e:
        print(f"  Parse error: {e}")

else:
    print("No interactions found!")
