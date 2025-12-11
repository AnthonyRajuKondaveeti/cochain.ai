# 🎉 Admin Pages - Complete Guide

## ✅ What's Fixed

1. **Renamed template file**: `user.html` → `users.html`
2. **Added Users link** to navigation menu (both desktop & mobile)
3. **Admin section** now shows both Analytics and Users

---

## 👑 Your Admin Access

### As admin (`tonykondaveetijmj98@gmail.com`), you now have:

### 1. **📊 Analytics Dashboard**

**URL**: http://localhost:5000/admin/analytics

**Shows:**

- Total Users count
- Total Interactions (clicks + bookmarks)
- Click-Through Rate (CTR)
- Total Bookmarks
- **Charts**: Position Bias, Domain Performance
- **Table**: Top Projects by engagement
- **Export**: Download interaction data for RL training

---

### 2. **👥 User Management** ⭐ NEW!

**URL**: http://localhost:5000/admin/users

**Shows:**

- ✅ **ALL registered users**
- ✅ User details: Name, Email, Join Date
- ✅ Activity stats per user:
  - Total sessions
  - Time on platform
  - GitHub views
  - GitHub clicks
  - Projects created
  - Collaboration requests sent
- ✅ **Filter & Sort** options
- ✅ **Click any user** to see full details:
  - Complete profile info
  - Education, field of study
  - Skills and interests
  - Recent session history
  - Engagement metrics

---

## 🚀 How to Access

### Method 1: Direct URL

1. Go to: **http://localhost:5000/admin/users**

### Method 2: Navigation Menu

1. Click your profile icon (top right)
2. You'll see an **Admin** section:
   - 📊 Analytics
   - 👥 Users ← Click this!

### Method 3: Mobile Menu

1. Click the hamburger menu (☰)
2. Scroll to **Admin** section
3. Click **Users**

---

## 📋 User Management Features

### Summary Stats (Top of page)

- **Total Users**: How many people registered
- **Active (7d)**: Users active in last 7 days
- **New (7d)**: New registrations in last 7 days
- **Avg. Time/User**: Average engagement time

### User List

Each user card shows:

- **Avatar** with initials
- **Name & Email**
- **Join Date**
- **Stats badges**:
  - ⏱️ Time spent on platform
  - 👁️ GitHub projects viewed
  - 🖱️ GitHub projects clicked
  - 📂 Projects created
- **Details button** to view full profile

### Filter & Sort Options

- **Search**: By email or name
- **Sort by**:
  - Registration Date
  - Total Sessions
  - Time on Platform
  - Projects Created
- **Order**: Ascending or Descending
- **Per Page**: 25, 50, or 100 users

### View User Details

Click "Details" button on any user to see:

- **User Info**: Name, email, join date, status
- **Profile**: Education, field of study, skill level, interests
- **Engagement**: Total sessions, time, projects, requests
- **Recent Sessions**: Login times, duration, pages visited

---

## 🎯 What You Can Do

✅ **See who registered**: View all user emails and names
✅ **Track engagement**: See who's active vs inactive
✅ **Understand users**: View their profiles and interests
✅ **Monitor activity**: Check session history and time spent
✅ **Export data**: All data can be exported from analytics page

---

## 📊 Sample View

When you open `/admin/users`, you'll see something like:

```
👥 User Management
Manage and analyze platform users

[Search: ___________] [Sort: Registration Date ▼] [Order: Desc ▼] [Apply Filters]

┌─────────────────────────────────────────────────────────┐
│ Total Users: 1    Active (7d): 0    New (7d): 1         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ TK  tonykondaveetijmj98@gmail.com                       │
│     Tony Kondaveeti                                      │
│     Joined: Nov 9, 2025                                  │
│                                                          │
│     ⏱️ 0m   👁️ 12 views   🖱️ 0 clicks   📂 0 projects  │
│                                         [Details ▶]      │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 If You Don't See Any Users

**Possible reasons:**

1. **Not logged in as admin**

   - Solution: Logout and login with `tonykondaveetijmj98@gmail.com`

2. **RLS (Row Level Security) blocking**

   - Solution: Make sure you applied the RLS policies from `database/fix_rls_policies.sql`

3. **No users in database yet**
   - Solution: Register some users first!

---

## 🎉 Try It Now!

1. **Make sure Flask is running**: `python app.py`
2. **Login as admin**: http://localhost:5000/logout then login
3. **Go to Users page**: http://localhost:5000/admin/users
4. **See your user list!** 🎊

---

**You now have full visibility into all registered users!** 👑
