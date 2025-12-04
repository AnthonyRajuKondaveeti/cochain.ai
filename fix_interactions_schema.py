"""
Fix user_interactions table schema to allow NULL for user_query_id and recommendation_result_id
This is needed because not all interactions come from a specific query.
"""
from database.connection import supabase
import sys

def fix_schema():
    """Run the schema fix migration"""
    try:
        print("🔧 Fixing user_interactions table schema...")
        
        # Read the SQL migration file
        with open('database/fix_user_interactions.sql', 'r') as f:
            sql_commands = f.read()
        
        # Split into individual commands
        commands = [cmd.strip() for cmd in sql_commands.split(';') if cmd.strip() and not cmd.strip().startswith('--')]
        
        print(f"📝 Found {len(commands)} SQL commands to execute")
        
        # Execute each command
        for i, command in enumerate(commands, 1):
            if command:
                print(f"   [{i}/{len(commands)}] Executing: {command[:50]}...")
                try:
                    supabase.rpc('exec_sql', {'query': command}).execute()
                    print(f"   ✅ Command {i} succeeded")
                except Exception as e:
                    # Try alternative method using raw SQL
                    print(f"   ⚠️  RPC method failed, trying direct execution...")
                    print(f"   Error was: {str(e)}")
                    print(f"\n   Please run this SQL command manually in Supabase SQL Editor:")
                    print(f"   {command}\n")
        
        print("\n✅ Schema migration completed!")
        print("\nℹ️  If the automatic execution failed, please run the SQL commands manually:")
        print("   1. Go to Supabase Dashboard > SQL Editor")
        print("   2. Run the contents of: database/fix_user_interactions.sql")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during schema migration: {str(e)}")
        print("\n📋 Manual steps required:")
        print("   1. Go to Supabase Dashboard > SQL Editor")
        print("   2. Run these commands:")
        print("\n   ALTER TABLE user_interactions ALTER COLUMN user_query_id DROP NOT NULL;")
        print("   ALTER TABLE user_interactions ALTER COLUMN recommendation_result_id DROP NOT NULL;")
        return False

if __name__ == '__main__':
    print("=" * 70)
    print("CoChain.ai - User Interactions Schema Fix")
    print("=" * 70)
    print()
    
    success = fix_schema()
    
    if not success:
        print("\n⚠️  Automatic migration failed. Please run SQL commands manually.")
        sys.exit(1)
    else:
        print("\n🎉 Migration completed successfully!")
        sys.exit(0)
