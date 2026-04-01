# Suspicion Score System

**Status**: DEPLOYED ✅  
**Tests**: 8/8 Passing  
**Feature Type**: Continuous Pressure (Layer 3 of Capital Governance)

---

## Executive Summary

The Suspicion Score System creates **continuous pressure on operators without requiring definitive proof** of malfeasance. Unlike binary breach flags, suspicion allows graduated penalties to accumulate from suspicious patterns, creating incentive for clean operations while allowing natural recovery.

**Core Concept**: "Operators feel constant pressure from suspicious patterns, even when evidence isn't conclusive. This incentivizes clean operations through mechanical enforcement rather than discretionary judgment."

**Key Insight**: Suspicion is not accusation—it's measurement of deviation from expected behavior. The system watches for patterns and penalizes operators for creating suspicious situations, while rewarding clean operations through decay.

---

## The Rule

### Formula

```
daily_risk = (max(0, variance_deviation - 1.5) / 10.0) + (0.5 if pattern_anomaly else 0)
suspicion_score = suspicion_score × (1 - 0.1) + daily_risk
suspicion_score = min(suspicion_score, 10.0)

penalty_multiplier = 0.8 if (suspicion_score ≥ 5.0) else 1.0
dce_adjusted = base_dce × penalty_multiplier
```

### Risk Components

#### 1. Variance Deviation (0.0 - 0.85 points/day)

**Tolerance**: ±1.5% variance is considered clean

**Calculation**: `(max(0, variance% - 1.5) / 10.0)`

| Variance | Daily Risk | Interpretation |
|----------|-----------|---|
| 0.5% | 0.0 | Well within tolerance |
| 1.5% | 0.0 | At tolerance limit |
| 2.0% | 0.05 | Slightly suspicious |
| 2.5% | 0.10 | Moderately suspicious |
| 3.5% | 0.20 | Clearly suspicious |
| 5.0% | 0.35 | Highly suspicious |
| 10.0%+ | 0.85 | Severe deviation |

**Rationale**: Operators controlling quality should maintain variance < 1.5%. Each additional 1% adds 0.1 points of suspicion. This creates graduated pressure—minor deviations don't trigger full penalties, but consistent patterns accumulate.

#### 2. Pattern Anomaly (0.0 or 0.5 points/day)

**Triggers**: Detected by:
- Entropy Monitor (high randomness in patterns)
- Z-score analysis (extreme statistical outliers)
- Breach detection (unusual activity sequences)
- Manual review flagging

**Calculation**: `0.5 if pattern_detected else 0.0`

**Rationale**: Pattern anomalies are qualitative signals that the operator is behaving unusually. Even if variance is acceptable, suspicious patterns add pressure separately.

### Decay Mechanism

**Formula**: `score = score × (1 - 0.1)` per day = 10% daily decay

**Mechanism**: Each day without suspicious activity reduces the score by 10%, allowing operators to recover reputation over time.

**Recovery Timeline**:
- **Score 5.0** → Penalty active
- After 5 clean days → ~2.95 (below threshold, penalty lifted)
- After 10 clean days → ~1.74
- After 20 clean days → ~0.31 (nearly cleared)

**Key Property**: Decay is exponential, not linear. Early recovery is slower (first week removes ~1.0 points), but once below threshold, reputation recovers quickly (remaining score clears in ~10 more days).

### Penalty Application

**Trigger**: When `suspicion_score ≥ 5.0`

**Penalty**: `dce_adjusted = dce_base × 0.8` = **20% capital reduction**

**Mechanics**:
- Applied at DCE calculation time (daily capital decision)
- Stacks multiplicatively with other penalties (hard floor, cumulative loss)
- Does NOT block funding entirely (unlike hard floor at <50% efficiency)
- Lifted automatically when score drops below 5.0

---

## Impact Examples

### Scenario 1: Clean Operation
```
Daily variance: 1.2%
Pattern anomalies: None

Day 1:  risk = (1.2-1.5)/10 + 0 = 0.0  →  score = 0.0
Day 2:  risk = 0.0                      →  score = 0.0
Day 30: score = 0.0

penalty_multiplier = 1.0 (no penalty)
Capital capacity: FULL
```

**Outcome**: Operator maintains clean operations, faces no suspicion-based capital pressure. This is the baseline expectation.

---

### Scenario 2: Gradual Accumulation (18-Day Breach)
```
Daily variance: 2.5%
Pattern anomalies: Yes (detected daily)
Daily risk: (2.5-1.5)/10 + 0.5 = 0.1 + 0.5 = 0.6 points/day

Day 1:   score = 0.0 × 0.9 + 0.6 = 0.60
Day 6:   score ≈ 2.81
Day 12:  score ≈ 4.31
Day 18:  score ≈ 5.10  ← Penalty ACTIVATES

Action: From Day 18 onward, capital reduced by 20%
Multiplier: 0.8 (applies automatically in DCE calculation)
```

**Impact**: 18 consecutive suspicious days pushes the operator to penalty threshold. The gradual accumulation gives early warning—by day 12, score is 4.31, only 0.69 away from penalty. This provides incentive to correct behavior before penalty hits.

---

### Scenario 3: Recovery After Breach
```
Day 18:  score = 5.10  (penalty: 0.8)
Day 19:  (clean day)  score = 5.10 × 0.9 = 4.59
Day 20:  (clean day)  score = 4.59 × 0.9 = 4.13
Day 23:  (clean day)  score = 3.70
Day 26:  (clean day)  score = 3.33
Day 30:  (clean day)  score = 2.66  ← Below threshold, penalty LIFTED
Day 40:  (clean day)  score = 0.56

Action: Penalty lifted after ~12 clean days
Recovery path: Operator can clear suspicion by demonstrating clean operations
```

**Outcome**: System allows genuine recovery. An operator caught in temporary suspicious activity can rebuild reputation through ~2 weeks of clean operations. After 30 total days, the incident is largely forgotten (score < 1.0).

---

### Scenario 4: Immediate Pattern Anomaly
```
Day 1: Variance = 0.9% (clean), BUT entropy monitor flags pattern anomaly
Daily risk = (0.9-1.5)/10 + 0.5 = 0.0 + 0.5 = 0.5

Day 1:   score = 0.5
Day 2:   score = 0.5 × 0.9 = 0.45
Day 10:  score ≈ 0.02  (one pattern anomaly decays in ~10 days)

Penalty: Never reaches threshold
Capital impact: None
```

**Outcome**: Isolated pattern anomalies don't trigger capital penalties—they decay naturally. But repeated anomalies (pattern every day) accumulates score toward threshold. This prevents false positives from paralyzing capital, while catching habitual suspicious behavior.

---

## Integration with Other Penalty Layers

### Penalty Stacking Order

```
1. HARD FLOOR (Layer 1)
   ↓ Check: if efficiency < 50% → return 0.0 (blocked)
   ↓
2. CUMULATIVE LOSS PRESSURE (Layer 2)
   ↓ Check: if rolling_avg < 75% → apply × 0.5 multiplier
   ↓
3. SUSPICION SCORE (Layer 3)
   ↓ Check: if score ≥ 5.0 → apply × 0.8 multiplier
   ↓
4. FINAL DCE
   dce = base_dce × cumulative_penalty × suspicion_penalty
```

### Example: Combined Penalties

**Operator State**:
- Current efficiency: 55% (above hard floor, passes check 1)
- 30-day rolling avg: 70% (below 75%, triggers cumulative loss)
- Suspicion score: 6.0 (above threshold, triggers penalty)

**Calculation**:
```
base_dce = 100,000 USD
cumulative_loss_multiplier = 0.5  (rolled avg < 75%)
suspicion_multiplier = 0.8  (score ≥ 5.0)

dce = 100,000 × 0.5 × 0.8 = 40,000 USD

Capital reduced by 60% total (50% from cumulative loss, 20% from suspicion)
```

**Outcome**: Operator feels compounding pressure. To recover full capacity, must:
1. Maintain efficiency > 50% (hard floor)
2. Achieve rolling avg > 75% (cumulative loss lifts)
3. Accumulate 12+ clean days (suspicion score decays below 5.0)

---

## Database Schema Changes

### MillIntegrityState Table

Added fields for suspicion tracking:

```python
class MillIntegrityState(SQLModel, table=True):
    # ... existing fields ...
    
    # NEW: Suspicion Score System
    suspicion_score: float = Field(default=0.0)
        # Current suspicion score (0.0 - 10.0)
        # Increment: variance deviation + pattern anomalies
        # Decrement: daily decay (10% per day)
        # Penalty: applied when score ≥ 5.0 (0.8 multiplier)
    
    suspicion_updated_at: datetime = Field(default_factory=datetime.utcnow)
        # Timestamp of last suspicion update
        # Used to calculate decay when loading from DB
```

### Data Types

- `suspicion_score`: Float (0.0 - 10.0, capped at max)
- `suspicion_updated_at`: DateTime (UTC)

### Persistence Model

Suspicion scores persist across system restarts. When the system initializes:
1. Load `suspicion_score` from database
2. Calculate elapsed days since `suspicion_updated_at`
3. Apply decay: `score = score × (0.9 ^ days_elapsed)`
4. Use decayed score for today's capital decision

---

## Recovery Mechanism

### How Operators Recover

**Automatic Decay**:
- No action required; score decays 10% per day
- Clean operations = no new risk added
- Purely time-based forgiveness

**Timeline**:
- Reached 5.0 at day 18 of suspicious activity
- Returns below 5.0 after ~12 clean days (day 30 total)
- Score < 1.0 after ~23 clean days (day 41 total)
- Score ≈ 0.0 after ~30 clean days (day 48 total)

**Incentive Structure**:
1. **First week clean**: Noticeable decay (~-0.6 points/week), operator feels progress
2. **Second week clean**: Further progress (~-0.5 points/week), approaching threshold
3. **Third+ week clean**: Rapid final decay (<0.1 points), reputation nearly restored

### Preventing Gaming

**Cannot be manipulated by**:
- Single day of clean operation (needs sustained behavior)
- High trust scores (decay is independent of trust)
- Capital infusion (mechanical enforcement, not discretionary)

**Decay is inevitable**—there's no way to "freeze" suspicion at high levels. This ensures operators always have a recovery path.

---

## Technical Implementation

### Core Class: SuspicionTracker

```python
class SuspicionTracker:
    def __init__(self, decay_rate: float = 0.1, threshold: float = 5.0):
        """Initialize with 10% daily decay and 5.0 penalty threshold."""
        self.score = 0.0
        self.decay_rate = decay_rate
        self.threshold = threshold
        self.max_score = 10.0

    def update(self, deviation_pct: float, pattern_anomaly: bool) -> float:
        """
        Update score based on day's variance and anomalies.
        
        Returns new score after decay and risk addition.
        """
        self.score = self.score * (1.0 - self.decay_rate)
        variance_risk = max(0.0, deviation_pct - 1.5) / 10.0
        pattern_risk = 0.5 if pattern_anomaly else 0.0
        self.score = min(self.score + variance_risk + pattern_risk, self.max_score)
        return self.score

    def decay_daily(self) -> float:
        """Apply one day of decay without adding risk."""
        self.score = self.score * (1.0 - self.decay_rate)
        return self.score

    def penalty_multiplier(self) -> float:
        """Return 0.8 if score >= threshold, else 1.0."""
        return 0.8 if self.score >= self.threshold else 1.0

    def get_status(self) -> dict:
        """Return dict with score, penalty status, and recovery estimate."""
        return {
            "current_score": round(self.score, 2),
            "threshold": self.threshold,
            "penalty_active": self.score >= self.threshold,
            "penalty_multiplier": self.penalty_multiplier(),
            "estimated_recovery_days": self._estimate_recovery()
        }
```

### Integration Points

#### 1. Daily Variance Update

**Called from**: PXE Step 4 or reconciliation engine

```python
# Get today's variance from reconciliation
variance = calculate_daily_variance(mill_id, metrics)
has_anomaly = entropy_monitor.check_pattern(mill_id)

# Update suspicion
capital_controls.update_suspicion(mill_id, variance, has_anomaly)
```

#### 2. DCE Calculation

**Called from**: `CapitalControls.calculate_dce()`

```python
def calculate_dce(self, mill_id: str, ...)  -> float:
    # ... existing calculations ...
    
    # Apply suspicion penalty
    suspicion_multiplier = self.suspicion_penalty(mill_id)
    dce = base_dce * suspicion_multiplier
    
    return dce
```

#### 3. PXE Advance Rate

**Called from**: `PXE.compute_advance_rate()` with optional `mill_id`

```python
def compute_advance_rate(trust_score: float, efficiency: float, 
                         base_rate: float, mill_id: str = None) -> float:
    # Hard floor check
    if efficiency < 0.5:
        return 0.0
    
    # Apply cumulative loss penalty
    effective_rate = base_rate
    if mill_id:
        cumulative_mult = capital_controls.cumulative_penalty(mill_id)
        effective_rate = base_rate * cumulative_mult
    
    # Calculate advance rate (suspicion penalty applied in DCE, not here)
    return effective_rate
```

---

## Testing & Validation

### Test Coverage

| Test | Purpose | Status |
|------|---------|--------|
| Initialization | Verify default parameters | ✅ PASS |
| Variance Risk | Validate tolerance level (1.5%) | ✅ PASS |
| Pattern Anomaly | Confirm 0.5 point contribution | ✅ PASS |
| Daily Decay | Verify 10% exponential decay | ✅ PASS |
| Accumulation | 18-day suspicious scenario | ✅ PASS |
| Threshold | Penalty applies at 5.0 | ✅ PASS |
| Max Cap | Score bounded at 10.0 | ✅ PASS |
| Status Output | Recovery estimate format | ✅ PASS |

**Result**: 8/8 tests passing

### Validation Scenarios

**Clean Operations** (all variance < 1.5%, no anomalies):
- Score remains 0.0
- No penalty applied
- Capital unrestricted

**Suspicious Pattern** (18 days × 2.5% variance + anomalies):
- Score reaches 5.1 on day 18
- Penalty activates (0.8 multiplier)
- Recovery achieved in ~12 clean days

**Mixed Scenario** (10 suspicious + 20 clean):
- Accumulates to 3.0+
- Never reaches threshold in this case
- No penalty, no impact

---

## FAQ

### Q: Why 1.5% tolerance?

**A**: Industry standard for well-controlled operations. Operators with manual processes naturally produce 0.5-1.5% variance. Above 1.5% suggests either system breakdown or deliberate manipulation. The system gives benefit of doubt for small deviations (< 0.1 points added until 2.0%+) while catching sustained patterns.

### Q: What if an operator has one bad day?

**A**: Single-day variance:
- 2.0% variance = 0.05 points, decays to ~0.04 next day
- 3.0% variance = 0.15 points, decays to ~0.13 next day

One day doesn't trigger penalty. But repeated days accumulate. This prevents overreaction while catching habits.

### Q: Can an operator "game" the decay?

**A**: No. Decay is automatic and mechanical:
- No discretionary override
- No "good behavior credits" outside of time passing
- No way to freeze or reset score

Only time and clean operations allow recovery.

### Q: How does suspicion interact with trust score?

**A**: Independently:
- **Trust Score** = historical operator reliability (breach count, volatility history)
- **Suspicion Score** = current pattern deviation (variance, anomalies)

An operator with high trust score but current suspicious activity gets penalized by suspicion (mechanical) while maintaining trust. Trust can slowly recover when suspicion score is high, but suspicion penalties apply regardless of trust.

### Q: What if variance is caused by external factors (supplier shortage)?

**A**: Suspicion score captures variance but doesn't judge cause:
- Variance = 4.0% → adds 0.3 points regardless of reason
- External factors still create operational risk
- System is agnostic to cause, focused on impact

If the variance persists for weeks, score accumulates and triggers caution. But if variance resolves within days, score decays quickly. This allows natural recovery from temporary disruptions while catching persistent problems.

### Q: Can suspicion score exceed 10.0?

**A**: No. Score is capped at 10.0 maximum:
- Prevents extreme penalties from unlimited accumulation
- Acts as safety valve—score can't go higher even with months of suspicious behavior
- Recovery still possible from any score level via decay

### Q: How long until reputation is fully restored?

**A**: Approximately 30 days of clean operations:
- Day 30 (after major breach): score < 0.5
- Day 40: score < 0.1
- Day 50: score ≈ 0.0

Recovery is gradual but inevitable. An operator caught in suspicious pattern can return to good standing in ~6 weeks of clean operations.

---

## Deployment Notes

### Configuration Parameters

```python
# In backend/capital_controls.py
DEFAULT_SUSPICION_DECAY_RATE = 0.1     # 10% daily decay
DEFAULT_SUSPICION_THRESHOLD = 5.0      # Penalty triggers at 5.0+
MAX_SUSPICION_SCORE = 10.0             # Hard cap

VARIANCE_TOLERANCE = 1.5               # ±1.5% is clean
VARIANCE_RISK_SCALE = 10.0             # (variance - 1.5) / 10.0
PATTERN_ANOMALY_RISK = 0.5             # Fixed 0.5 points
SUSPICION_PENALTY_MULTIPLIER = 0.8     # 20% capital reduction
```

### Customization

All parameters are configurable in `SuspicionTracker.__init__()`:

```python
# Faster forgiveness (6% daily decay)
tracker = SuspicionTracker(decay_rate=0.06, threshold=5.0)

# Stricter enforcement (threshold 4.0)
tracker = SuspicionTracker(decay_rate=0.1, threshold=4.0)

# Higher tolerance (2.0% instead of 1.5%)
# Requires code change in variance_risk calculation
```

### Database Evolution

Schema includes suspicion fields. For existing deployments:
```sql
ALTER TABLE mill_integrity_state ADD COLUMN suspicion_score REAL DEFAULT 0.0;
ALTER TABLE mill_integrity_state ADD COLUMN suspicion_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
```

---

## Related Documentation

- [HARD_ECONOMIC_FLOOR.md](HARD_ECONOMIC_FLOOR.md) - Layer 1: 50% efficiency circuit breaker
- [CUMULATIVE_LOSS_PRESSURE.md](CUMULATIVE_LOSS_PRESSURE.md) - Layer 2: 30-day rolling average memory
- [ARCHITECTURE.md](ARCHITECTURE.md) - Full penalty system overview
- [test_suspicion_score.py](test_suspicion_score.py) - Comprehensive test suite

---

## Summary

The Suspicion Score System provides the third layer of capital governance discipline, creating continuous pressure on operators through mechanical enforcement of pattern-based penalties. Unlike hard floors or cumulative loss measures, suspicion allows graduated response to behavioral anomalies while providing genuine recovery paths through natural decay.

**Core Principle**: "The system doesn't accuse—it measures. Operators feel pressure for suspicious activity, but can always recover through demonstrated clean operations."
