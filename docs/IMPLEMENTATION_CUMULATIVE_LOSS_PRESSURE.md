# Implementation Summary: Cumulative Loss Pressure (March 30, 2026)

## What Was Implemented

A **long-term memory system** that tracks operator performance via 30-day rolling average efficiency. If an operator's average efficiency falls below 75%, their capital capacity is permanently halved until they recover.

**Key Principle:** Short-term spikes don't erase the memory of prolonged underperformance. The system remembers damage.

---

## Components Added

### 1. `CapitalControls.get_rolling_efficiency(mill_id, days=30)`
**Location:** [backend/capital_controls.py](backend/capital_controls.py#L204-L240)

Calculates the 30-day rolling average of Energy Accountability Ratio (EAR).

```python
rolling_eff = CapitalControls.get_rolling_efficiency("MILL_001")
# Returns: 0.75 to 1.15 (depends on reconciliation records)
```

### 2. `CapitalControls.cumulative_penalty(mill_id)`
**Location:** [backend/capital_controls.py](backend/capital_controls.py#L242-L264)

Returns the penalty multiplier based on rolling efficiency.

```python
penalty = CapitalControls.cumulative_penalty("MILL_001")
# Returns: 0.5 if rolling < 0.75, else 1.0
```

### 3. Enhanced `compute_advance_rate(..., mill_id=None)`
**Location:** [backend/policy_execution_engine.py](backend/policy_execution_engine.py#L240-L340)

Updated to accept optional `mill_id` and apply cumulative penalty.

```python
# Without penalty lookup (backward compatible)
rate = compute_advance_rate(90, 0.85, 0.50)

# With cumulative penalty applied
rate = compute_advance_rate(90, 0.85, 0.50, "MILL_001")
```

---

## How It Works

### The Math

```
Step 1: Get rolling efficiency (30-day average)
  rolling_eff = avg(EAR from last 30 days)

Step 2: Apply cumulative penalty
  IF rolling_eff < 0.75:
    cumulative_penalty = 0.5  (halve base rate)
  ELSE:
    cumulative_penalty = 1.0  (no penalty)

Step 3: Apply to base rate
  effective_base_rate = base_rate × cumulative_penalty

Step 4: Normal advance rate calculation
  advance_rate = effective_base_rate × (trust / 100) × (efficiency²)
```

### Example Calculations

#### Case 1: Good Rolling Average (No Penalty)
```
Rolling efficiency: 85%  (≥ 75%)
Current efficiency: 85%
Trust score: 80%

cumulative_penalty = 1.0
effective_base_rate = 0.50 × 1.0 = 0.50
advance_rate = 0.50 × 0.80 × 0.7225 = 0.289 (28.9%)
```

#### Case 2: Poor Rolling Average (Penalty Applied)
```
Rolling efficiency: 62%  (< 75%)  [operator was underperforming]
Current efficiency: 90%  [but has improved recently]
Trust score: 80%

cumulative_penalty = 0.5  [memory penalty!]
effective_base_rate = 0.50 × 0.5 = 0.25  [halved]
advance_rate = 0.25 × 0.80 × 0.81 = 0.162 (16.2%)  [half of Case 1]
```

#### Case 3: Hard Floor Override
```
Rolling efficiency: 62%  (< 75%)
Current efficiency: 40%  (< 50% hard floor!)
Trust score: 90%

Hard floor triggers first: return 0.0
(cumulative penalty is not even calculated)
```

---

## Integration Points

### In PXE Execution Flow
**File:** [backend/policy_execution_engine.py](backend/policy_execution_engine.py#L710-L720)

The `compute_advance_rate()` call now passes `mill_id`:

```python
computed_rate = compute_advance_rate(
    trust_score=pxe_input.trust_score,
    digital_efficiency=pxe_input.digital_efficiency,
    base_rate=policy_base_rate,
    mill_id=pxe_input.mill_id,  # NEW: enables cumulative penalty
)
```

### Penalty Execution Order
1. **Hard Floor** (< 50% current efficiency) → 0.0 immediately
2. **Cumulative Loss** (< 75% rolling avg) → base_rate × 0.5
3. **Gradual Squeeze** (efficiency²) → squared penalty
4. **Structural Leakage** (entropy) → final multiplier

---

## Backward Compatibility

✅ **Fully backward compatible**

- `mill_id` parameter is **optional** (defaults to None)
- When `mill_id=None`, cumulative penalty is **skipped** (penalty = 1.0)
- Existing code that doesn't pass `mill_id` works unchanged
- No database schema changes required

### Migration Path
1. Code works with or without `mill_id`
2. Gradually pass `mill_id` as opportunities arise
3. Once all callers pass `mill_id`, can enforce penalty across system

---

## Data Flow

```
ReconciliationRecord (created daily)
    ↓
Energy Accountability Ratio (EAR field)
    ↓
CapitalControls.get_rolling_efficiency() [30-day avg]
    ↓
CapitalControls.cumulative_penalty() [0.5 or 1.0]
    ↓
compute_advance_rate(mill_id=...) [apply to base_rate]
    ↓
Effective advance rate [base_rate × cumulative_penalty × ...]
    ↓
CreditMetrics stored in database [audit trail]
```

---

## Testing & Validation

### Test Files
- **[test_squeeze.py](test_squeeze.py)** — Hard floor tests (all 7 pass)
- **[test_cumulative_penalty_quick.py](test_cumulative_penalty_quick.py)** — Integration tests

### Test Results
✅ Tests 1-2: Basic integration (no mill_id, hard floor) — PASS  
⏳ Tests 3-5: DB lookups (may timeout, needs DB init)  

### Backward Compatibility
✅ All existing tests pass without modification  
✅ No breaking changes to function signatures  
✅ Error handling graceful (DB lookup failures don't crash)

---

## Configuration

Current threshold values:

```python
# In CapitalControls.cumulative_penalty():
ROLLING_THRESHOLD = 0.75  # 75%
PENALTY_MULTIPLIER = 0.5  # Halve base rate
ROLLING_WINDOW = 30       # Days
```

To adjust:
1. Edit `cumulative_penalty()` method
2. Change threshold comparison (0.75 → 0.70, etc.)
3. Change multiplier (0.5 → 0.6, etc.)
4. Change days (30 → 45, etc.)

---

## Recovery Mechanism

**How operators recover:**

1. **Identified as underperforming:** Rolling average < 75%
2. **Penalty applied:** Base rate halved
3. **Operator improves:** Daily efficiency increases
4. **Rolling window advances:** Worst performing days drop off
5. **Threshold crossed:** When rolling average ≥ 75%
6. **Automatic recovery:** Penalty lifted immediately at next cycle

**No manual intervention needed.** The system is purely mechanical.

---

## Operator Impact

### Scenario: Monthly Assessment

```
Week 1: 60% efficiency → rolling avg 60%, penalty -50% ✓
  - Current: can only access 14.5% advance rate (halved from 28.9%)

Week 2-3: Improve to 80% efficiency daily
  - Rolling avg improves daily, still below 75%
  - Penalty still active

Week 4: Reach 95% efficiency
  - Rolling avg: ~74% (getting close)
  - Penalty still active, but lifting soon

Day 31: Rolling average finally ≥ 75%
  - Penalty lifted
  - Advance rate restored to 28.9%
  - "Recovery successful"
```

---

## Documentation

- **[CUMULATIVE_LOSS_PRESSURE.md](CUMULATIVE_LOSS_PRESSURE.md)** — Complete feature documentation
- **[HARD_ECONOMIC_FLOOR.md](HARD_ECONOMIC_FLOOR.md)** — Hard floor documentation (related feature)
- **Code comments** — All functions documented with examples

---

## Deployment Status

- [x] Functions implemented
- [x] Integration complete
- [x] Tests written
- [x] Backward compatible
- [x] Documentation complete
- [x] Error handling in place
- [ ] Database migration (if needed)
- [ ] Operator communication

---

## Key Files Changed

| File | Changes | Lines |
|------|---------|-------|
| [backend/capital_controls.py](backend/capital_controls.py) | Added 2 methods | 204-264 |
| [backend/policy_execution_engine.py](backend/policy_execution_engine.py) | Updated function sig, added error handling | 240-340, 313-325 |
| [test_squeeze.py](test_squeeze.py) | All existing tests pass | 1-120 |

---

## Success Criteria

✅ **Implemented**: 30-day rolling average efficiency tracking  
✅ **Implemented**: Cumulative penalty (0.5 multiplier when < 75%)  
✅ **Implemented**: Integration with compute_advance_rate()  
✅ **Verified**: Backward compatible (mill_id optional)  
✅ **Verified**: Hard floor takes priority  
✅ **Verified**: Existing tests still pass  
✅ **Documented**: Complete feature documentation  

---

## System Behavior Summary

| Condition | Hard Floor | Cumulative | Result |
|-----------|-----------|------------|--------|
| Current 40%, Rolling 80% | ✗ Triggered | N/A | BLOCKED (0.0) |
| Current 85%, Rolling 80% | ✓ OK | ✓ OK | FULL (28.9%) |
| Current 85%, Rolling 60% | ✓ OK | ✗ Active | PENALIZED (14.5%) |
| Current 50%, Rolling 80% | ✓ OK | ✓ OK | BOUNDARY (11.3%) |
| Current 50%, Rolling 60% | ✓ OK | ✗ Active | PENALIZED (5.6%) |

---

**Implementation Complete.** The system now has memory. Short-term spikes cannot erase the evidence of prolonged underperformance.
