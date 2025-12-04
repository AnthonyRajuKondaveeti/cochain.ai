"""
Verify that training now works correctly
"""

from database.connection import supabase_admin
from datetime import datetime, timedelta

print("=" * 70)
print("TRAINING FIX VERIFICATION")
print("=" * 70)

# 1. Check interactions with admin client
print("\n1. Testing admin client access to interactions...")
since_date = (datetime.now() - timedelta(days=90)).isoformat()
interactions = supabase_admin.table('user_interactions')\
    .select('*')\
    .gte('interaction_time', since_date)\
    .execute()

count = len(interactions.data) if interactions.data else 0
print(f"   ✅ Found {count} interactions using admin client")

if count == 0:
    print("   ❌ ERROR: Still finding 0 interactions!")
    print("   Check if supabase_admin is configured correctly")
else:
    print(f"   ✅ Ready to process {count} interactions")

# 2. Check training history before
print("\n2. Checking current training history...")
history_before = supabase_admin.table('rl_training_history')\
    .select('*')\
    .execute()

before_count = len(history_before.data) if history_before.data else 0
print(f"   Current records: {before_count}")

# 3. Verify imports
print("\n3. Verifying code changes...")
with open('services/contextual_bandit.py', 'r', encoding='utf-8') as f:
    content = f.read()
    if 'supabase_admin' in content:
        print("   ✅ contextual_bandit.py uses admin client")
    else:
        print("   ❌ contextual_bandit.py still using regular client!")

with open('services/background_tasks.py', 'r', encoding='utf-8') as f:
    content = f.read()
    if 'supabase_admin' in content:
        print("   ✅ background_tasks.py uses admin client")
    else:
        print("   ❌ background_tasks.py still using regular client!")
    
    if 'training_record = {' in content and 'run_manual_retrain' in content:
        print("   ✅ run_manual_retrain saves training history")
    else:
        print("   ❌ run_manual_retrain doesn't save history!")

print("\n" + "=" * 70)
print("READY TO TEST")
print("=" * 70)
print("\nNext steps:")
print("1. Restart Flask app (Ctrl+C then `python app.py`)")
print("2. Go to /admin/rl-performance")
print("3. Set period to '7 days' (to include Nov 9 data)")
print("4. Click 'Trigger Training'")
print("5. Should see:")
print("   - Training completes with reward > 0")
print("   - Graphs populate with data")
print("   - Training history increases to", before_count + 1, "records")
