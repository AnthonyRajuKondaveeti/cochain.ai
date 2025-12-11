# Profile Redirect Fix

## Issue

After logging in, new users were being redirected to the profile setup page instead of the dashboard, even after completing their profile.

## Root Cause

The `profile_completed` column exists in the `user_profiles` table but **NOT in the `users` table**.

### The Problem Flow:

1. ✅ User completes profile → `user_profiles.profile_completed` is set to `TRUE`
2. ❌ User logs in → Login reads from `users.profile_completed` (which doesn't exist) → defaults to `FALSE`
3. ❌ User is redirected to profile_setup instead of dashboard

## Solution

### 1. Database Migration

Run `database/add_profile_completed_to_users.sql` in your Supabase SQL editor.

This will:

- Add `profile_completed` column to the `users` table
- Update existing users who have completed profiles in `user_profiles` table
- Create an index for better query performance

### 2. Code Fix

Updated `services/user_service.py` → `update_profile()` method to update both tables:

- `user_profiles.profile_completed = TRUE` (existing)
- `users.profile_completed = TRUE` (NEW - this was missing!)

## Files Changed

1. ✅ `services/user_service.py` - Updated `update_profile()` to set `users.profile_completed`
2. ✅ `database/add_profile_completed_to_users.sql` - Migration script to add column

## Testing Steps

1. Run the SQL migration in Supabase
2. Register a new user
3. Complete the profile setup
4. Logout and login again
5. ✅ Should redirect to dashboard instead of profile_setup

## Technical Details

### Before Fix:

```python
# user_service.py - update_profile()
supabase.table('users').update({
    'last_login': datetime.now().isoformat()
    # Missing: 'profile_completed': True
}).eq('id', user_id).execute()
```

### After Fix:

```python
# user_service.py - update_profile()
supabase.table('users').update({
    'last_login': datetime.now().isoformat(),
    'profile_completed': True  # ✅ ADDED
}).eq('id', user_id).execute()
```

## Why This Matters

The login redirect logic in `app.py` checks:

```python
session['profile_completed'] = user.get('profile_completed', False)
# This reads from users table, not user_profiles!

# Redirect logic:
redirect_url = url_for('profile_setup') if not user.get('profile_completed') else url_for('dashboard')
```

Without the `users.profile_completed` column being set, users are stuck in a loop of profile setup even after completing it.
