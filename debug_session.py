"""
Debug Script - Check Session and Admin Status
Run this to see what's in your session and verify admin status
"""

from database.connection import supabase

# Admin emails list
ADMIN_EMAILS = [
    'admin@cochain.ai', 
    'analytics@cochain.ai',
    'anthony.raju@msds.christuniversity.in',
    'tonykondaveetijmj98@gmail.com'
]

print("=" * 80)
print("🔍 ADMIN STATUS DEBUG")
print("=" * 80)

# Check users in database
print("\n📊 Checking users in database...")
try:
    users_result = supabase.table('users').select('id, email, full_name').execute()
    
    if users_result.data:
        print(f"\n✅ Found {len(users_result.data)} users:")
        for user in users_result.data:
            is_admin = user['email'] in ADMIN_EMAILS
            admin_mark = "👑 ADMIN" if is_admin else "👤 User"
            print(f"   {admin_mark} - {user['email']} ({user['full_name']})")
            
        # Check your specific email
        print(f"\n🎯 Checking your email: tonykondaveetijmj98@gmail.com")
        your_email = 'tonykondaveetijmj98@gmail.com'
        
        user_found = any(u['email'] == your_email for u in users_result.data)
        is_admin = your_email in ADMIN_EMAILS
        
        print(f"   ✅ Email exists in database: {user_found}")
        print(f"   ✅ Email in ADMIN_EMAILS list: {is_admin}")
        
        if user_found and is_admin:
            print("\n🎉 Everything looks correct! Your email should have admin access.")
            print("\n💡 TIP: Make sure you logged out and logged back in after applying RLS policies.")
            print("   Old sessions might not have the email set correctly.")
            print("\n🔄 To fix: Go to http://localhost:5000/logout and login again")
        elif not user_found:
            print("\n⚠️  Your email is not in the database yet.")
            print("   Please register with: tonykondaveetijmj98@gmail.com")
        elif not is_admin:
            print("\n⚠️  Your email is in database but not in ADMIN_EMAILS list!")
            print("   This should not happen - check app.py ADMIN_EMAILS")
    else:
        print("\n❌ No users found in database")
        print("   Please register first at: http://localhost:5000/register")
        
except Exception as e:
    print(f"\n❌ Error checking database: {e}")

print("\n" + "=" * 80)
print("📋 ADMIN_EMAILS LIST:")
print("=" * 80)
for email in ADMIN_EMAILS:
    print(f"   ✅ {email}")

print("\n" + "=" * 80)
print("🔧 TROUBLESHOOTING STEPS:")
print("=" * 80)
print("1. Logout: http://localhost:5000/logout")
print("2. Login again with: tonykondaveetijmj98@gmail.com")
print("3. Try accessing: http://localhost:5000/admin/analytics")
print("\n💡 The issue is likely an old session without the email stored correctly.")
print("   Logging out and back in will fix it!")
print("=" * 80)
