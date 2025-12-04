# 🚀 Quick Start: A/B Testing RL Recommendations

## TL;DR

Test if RL recommendations are better than baseline by automatically splitting users into two groups and comparing performance metrics.

## 5-Minute Setup

### Step 1: Run Database Script (2 minutes)

1. Open Supabase SQL Editor
2. Copy/paste: `database/ab_testing_schema.sql`
3. Click "Run"
4. ✅ 4 tables created

### Step 2: Restart Flask (30 seconds)

```bash
# Press Ctrl+C in terminal running Flask
python app.py
# ✅ A/B endpoints loaded
```

### Step 3: Start First Test (2 minutes)

1. Go to: `http://localhost:5000/admin/ab-testing`
2. Click "Start New Test"
3. Fill form:
   - Name: "RL vs Baseline Test 1"
   - Control%: 50
   - Duration: 14 days
4. Click "Start Test"
5. ✅ Test running!

### Step 4: Generate Data (ongoing)

- Use platform normally
- View recommendations
- Click projects
- Bookmark items
- System automatically tracks everything

### Step 5: Check Results (after 7 days)

1. Dashboard shows real-time metrics
2. Wait for "Statistically Significant" badge
3. Review winner (Control vs Treatment)
4. Click "Rollout Winner" when ready
5. ✅ Done!

## What Gets Tested?

### Control Group (50% of users)

- Gets **baseline** recommendations
- Pure embedding similarity
- No reinforcement learning

### Treatment Group (50% of users)

- Gets **RL-enhanced** recommendations
- Thompson Sampling + embeddings
- Learns from user behavior

## Metrics Compared

| Metric         | Formula                          | Good Value       |
| -------------- | -------------------------------- | ---------------- |
| **CTR**        | Clicks / Impressions × 100       | > 5%             |
| **Engagement** | Interactions / Impressions × 100 | > 10%            |
| **Avg Reward** | Σ(rewards) / Interactions        | Higher is better |

## When to Roll Out?

✅ **Ready when**:

- Test ran 7+ days
- 100+ interactions per group
- P-value < 0.05
- Winner is clear

❌ **Wait if**:

- "Not Yet Significant" showing
- Less than 100 interactions
- Metrics still fluctuating

## Quick Commands

### Verify RL System

```bash
python deep_rl_verification.py
```

### Check Database

```sql
SELECT * FROM ab_test_configs WHERE status = 'active';
SELECT COUNT(*) FROM ab_test_assignments;
SELECT * FROM ab_test_results ORDER BY recorded_at DESC;
```

### Access Dashboards

- A/B Testing: `/admin/ab-testing`
- RL Performance: `/admin/rl-performance`
- Analytics: `/admin/analytics`

## Troubleshooting

**Problem**: Dashboard says "No Active Test"
**Fix**: Click "Start New Test"

**Problem**: Metrics show 0
**Fix**: Generate user interactions first

**Problem**: "Not Yet Significant"
**Fix**: Wait for more data (patience!)

---

**Need Help?** Check `AB_TESTING_GUIDE.md` for detailed documentation.
