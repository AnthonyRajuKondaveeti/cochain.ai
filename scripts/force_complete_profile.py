
import os
import sys
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import supabase_admin

def force_complete_profile(email):
    print(f"Assigning profile_completed=True for {email}...")
    
    # 1. Get User ID
    user_res = supabase_admin.table('users').select('id').eq('email', email).execute()
    if not user_res.data:
        print("User not found.")
        return
        
    user_id = user_res.data[0]['id']
    print(f"User ID: {user_id}")
    
    # 2. Update 'users' table (often stores the flag)
    # Check if 'profile_completed' is on 'users' table
    try:
        supabase_admin.table('users').update({'profile_completed': True}).eq('id', user_id).execute()
        print("Updated 'users.profile_completed'.")
    except Exception as e:
        print(f"Could not update 'users' table directly: {e}")
        
    # 3. Create/Update 'profiles' table if it exists
    # Based on app.py, there seems to be a profile retrieval. 
    # Let's assume there is a 'user_profiles' or 'profiles' table.
    try:
        data = {
            'user_id': user_id,
            'bio': 'Forced completion via script.',
            'skill_level': 'intermediate',
            'education_level': 'undergraduate',
            'profile_completed': True
        }
        # Try upserting to 'profiles'
        try:
            supabase_admin.table('profiles').upsert(data).execute()
            print("Upserted 'profiles'.")
        except:
            # Try 'user_profiles'
            supabase_admin.table('user_profiles').upsert(data).execute()
            print("Upserted 'user_profiles'.")
            
    except Exception as e:
        print(f"Profile table update warning: {e}")

if __name__ == "__main__":
    force_complete_profile("test_e2e_full_v1@test.com")
