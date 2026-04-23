# Turnover Time (TT) Penalty Implementation - Pilot Deployment Guide

**Status**: ✅ Backend implementation complete and verified  
**Commit**: `3d6af9e` - backend: integrate TT penalty into advance rate calculation  
**Date**: April 23, 2026

---

## Executive Summary

The Turnover Time (TT) penalty system is now active in the backend. It measures cycle velocity (time from capital allocation to cash receipt) and applies dynamic penalties/bonuses to advance rates:

| Classification | Lag Range | Multiplier | Business Impact |
|---|---|---|---|
| **FAST** | < 24h | 1.05× | 5% bonus for rapid velocity |
| **NORMAL** | 24–48h | 1.0× | Standard commercial terms |
| **SLOW** | 48–72h | 0.95× | 5% penalty, pattern monitoring |
| **STALLED** | ≥ 72h | 0.0× | **BLOCKED next cycle** |

---

## Implementation Details

### Core Functions (backend/policy_execution_engine.py)

#### `classify_turnover_time(lag_hours: float) → str`
Classifies cycle latency into TT categories based on hours from allocation to cash receipt.

```python
classify_turnover_time(12.0)   # "FAST"
classify_turnover_time(36.0)   # "NORMAL"
classify_turnover_time(60.0)   # "SLOW"
classify_turnover_time(96.0)   # "STALLED"
```

#### `turnover_penalty(turnover_classification: str) → float`
Returns penalty/bonus multiplier for advance rate calculation.

```python
turnover_penalty("FAST")      # 1.05
turnover_penalty("NORMAL")    # 1.0
turnover_penalty("SLOW")      # 0.95
turnover_penalty("STALLED")   # 0.0  ← COMPLETE BLOCK
```

#### `compute_per_cycle_advance_rate(..., turnover_classification: str)`
Updated formula:
```
advance_rate = base_rate × (trust/100) × (adherence²) × latency_penalty × TT_multiplier

Examples:
- FAST (12h, trust=90%, adherence=95%):
  0.5 × 0.90 × 0.9025 × 1.0 × 1.05 = 0.426
  
- STALLED (96h, trust=90%, adherence=95%):
  0.5 × 0.90 × 0.9025 × 0.85 × 0.0 = 0.0 (BLOCKED)
```

### Integration Points

#### 1. **cycle_manager.py** - `evaluate_mill_capital()`
```python
# Classify turnover time from last cycle's lag
turnover_classification = classify_turnover_time(lag_hours)

# Pass to rate computation
rate = compute_per_cycle_advance_rate(
    trust_score=trust_score,
    adherence=adherence,
    lag_hours=lag_hours,
    base_rate=BASE_ADVANCE_RATE,
    turnover_classification=turnover_classification  # ← NEW
)
```

#### 2. **owner_routes.py** - Token allocation decision
```python
# In _compute_allocation_size() and decision basis building
turnover_classification = classify_turnover_time(lag_hours)

advance_rate = compute_per_cycle_advance_rate(
    trust_score=trust_score,
    adherence=adherence,
    lag_hours=lag_hours,
    turnover_classification=turnover_classification  # ← NEW
)
```

---

## Verification Results

### Test: quick_test_tt.py ✅
```
✓ Classification Tests:
  12h (FAST):    FAST
  36h (NORMAL):  NORMAL
  60h (SLOW):    SLOW
  96h (STALLED): STALLED

✓ Penalty Multipliers:
  FAST:    1.05
  NORMAL:  1.0
  SLOW:    0.95
  STALLED: 0.0

✓ Advance Rate Calculations (trust=90%, adherence=95%):
  FAST (12h):    0.426431  ← boosted
  NORMAL (36h):  0.385819  ← standard
  SLOW (60h):    0.347237  ← penalized
  STALLED (96h): 0.000000  ← BLOCKED

✅ ALL TESTS PASSED
```

---

## Pilot Deployment Checklist

### Phase 1: Nabiwi (Baseline Mill)

- [ ] **Activate TT penalty** for Nabiwi token allocations
  - Monitor: NORMAL cycles (24-48h) should be standard
  - Verify: Previous FAST cycles get 5% boost
  
- [ ] **Log first 5 cycles** with TT classifications
  - Capture: lag_hours, classification, advance_rate (before/after TT)
  - Expected: All cycles < 48h (should be FAST or NORMAL)
  
- [ ] **Verify BLOCKED state doesn't occur** (healthy operations)
  - Verify: No STALLED classifications (lag ≥ 72h)
  - If any STALLED: Escalate to operations for review

### Phase 2: Secondary Mill (TBD)

- [ ] Deploy TT penalty to second mill (select mill with recent rate changes)
  
- [ ] **Comparative analysis**: Nabiwi vs Secondary
  - Track: Allocation patterns, rate changes, cycle latency trends
  - Document: Any differences in TT distribution
  
- [ ] **Stress test** if mill has historical latency issues
  - If any SLOW/STALLED: Verify BLOCKED state is correctly applied
  - Verify: Next cycle allocation = 0 kWh (or appropriate reduced amount)

### Phase 3: Cross-check with Frontend

- [ ] **Verify UI displays match backend calculations**
  - CycleVelocityPanel shows correct classifications
  - EnforcementPanel shows turnover status for last cycle
  - ReconciliationTimeline displays TT badges

- [ ] **Test BLOCKED → NORMAL recovery flow**
  - Simulate: Mill with STALLED cycle
  - Next cycle: Verify allocation status transitions correctly
  - UI: Verify no "ghost" allocations from stalled state

---

## Monitoring During Pilot

### Daily Checks

```sql
-- Query 1: Last 10 cycles per mill - lag and classification
SELECT 
  mill_id, 
  allocated_at, 
  received_at,
  EXTRACT(EPOCH FROM (received_at - allocated_at)) / 3600 AS lag_hours,
  CASE 
    WHEN lag_hours < 24 THEN 'FAST'
    WHEN lag_hours < 48 THEN 'NORMAL'
    WHEN lag_hours < 72 THEN 'SLOW'
    ELSE 'STALLED'
  END AS classification
FROM token_allocations
ORDER BY mill_id, allocated_at DESC
LIMIT 20;

-- Query 2: Any STALLED allocations this week?
SELECT COUNT(*) as stalled_count
FROM token_allocations
WHERE status IN ('CLOSED', 'DISPUTED')
  AND (received_at - allocated_at) >= INTERVAL '72 hours';
```

### Expected Behavior

| Scenario | Expected Outcome | Verification |
|---|---|---|
| Healthy mill (24h cycle) | NORMAL classification, standard rate | `advance_rate = 0.5 × ... × 1.0` |
| Fast mill (12h cycle) | FAST classification, boosted rate | `advance_rate = 0.5 × ... × 1.05` |
| Slow mill (60h cycle) | SLOW classification, penalized | `advance_rate = 0.5 × ... × 0.95` |
| Stalled mill (96h cycle) | STALLED classification, **blocked** | `advance_rate = 0.0` → next allocation = 0 kWh |

---

## API Endpoints Affected

### GET `/api/owner/mills/{mill_id}/status`
Now includes turnover classification in decision basis.

**Response** (updated):
```json
{
  "mill_id": "NABIWI_01",
  "last_cycle_lag_hours": 36.5,
  "next_advance_rate": 0.385819,
  "decision_basis": {
    "last_cycle_lag_hours": 36.5,
    "next_advance_rate": 0.385819
    // TT penalty already applied in advance_rate
  }
}
```

### GET `/api/owner/mills/{mill_id}/allocations/next`
Allocation blocked if last cycle was STALLED.

**Response when STALLED**:
```json
{
  "status": "BLOCKED",
  "reason": "Last cycle STALLED (96h lag) - no token allocation",
  "advance_rate": 0.0,
  "simulated_allocation_kwh": 0.0
}
```

---

## Rollback Plan (If Issues Arise)

### Quick Disable (Non-disruptive)

```python
# In policy_execution_engine.py, function compute_per_cycle_advance_rate()
# Temporarily comment out TT penalty:

# factor_turnover = turnover_penalty(turnover_classification)
factor_turnover = 1.0  # Disable TT penalty (revert to pre-TT behavior)

effective_rate = base_rate * factor_trust * factor_adherence * factor_latency * factor_turnover
```

### Full Revert (If needed)
```bash
git revert 3d6af9e  # Revert commit containing TT penalty
```

---

## Success Criteria

### Pilot Success = All of:

1. ✅ **No STALLED allocations blocked incorrectly**
   - Any STALLED must be operational issue (not system bug)
   - Blocked state correctly prevents next token allocation

2. ✅ **Rate calculations match expected formulas**
   - FAST cycles: +5% boost verified
   - SLOW cycles: -5% penalty verified
   - STALLED cycles: 0.0 rate verified

3. ✅ **UI matches backend classifications**
   - CycleVelocityPanel displays correct TT labels
   - EnforcementPanel shows turnover status correctly

4. ✅ **No performance degradation**
   - Token allocation endpoint response time < 500ms
   - Rate calculation queries execute in < 10ms

5. ✅ **Audit trail complete**
   - All TT classifications logged
   - Decision basis records include turnover factor
   - API responses track rate changes

---

## Post-Pilot Actions

### Week 1 (April 30, 2026)
- [ ] Analyze 20-30 cycles from both mills
- [ ] Verify no unintended BLOCKED states
- [ ] Confirm rate calculations match expectations
- [ ] Document any operational insights

### Week 2 (May 7, 2026)
- [ ] If successful: Deploy to all mills
- [ ] If issues: Investigate and fix, then re-pilot
- [ ] Update documentation based on findings

### Production Deployment (Target: May 15, 2026)
- [ ] TT penalty active for all mills
- [ ] Monitoring dashboards updated
- [ ] Operator communications sent (explaining STALLED blocks)

---

## Questions for Pilot Phase

**For Nabiwi operator**:
1. Have you experienced any cycles > 48h in the past 30 days?
2. Are there operational reasons for delays beyond 24h?
3. What's your typical payment processing time?

**For system monitoring**:
1. Are there any SLOW cycles that should escalate to BLOCKED?
2. Is the 72h STALLED threshold appropriate for your mills?
3. Should we adjust FAST threshold (currently < 24h)?

---

## Technical Notes

### Why STALLED = Complete Block (0.0×)?

The 72-hour threshold (3 days) represents a hard boundary for capital velocity:

- **Under 48h**: Acceptable commercial terms (NORMAL rate)
- **48-72h**: Concerning pattern (SLOW rate, monitor)
- **72h+**: Operational failure or fraud (STALLED = BLOCKED)

A 3-day cycle means capital is held excessively long. Blocking the next token creates immediate economic pressure to fix the issue:

```
Cycle 1 (STALLED, 96h)
  ↓
Advance rate = 0.0 (calculated but not allocated yet)
  ↓
Operator must fix underlying issue before next token
  ↓
Cycle 2 (FAST/NORMAL, <48h)
  ↓
Advance rate = normal/boosted (recovery possible)
```

### Edge Cases Handled

1. **First cycle (no history)**
   - classify_turnover_time() defaults to "NORMAL" if no lag data
   - No penalty/bonus applied on first allocation

2. **Very fast cycles (< 1h)**
   - Still classified as "FAST"
   - Multiplier = 1.05× (bonus still applied)
   - Could indicate same-day settlement (positive signal)

3. **Disputed cycles**
   - lag_hours calculated from allocation to dispute raised
   - SLOW/STALLED penalties apply to adherence, not classification
   - TT penalty independent (both factors considered)

---

**Status**: Ready for Nabiwi + 1 secondary mill pilot deployment
