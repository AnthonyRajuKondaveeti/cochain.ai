# 🧪 A/B Testing Framework for RL Recommendations

## Overview

The A/B Testing Framework automatically compares Reinforcement Learning (RL) recommendations against baseline (similarity-only) recommendations to determine which performs better. The system handles user assignment, metrics tracking, statistical significance testing, and automatic rollout of winning variants.

## Architecture

### Components

1. **A/B Test Service** (`services/ab_test_service.py`)

   - User group assignment (control vs treatment)
   - Metrics calculation
   - Statistical significance testing
   - Winner determination and rollout

2. **Database Tables** (`database/ab_testing_schema.sql`)

   - `ab_test_configs`: Test configuration and status
   - `ab_test_assignments`: User → group mappings
   - `ab_test_results`: Final test results
   - `ab_test_metrics_history`: Daily metrics tracking

3. **Admin Dashboard** (`templates/admin/ab_testing.html`)

   - Start/end tests
   - Real-time metrics comparison
   - Statistical significance indicators
   - Winner rollout controls

4. **API Endpoints** (in `app.py`)
   - `/api/admin/ab-testing/dashboard`: Get test data
   - `/api/admin/ab-testing/start`: Start new test
   - `/api/admin/ab-testing/end/<test_id>`: End test and rollout winner

## How It Works

### 1. Test Setup

```python
# Admin starts a new A/B test
ab_test_service.start_new_test(
    test_name="RL vs Baseline Q4 2025",
    control_percentage=50,  # 50% get baseline
    duration_days=14,
    description="Testing RL effectiveness for new users"
)
```

### 2. User Assignment

- Users are automatically assigned to groups based on deterministic hash
- Assignment is persistent (same user always gets same group)
- Split: Control (baseline) vs Treatment (RL)

### 3. Metrics Tracked

- **CTR (Click-Through Rate)**: Clicks / Impressions
- **Engagement Rate**: Total interactions / Impressions
- **Average Reward**: Mean reward per interaction
- **Bookmarks**: Number of saved projects
- **User Count**: Users in each group

### 4. Statistical Testing

- **Method**: Two-proportion z-test for CTR
- **Confidence Level**: 95% (configurable)
- **Minimum Effect Size**: 5% improvement required
- **Sample Size**: Minimum 100 interactions per group

### 5. Winner Determination

A variant wins if:

1. ✅ Statistically significant (p < 0.05)
2. ✅ Effect size > 5%
3. ✅ Higher CTR or engagement rate

### 6. Automatic Rollout

- Admin reviews results
- Clicks "Rollout Winner"
- System ends test and updates configuration
- All users get winning variant

## Usage Guide

### For Administrators

#### Starting a Test

1. Go to `/admin/ab-testing`
2. Click "Start New Test"
3. Configure:
   - **Test Name**: Descriptive name
   - **Control %**: % of users getting baseline (default: 50%)
   - **Duration**: Test length in days (7-90)
   - **Description**: Optional notes
4. Click "Start Test"

#### Monitoring Progress

- Dashboard auto-refreshes every 30 seconds
- View real-time metrics for both groups
- Check statistical significance indicator
- Winner badge appears when results are conclusive

#### Ending a Test

1. Review metrics and significance
2. Click "End Test" or "Rollout Winner"
3. System calculates final results
4. Recommendation provided (which variant to use)

### For Developers

#### Integration with Recommendations

The A/B test service automatically determines which recommendation engine to use:

```python
from services.ab_test_service import get_ab_test_service

ab_test_service = get_ab_test_service()

# Check which engine to use for this user
use_rl = ab_test_service.should_use_rl(user_id)

# Get recommendations
if use_rl:
    recommendations = rl_engine.get_recommendations(user_id)
else:
    recommendations = baseline_engine.get_recommendations(user_id)
```

#### Manual Metrics Calculation

```python
# Get metrics for last 7 days
metrics = ab_test_service.calculate_test_metrics(test_id, days=7)

print(f"Control CTR: {metrics['control']['ctr']}%")
print(f"Treatment CTR: {metrics['treatment']['ctr']}%")
print(f"Significant: {metrics['significance']['significant']}")
print(f"Winner: {metrics['winner']}")
```

## Database Setup

Run the SQL schema in Supabase:

```bash
# In Supabase SQL Editor, run:
database/ab_testing_schema.sql
```

This creates:

- 4 tables with proper relationships
- Indexes for performance
- Row Level Security policies
- Automatic timestamp updates

## Configuration

### Test Parameters

```python
class ABTestService:
    def __init__(self):
        self.min_sample_size = 100      # Minimum interactions per group
        self.confidence_level = 0.95    # 95% confidence
        self.minimum_effect_size = 0.05  # 5% minimum improvement
```

### Recommended Settings

| Use Case      | Control % | Duration | Min Sample |
| ------------- | --------- | -------- | ---------- |
| Quick Test    | 50%       | 7 days   | 50         |
| Standard Test | 50%       | 14 days  | 100        |
| Cautious Test | 80%       | 30 days  | 200        |
| High Traffic  | 10%       | 7 days   | 100        |

## Metrics Formulas

### Click-Through Rate (CTR)

```
CTR = (Clicks / Impressions) × 100
```

### Engagement Rate

```
Engagement = (Total Interactions / Impressions) × 100
```

### Average Reward

```
Avg Reward = Σ(rewards) / Total Interactions
```

### Statistical Significance (Z-Test)

```python
# Pooled proportion
p_pool = (clicks1 + clicks2) / (n1 + n2)

# Standard error
SE = sqrt(p_pool × (1 - p_pool) × (1/n1 + 1/n2))

# Z-score
z = (p2 - p1) / SE

# P-value (two-tailed)
p_value = 2 × (1 - Φ(|z|))
```

## Best Practices

### ✅ DO

- Run tests for at least 7 days (full week cycle)
- Wait for statistical significance before ending
- Monitor both CTR and engagement
- Document test objectives
- Keep control % between 20-80%
- Analyze by user segments

### ❌ DON'T

- End tests early (before min sample size)
- Run multiple conflicting tests simultaneously
- Change test configuration mid-test
- Ignore statistical significance
- Rollout losing variant
- Test during holidays/special events

## Troubleshooting

### Issue: No users assigned to test

**Solution**: Check that active test exists, verify user authentication

### Issue: Metrics not updating

**Solution**: Ensure interactions are being recorded in `user_interactions` table

### Issue: "Not Yet Significant"

**Solution**: Wait for more data or extend test duration

### Issue: No clear winner

**Solution**: Variants perform similarly, safe to keep current setup

## Advanced Features

### Gradual Rollout

Instead of immediate 100% rollout, gradually increase traffic:

```python
# Week 1: 10% treatment
# Week 2: 25% treatment
# Week 3: 50% treatment
# Week 4: 100% treatment (if winning)
```

### Segment Analysis

Analyze results by user segments:

```python
# New users vs returning users
# Mobile vs desktop
# Different regions
# Skill levels
```

### Multi-Armed Bandit

Test multiple variants simultaneously:

```python
# Variant A: Pure similarity
# Variant B: RL with 40% weight
# Variant C: RL with 60% weight
# Variant D: Pure RL
```

## API Reference

### Start Test

```http
POST /api/admin/ab-testing/start
Content-Type: application/json

{
    "test_name": "RL vs Baseline Q4",
    "description": "Testing new RL engine",
    "control_percentage": 50,
    "duration_days": 14
}
```

### Get Dashboard Data

```http
GET /api/admin/ab-testing/dashboard

Response:
{
    "success": true,
    "active_test": {...},
    "metrics": {
        "control": {...},
        "treatment": {...},
        "significance": {...},
        "winner": "treatment"
    },
    "past_tests": [...]
}
```

### End Test

```http
POST /api/admin/ab-testing/end/<test_id>

Response:
{
    "success": true,
    "winner": "treatment",
    "action": "rollout_treatment",
    "recommendation": "Use RL for all users"
}
```

## Example Workflow

```
Day 0: Admin starts test (50/50 split)
├─ Control group: 100 users get baseline
└─ Treatment group: 100 users get RL

Day 1-3: Collecting data
├─ Control: 500 impressions, 25 clicks (5% CTR)
└─ Treatment: 500 impressions, 35 clicks (7% CTR)

Day 4-7: More data accumulation
├─ Control: 2000 impressions, 100 clicks (5% CTR)
└─ Treatment: 2000 impressions, 160 clicks (8% CTR)
└─ ✅ Statistically significant!

Day 7: Review results
├─ Treatment wins (8% vs 5% CTR)
├─ Effect size: 60% improvement
├─ P-value: 0.0012 (highly significant)
└─ Decision: Rollout RL to all users

Day 8+: All users get RL recommendations
```

## Success Metrics

Track these KPIs after rollout:

- ✅ Overall CTR improvement
- ✅ User engagement increase
- ✅ Bookmark rate improvement
- ✅ Session duration increase
- ✅ User retention improvement

## Next Steps

1. ✅ Run SQL schema in Supabase
2. ✅ Start first A/B test
3. ✅ Monitor for 7-14 days
4. ✅ Review results
5. ✅ Rollout winner
6. ✅ Measure impact

---

**Status**: ✅ **READY TO USE**
**Last Updated**: November 12, 2025
**Documentation Version**: 1.0
