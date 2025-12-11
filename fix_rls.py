"""
Fix RLS Policies for CoChain.ai Database
This script adds the necessary Row Level Security policies to allow users to register and access data
"""

from database.connection import supabase
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_rls_policies():
    """Apply RLS policies by reading and executing the SQL file"""
    
    print("=" * 80)
    print("🔒 APPLYING ROW LEVEL SECURITY (RLS) POLICIES")
    print("=" * 80)
    
    # Read the SQL file
    try:
        with open('database/fix_rls_policies.sql', 'r') as f:
            sql_content = f.read()
        
        print("\n✅ SQL file loaded successfully")
        
        # Split into individual statements
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip() and not stmt.strip().startswith('--')]
        
        print(f"📝 Found {len(statements)} SQL statements to execute\n")
        
        # Execute each statement
        success_count = 0
        error_count = 0
        
        for i, statement in enumerate(statements, 1):
            # Skip comment-only statements
            if all(line.strip().startswith('--') or not line.strip() for line in statement.split('\n')):
                continue
            
            try:
                # Get statement type for better logging
                stmt_type = statement.split()[0].upper() if statement.split() else "UNKNOWN"
                
                # Show what we're doing
                if 'CREATE POLICY' in statement:
                    policy_name = statement.split('"')[1] if '"' in statement else "unknown"
                    print(f"  [{i}/{len(statements)}] Creating policy: {policy_name}...", end=" ")
                elif 'ALTER TABLE' in statement and 'ENABLE ROW LEVEL SECURITY' in statement:
                    table_name = statement.split()[2] if len(statement.split()) > 2 else "unknown"
                    print(f"  [{i}/{len(statements)}] Enabling RLS on: {table_name}...", end=" ")
                else:
                    print(f"  [{i}/{len(statements)}] Executing {stmt_type}...", end=" ")
                
                # Execute the statement using Supabase RPC
                result = supabase.rpc('exec_sql', {'sql': statement}).execute()
                
                print("✅")
                success_count += 1
                
            except Exception as e:
                error_msg = str(e)
                
                # Check if it's just a "policy already exists" error (not critical)
                if 'already exists' in error_msg.lower():
                    print("⚠️  (already exists)")
                    success_count += 1
                else:
                    print(f"❌ ERROR: {error_msg}")
                    error_count += 1
        
        print("\n" + "=" * 80)
        print(f"✅ COMPLETED: {success_count} successful, {error_count} errors")
        print("=" * 80)
        
        if error_count > 0:
            print("\n⚠️  Some statements failed. You may need to run them manually in Supabase SQL Editor.")
            print("   The SQL file is: database/fix_rls_policies.sql")
        else:
            print("\n🎉 All RLS policies applied successfully!")
            print("   Users can now register and access their data.")
        
    except FileNotFoundError:
        print("❌ ERROR: Could not find database/fix_rls_policies.sql")
        print("   Please make sure the file exists.")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        logger.exception("Failed to apply RLS policies")

if __name__ == "__main__":
    apply_rls_policies()
