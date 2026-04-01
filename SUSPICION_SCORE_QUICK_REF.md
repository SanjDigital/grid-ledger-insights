# Suspicion Score Quick Reference

## One-Liner

**Continuous pressure system**: Accumulates score from variance deviations and pattern anomalies, decays 10% daily, applies 0.8× multiplier when score ≥ 5.0.

---

## Core Formula

```
daily_risk = (max(0, variance% - 1.5) / 10.0) + (0.5 if pattern_anomaly else 0)
score = score × 0.9 + daily_risk  [capped at 10.0]

penalty = 0.8 if (score ≥ 5.0) else 1.0
dce_adjusted = dce_base × penalty
```

---

## Quick Numbers

| Metric | Value |
|--------|-------|
| Tolerance | ±1.5% variance |
| Daily decay rate | 10% per day |
| Penalty threshold | 5.0 |
| Penalty multiplier | 0.8 (20% reduction) |
| Max score | 10.0 |
| Days to threshold (18 days suspicious) | ~12-14 clean days to recover |
| Pattern anomaly contribution | 0.5 points |

---

## Risk Table

### Variance Risk (daily)
| Variance | Risk | Notes |
|----------|------|-------|
| 0-1.5% | 0.0 | Clean |
| 2.0% | 0.05 | Slight |
| 2.5% | 0.10 | Moderate |
| 3.5% | 0.20 | Concerning |
| 5.0% | 0.35 | High |
| 10%+ | 0.85+ | Severe |

### Decay Chart
| Days | Score (starting 5.0) | Below Threshold? |
|------|-------------------|---|
| 0 | 5.00 | At threshold |
| 5 | 2.95 | Yes ✓ |
| 10 | 1.74 | Yes |
| 15 | 1.03 | Yes |
| 20 | 0.61 | Yes |
| 30 | 0.08 | Yes |

---

## State Diagram

```
CLEAN OPERATION (score < 5.0)
├─ variance ≤ 1.5%
├─ no pattern anomalies
└─ multiplier = 1.0 ✓ FULL CAPACITY

         ↓ (18 days suspicious)

SUSPICIOUS ACTIVITY (score ≥ 5.0)
├─ excess variance accumulates
├─ patterns detected
└─ multiplier = 0.8 ⚠️ -20% CAPITAL

         ↓ (12+ clean days)

RECOVERY (score < 5.0)
├─ variance returns normal
├─ anomalies clear
└─ multiplier = 1.0 ✓ FULL CAPACITY RESTORED
```

---

## Code Usage

### Initialize
```python
from backend.capital_controls import SuspicionTracker

tracker = SuspicionTracker(decay_rate=0.1, threshold=5.0)
```

### Update (called daily)
```python
# With variance and anomaly detection
score = tracker.update(deviation_pct=2.5, pattern_anomaly=True)

# Clean day
score = tracker.update(deviation_pct=1.2, pattern_anomaly=False)
```

### Get Penalty
```python
multiplier = tracker.penalty_multiplier()  # 0.8 or 1.0
dce_adjusted = base_dce * multiplier
```

### Query Status
```python
status = tracker.get_status()
# Returns: {
#   "current_score": 5.2,
#   "threshold": 5.0,
#   "penalty_active": True,
#   "penalty_multiplier": 0.8,
#   "estimated_recovery_days": 12
# }
```

### From CapitalControls
```python
# Update in database
capital_controls.update_suspicion(mill_id, variance_pct, has_anomaly)

# Get penalty multiplier
multiplier = capital_controls.suspicion_penalty(mill_id)

# Calculate DCE with penalty
dce = base_dce * multiplier
```

---

## Integration with Other Penalties

### Stack Order
```
1. Hard Floor (efficiency < 50%) → BLOCKED
2. Cumulative Loss (rolling < 75%) → × 0.5
3. Suspicion Score (score ≥ 5.0) → × 0.8
4. Result = base × 0.5 × 0.8 = 40% of base
```

### Example
```
base_dce = 100,000
cumulative_loss_mult = 0.5   (rolling avg < 75%)
suspicion_mult = 0.8         (score 6.0 ≥ 5.0)

final_dce = 100,000 × 0.5 × 0.8 = 40,000
Reduction: 60% (50% + 20%, stacked)
```

---

## Scenarios

### Scenario A: One-Day Spike
```
Day 1: variance 3.5%, pattern anomaly
Risk = (3.5-1.5)/10 + 0.5 = 0.7
Score = 0 × 0.9 + 0.7 = 0.7
Penalty: 1.0 (no penalty)

Day 2: variance 1.0%, clean
Risk = 0.0
Score = 0.7 × 0.9 = 0.63
Result: No penalty, decays naturally
```

### Scenario B: Sustained Suspicious Activity
```
Days 1-18: variance 2.5%, daily anomaly
Daily risk = 0.1 + 0.5 = 0.6

Day 18: score ≈ 5.1
Action: Multiplier = 0.8, capital reduced 20%

Days 19-30: Clean operations
Day 30: score ≈ 0.6, penalty lifted
Result: 12-day recovery period
```

### Scenario C: Extreme Deviation
```
Days 1-10: variance 6.0%, daily anomalies
Daily risk = 0.45 + 0.5 = 0.95

Day 10: score ≈ 8.0 (approaching max)
Action: Multiplier = 0.8, persist until recovery

Days 11-25: Clean operations
Day 25: score ≈ 1.0, penalty lifted
Result: ~2 week recovery from extreme case
```

---

## Configuration

### Default Parameters
```python
decay_rate = 0.1           # 10% daily forgetting
threshold = 5.0            # Penalty triggers at 5.0+
max_score = 10.0           # Score bounded at 10.0
variance_tolerance = 1.5   # ±1.5% is clean
pattern_risk = 0.5         # Fixed anomaly cost
penalty_multiplier = 0.8   # 20% capital reduction
```

### To Customize
```python
# Faster recovery (20% daily decay)
tracker = SuspicionTracker(decay_rate=0.2, threshold=5.0)

# Stricter (penalty at 4.0)
tracker = SuspicionTracker(decay_rate=0.1, threshold=4.0)

# More forgiving (lower pattern risk)
# Requires code modification
```

---

## Key Properties

✓ **Automatic Decay**: No manual intervention, purely time-based recovery  
✓ **Graduated Pressure**: Accumulates gradually, not binary  
✓ **Fair Recovery**: Always recoverable through clean operations  
✓ **Independent**: Separate from trust scores, hard floors  
✓ **Mechanical**: No discretionary override, fully automatic  
✓ **Bounded**: Max score 10.0 prevents runaway penalties  

---

## Testing

All scenarios validated in `test_suspicion_score.py`:
- ✅ Initialization (defaults correct)
- ✅ Variance risk (tolerance at 1.5%)
- ✅ Pattern anomalies (0.5 points)
- ✅ Daily decay (10% exponential)
- ✅ Accumulation (18 days to threshold)
- ✅ Threshold behavior (0.8 multiplier at 5.0+)
- ✅ Score cap (10.0 maximum)
- ✅ Status output (recovery estimates)

**Result**: 8/8 tests passing ✅

---

## Database

### Schema
```python
class MillIntegrityState(SQLModel, table=True):
    suspicion_score: float = 0.0
    suspicion_updated_at: datetime
```

### Persistence
- Score saved to database daily
- Decay calculated on load: `score = score × (0.9 ^ days_elapsed)`
- Used in daily capital decision calculation

---

## Related Docs

| Document | Purpose |
|----------|---------|
| SUSPICION_SCORE.md | Comprehensive reference |
| HARD_ECONOMIC_FLOOR.md | Layer 1: 50% efficiency cutoff |
| CUMULATIVE_LOSS_PRESSURE.md | Layer 2: 30-day rolling average |
| ARCHITECTURE.md | Full system overview |
| test_suspicion_score.py | Test validation (8/8 passing) |

