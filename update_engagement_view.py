"""
Update the user_engagement_summary view to properly count clicks from user_interactions
"""
from database.connection import supabase_admin

print("=" * 60)
print("Updating user_engagement_summary View")
print("=" * 60)

# Read the SQL file
with open('database/fix_user_engagement_view.sql', 'r') as f:
    sql_content = f.read()

print("\n📝 SQL to execute:")
print("-" * 60)
print(sql_content)
print("-" * 60)

print("\n⚠️  IMPORTANT: This SQL needs to be run directly in Supabase SQL Editor")
print("   because views cannot be created via the Supabase Python client.")
print("\nSteps:")
print("   1. Go to your Supabase dashboard")
print("   2. Click on 'SQL Editor' in the left menu")
print("   3. Copy and paste the SQL above")
print("   4. Click 'Run' to execute")
print("\n" + "=" * 60)

# Alternative: Try to check current view definition
print("\n📊 Current state of user_engagement_summary:")
try:
    result = supabase_admin.table('user_engagement_summary').select('user_id, email, github_clicks').limit(5).execute()
    print(f"   Sample data (first 5 users):")
    for user in result.data:
        print(f"      - {user['email']}: {user['github_clicks']} clicks")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("After updating the view in Supabase, run check_clicks_tracking.py again")
print("=" * 60)
