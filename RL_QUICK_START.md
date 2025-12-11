# 🚀 Quick Start: RL Recommendation System

## ✅ System Status: ACTIVE

Your RL recommendation system is now ready! Here's how to use it.

---

## 🏃 Start the App

```bash
cd e:\5MDS\Project\project
python app.py
```

**Look for these startup messages**:

```
✅ RL Recommendation Engine initialized successfully
✅ Background RL training scheduler started
   - Daily model retraining: 2:00 AM
   - Cache invalidation: Every 6 hours
   - Performance monitoring: Every hour
```

---

## 📊 Monitor RL Performance

### Option 1: Admin Dashboard

1. Login as admin
2. Visit: `http://localhost:5000/admin/analytics`
3. Check RL metrics section

### Option 2: API Endpoint

```bash
curl http://localhost:5000/api/admin/analytics/rl-performance?days=7
```

### Option 3: Trigger Manual Training

```bash
curl -X POST http://localhost:5000/api/admin/rl/trigger-training \
  -H "Content-Type: application/json" \
  -d '{"days": 7}'
```

---

## 🔧 Configuration

### Toggle RL On/Off

**File**: `app.py` (line ~53)

```python
USE_RL_RECOMMENDATIONS = True   # RL enabled
# USE_RL_RECOMMENDATIONS = False  # Similarity only
```

### Adjust Exploration Rate

**File**: `services/rl_recommendation_engine.py` (line ~38)

```python
exploration_rate = 0.15  # 15% exploration (default)
# Higher = more exploration, Lower = more exploitation
```

### Adjust Similarity/Bandit Balance

**File**: `services/rl_recommendation_engine.py` (lines ~52-53)

```python
similarity_weight = 0.6  # 60% similarity (default)
bandit_weight = 0.4      # 40% RL learning (default)
```

---

## 📈 Expected Timeline

### Week 1 (Cold Start)

- **CTR**: ~65% (baseline)
- **Method**: Mostly similarity
- **Status**: Collecting data

### Weeks 2-4 (Learning Phase)

- **CTR**: ~70-75%
- **Method**: Balanced RL + similarity
- **Status**: Active improvement

### Month 2+ (Mature)

- **CTR**: ~75-85%
- **Method**: RL-optimized
- **Status**: Continuous optimization

---

## 🎯 Key Metrics to Watch

1. **Click-Through Rate (CTR)**: Target 75-85%
2. **Average Reward**: Target 5.0+
3. **Positive Interaction Rate**: Target 70%+
4. **Training Examples**: Need 50+ for meaningful results

---

## 🐛 Troubleshooting

### RL not working?

1. Check `USE_RL_RECOMMENDATIONS = True` in app.py
2. Restart Flask app
3. Check logs for errors

### Background tasks not running?

1. Verify apscheduler installed: `pip list | grep -i apscheduler`
2. Check startup logs for "Background RL training scheduler started"

### Want to switch back?

```python
# app.py line 53
USE_RL_RECOMMENDATIONS = False
```

Then restart app.

---

## 📞 Support

Check detailed documentation:

- `RL_IMPLEMENTATION_REPORT.md` - Full technical details
- `RL_ACTIVATION_SUCCESS.md` - Complete activation guide

---

**Status**: ✅ Ready to use!  
**Next**: Start your Flask app and monitor RL performance!
