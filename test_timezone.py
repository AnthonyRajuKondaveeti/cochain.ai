"""
Check timezone handling in date queries
"""

from datetime import datetime, timedelta, timezone
from database.connection import supabase_admin

supabase = supabase_admin

print("=" * 70)
print("TIMEZONE TEST")
print("=" * 70)

# Get one interaction to see the exact format
sample = supabase.table('user_interactions')\
    .select('interaction_time')\
    .limit(1)\
    .execute()

if sample.data:
    stored_time = sample.data[0]['interaction_time']
    print(f"\nStored time format: {stored_time}")
    print(f"Type: {type(stored_time)}")
    
    # Try different query formats
    print("\n" + "=" * 70)
    print("TESTING DIFFERENT DATE QUERY FORMATS")
    print("=" * 70)
    
    test_formats = [
        ("datetime.now().isoformat()", (datetime.now() - timedelta(days=90)).isoformat()),
        ("UTC now isoformat", (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()),
        ("Remove microseconds", (datetime.now() - timedelta(days=90)).replace(microsecond=0).isoformat()),
        ("Simple date string", "2025-11-09"),
        ("Very old date", "2025-01-01"),
    ]
    
    for name, since_date in test_formats:
        try:
            result = supabase.table('user_interactions')\
                .select('id', count='exact')\
                .gte('interaction_time', since_date)\
                .execute()
            
            count = result.count or 0
            print(f"\n{name}:")
            print(f"  Query: >= '{since_date}'")
            print(f"  Found: {count} interactions")
        except Exception as e:
            print(f"\n{name}:")
            print(f"  ERROR: {e}")
else:
    print("No interactions found!")

# Test the exact query used in training
print("\n" + "=" * 70)
print("EXACT TRAINING QUERY (90 days)")
print("=" * 70)

since_date = (datetime.now() - timedelta(days=90)).isoformat()
print(f"Query date: {since_date}")

interactions = supabase.table('user_interactions')\
    .select('*')\
    .gte('interaction_time', since_date)\
    .execute()

count = len(interactions.data) if interactions.data else 0
print(f"Found: {count} interactions")

if interactions.data:
    print("\nFirst 3 interactions:")
    for i in interactions.data[:3]:
        print(f"  - {i['interaction_type']:15s} at {i['interaction_time']}")
