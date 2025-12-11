"""
Test User Registration After RLS Fix
This script tests if user registration works after applying RLS policies
"""

from services.user_service import UserService
from database.connection import supabase
import sys

def test_registration():
    """Test user registration"""
    
    print("=" * 80)
    print("🧪 TESTING USER REGISTRATION")
    print("=" * 80)
    
    # Create test user data
    test_email = f"test_user_{int(__import__('time').time())}@cochain.test"
    test_password = "TestPassword123!"
    test_name = "Test User"
    
    print(f"\n📝 Test User Details:")
    print(f"   Email: {test_email}")
    print(f"   Password: {test_password}")
    print(f"   Name: {test_name}")
    
    # Initialize user service
    user_service = UserService()
    
    print("\n🔄 Attempting registration...")
    
    try:
        # Attempt registration
        result = user_service.register_user(test_email, test_password, test_name)
        
        if result.get('success'):
            print("\n✅ REGISTRATION SUCCESSFUL!")
            print(f"   User ID: {result.get('user_id')}")
            print(f"   Email: {result.get('email')}")
            print(f"   Full Name: {result.get('full_name')}")
            
            # Verify user exists in database
            print("\n🔍 Verifying user in database...")
            user_check = supabase.table('users').select('*').eq('id', result.get('user_id')).execute()
            
            if user_check.data and len(user_check.data) > 0:
                print("✅ User found in database!")
                print(f"   Record: {user_check.data[0]}")
            else:
                print("❌ User NOT found in database (RLS issue)")
            
            # Check total user count
            print("\n📊 Checking total users...")
            all_users = supabase.table('users').select('id', count='exact').execute()
            print(f"   Total users in database: {all_users.count}")
            
            print("\n" + "=" * 80)
            print("🎉 TEST PASSED - Registration is working!")
            print("=" * 80)
            
            return True
            
        else:
            print("\n❌ REGISTRATION FAILED!")
            print(f"   Error: {result.get('error')}")
            print(f"   Error Type: {result.get('error_type')}")
            
            print("\n" + "=" * 80)
            print("❌ TEST FAILED - Registration not working")
            print("=" * 80)
            print("\n💡 This likely means RLS policies haven't been applied yet.")
            print("   Please run the SQL file in Supabase Dashboard SQL Editor:")
            print("   📁 database/fix_rls_policies.sql")
            
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\n" + "=" * 80)
        print("❌ TEST FAILED - Exception occurred")
        print("=" * 80)
        return False

if __name__ == "__main__":
    success = test_registration()
    sys.exit(0 if success else 1)
