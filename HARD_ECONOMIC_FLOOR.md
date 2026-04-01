# Hard Economic Floor: Stop Funding Dysfunction

**Implementation Date:** March 30, 2026  
**Status:** ✅ DEPLOYED  
**Requirement:** Circuit breaker that halts capital flow when operator efficiency < 50%

---

## Executive Summary

When an operator's digital efficiency falls below 50%, capital advances **stop completely**. No exceptions. No trust-based overrides. This is a circuit breaker for protecting the system from theft and operational failure.

### Why?
Below 50% efficiency, the operator is either:
1. **Stealing from the system** (fraud), OR
2. **So operationally broken** that further capital is a pure loss

There is no third scenario. Capital protection demands a hard line.

---

## The Rule

```
IF digital_efficiency < 0.5:
    advance_rate = 0.0  (STOP—no debate)
ELSE:
    advance_rate = base_rate × (trust_score / 100) × (digital_efficiency²)
```

### Key Points
- **Efficiency = verified_deposits / expected_revenue**
- **Range:** 0.0 to 2.0 (normal: 0.8–1.2)
- **Threshold:** 50% (0.5)
- **Override capability:** NONE—trust cannot override

---

## Impact Examples

### ✅ Approved Cases

| Trust | Efficiency | Rate | Status |
|-------|-----------|------|--------|
| 90% | 100% | 45% | ✓ Full advance |
| 85% | 80% | 27.2% | ✓ Healthy margin |
| 80% | 50% | 10% | ✓ At boundary (permitted) |
| 70% | 51% | 10.4% | ✓ Just above floor |

### ❌ Blocked Cases

| Trust | Efficiency | Rate | Status |
|-------|-----------|------|--------|
| 99% | 49% | **0%** | ❌ Hard floor (no debate) |
| 95% | 30% | **0%** | ❌ Hard floor (no debate) |
| 100% | 0% | **0%** | ❌ Hard floor (no debate) |

**Critical observation:** Trust score of 99% **cannot override** 49% efficiency.

---

## Implementation Locations

### 1. Core Logic
**File:** `backend/policy_execution_engine.py` (Lines 241–290)
- Function: `compute_advance_rate()`
- Hard floor check: Lines 291–292

```python
# HARD ECONOMIC FLOOR: Stop funding dysfunction at 50% efficiency
if digital_efficiency < 0.5:
    return 0.0  # Circuit breaker—no advance, no exceptions
```

### 2. Execution Flow
**File:** `backend/policy_execution_engine.py` (Lines 674–689)
- Called in Step 4 of policy execution
- Applied to both APPROVE and CONDITIONAL decisions
- Precedes structural penalty multiplier

### 3. Test Coverage
**Files Updated:**
- `test_squeeze.py` (Tests 4–7)
- `test_gradual_squeeze.py` (Updated test cases)

**Tests:**
- ✅ Efficiency 40% → 0.0 (hard floor triggered)
- ✅ Efficiency 49% + 99% trust → 0.0 (trust irrelevant)
- ✅ Efficiency 50% → 10% (at boundary, permitted)
- ✅ Efficiency 51% → 10.4% (normal calculation)

---

## Operator Recovery Path

Once blocked by the hard floor (efficiency < 50%), the operator must:

1. **Diagnose:** Identify why reported revenue doesn't match deposits
2. **Correct:** Fix metering, reconciliation, or compliance issues
3. **Document:** Report remediation steps
4. **Recover:** Demonstrate 50%+ efficiency across 14-day rolling window
5. **Advance:** System automatically lifts hard floor when threshold exceeded

**No manual override available.** System enforces discipline automatically.

---

## System Behavior

### Execution Order (Priority)
1. **Hard Floor Check** ← Highest priority
2. Structural Penalty Multiplier
3. Auto-Adjustment (Third Authority)
4. Final CAO Emission

### Edge Cases

#### At Exactly 50%
```python
compute_advance_rate(80, 0.5)  # Returns 0.10 (permitted)
# Formula: 0.5 × 0.80 × (0.5²) = 0.5 × 0.80 × 0.25 = 0.10
```
Efficiency at exactly 50% **still advances capital** (boundary inclusive).

#### Negative Variance
If efficiency < 50% AND entropy monitor detects structural leakage:
- Hard floor triggers first (advance_rate = 0.0)
- Structural penalty would apply (0.0 × multiplier = 0.0)
- Result: doubly blocked

#### Recovery Across Observations
```
Day 1: Efficiency 45% → blocked
Day 2: Efficiency 55% → unlocked
Day 3: Efficiency 48% → blocked again
Day 4: Efficiency 52% → unlocked again
```
Each observation is **independently evaluated**.

---

## Monitoring & Alerts

### Red Flags (Efficiency Approaching Floor)
- Efficiency 55%–60%: Monitor closely
- Efficiency 50%–55%: Prepare audit
- Efficiency < 50%: **Automatic block**

### Recovery Window
- Hard floor triggered: T₀
- 14-day recovery period: T₀ to T₀+14
- If efficiency stays < 50%: Capital remains frozen
- If efficiency rises ≥ 50%: Capital resumes at next cycle

---

## Why This Matters

### Protection Against
1. **Revenue Fraud:** Operator reports deposits they didn't receive
2. **Metering Errors:** Systematic under-reporting (leakage)
3. **Operational Collapse:** System too broken to advance capital
4. **Moral Hazard:** "Trust me" cannot override hard evidence

### Enforces
- **Operator Accountability:** Performance determines capital access
- **System Discipline:** No discretionary exceptions
- **Fiduciary Duty:** Cannot lend to operators losing money

---

## Testing & Validation

### Unit Test Results
```
✅ Test 1: Perfect efficiency (100%)     → PASS
✅ Test 2: Good efficiency (80%)         → PASS
✅ Test 3: Fair efficiency (50%)         → PASS (boundary)
✅ Test 4: Poor efficiency (40%)         → PASS (hard floor)
✅ Test 5: Edge case (49% + 99% trust)   → PASS
✅ Test 6: Boundary (exactly 50%)        → PASS
✅ Test 7: Recovery (51%)                → PASS
```

### Integration Test Status
- ✅ PXE execution flow
- ✅ Structural penalty interaction
- ✅ Auto-adjustment compatibility
- ✅ CAO emission validation

---

## Changelog

| Date | Change | Impact |
|------|--------|--------|
| 2026-03-30 | Hard floor implemented | Efficiency < 50% → zero advance |
| 2026-03-30 | Test suite updated | 7 tests covering hard floor behavior |
| 2026-03-30 | Documentation complete | Operator and internal specs ready |

---

## Questions & Clarifications

**Q: Can an operator appeal the hard floor?**  
A: No. The system is mechanical. Operator must improve efficiency.

**Q: Does trust score override the floor?**  
A: No. Trust modulates the advance rate *above* 50% efficiency. Below 50% is a circuit breaker.

**Q: What triggers recovery?**  
A: Any 14-day rolling window where efficiency ≥ 50%.

**Q: Can we temporarily waive the hard floor?**  
A: No. The hard floor is a system invariant, not a policy setting.

---

## Related Documents
- [ARCHITECTURE.md](ARCHITECTURE.md) — System design overview
- [test_squeeze.py](test_squeeze.py) — Hard floor test cases
- [backend/policy_execution_engine.py](backend/policy_execution_engine.py) — Implementation
