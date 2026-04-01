# Kill the Floor Surfers - Quick Reference

## One-Liner

**Three-zone efficiency system**: < 50% = blocked, 50–65% = 25% rate, ≥ 65% = normal rate.

---

## Core Rules

| Efficiency | Zone | Action | Rate |
|-----------|------|--------|------|
| < 50% | Death | Block entirely | $0 |
| 50–65% | Starvation | 25% of normal | ~$0.03-0.05 |
| ≥ 65% | Normal | Full calculation | 0.15–0.48 |

---

## Quick Formula

```
if efficiency < 0.50:
    return 0.0

if efficiency < 0.65:
    multiplier = 0.25  # Starvation zone
else:
    multiplier = 1.0   # Normal zone

rate = base × (trust/100) × (efficiency²) × multiplier
```

---

## Key Numbers

- **Death threshold**: 50%
- **Starvation escape**: 65% (4× rate improvement)
- **Starvation multiplier**: 0.25 (75% reduction)
- **Monthly revenue loss** (55%, $10k capital): ~$475

---

## Why 65%?

At 65%, rate jumps from ~$0.044 to ~$0.190 (4.3×).

This discontinuity is intentional—creates strong incentive to cross threshold.

---

## Economic Reality

| Efficiency | Monthly Revenue | Monthly Cost | Status |
|-----------|-----------------|-------------|--------|
| 55% | $25 | $500 | 🔴 Unsustainable |
| 60% | $30 | $500 | 🔴 Unsustainable |
| 65% | $141 | $500 | 🟡 Still tough |
| 75% | $188 | $500 | 🟡 Marginal |

**Implication**: Starvation zone forces operators to exit or improve within weeks.

---

## Stacking Examples

**Starvation + Cumulative Loss** (58% + rolling 65%):
```
Starvation: ×0.25
Cumulative: ×0.5
Combined: ×0.125 (87.5% reduction)
```

**Starvation + Suspicion** (60% + score 6.0):
```
Starvation: ×0.25
Suspicion: ×0.8
Combined: ×0.20 (80% reduction)
```

---

## Test Results

✅ All 10 tests passing:
- Death zone (< 50%) blocks entirely
- Starvation zone (50–65%) applies 0.25
- Normal zone (≥ 65%) full rate
- Boundaries precise (50%, 65%)
- Economic impact verified

---

## Code Location

**File**: `backend/policy_execution_engine.py`  
**Function**: `compute_advance_rate()`  
**Lines**: ~241-350  

---

## Implementation Impact

- **New**: `if 0.5 <= digital_efficiency < 0.65: starvation_mult = 0.25`
- **Maintains**: Hard floor (< 50% = blocked)
- **Integrates**: With cumulative loss and suspicion penalties
- **Result**: Four-layer penalty stack

---

## Operator Actions

**In Starvation (50–65%)**:
1. Accept unsustainable economics, OR
2. Invest in operational improvement, OR
3. Exit system

**Typical Timeline**: Decision within 3-6 months (capital runs out)

**Best Outcome**: Improve to 65%+ (revenue 4-5× improvement)

---

## Key Files

- [KILL_THE_FLOOR_SURFERS.md](KILL_THE_FLOOR_SURFERS.md) - Full documentation
- [test_starvation_zone.py](test_starvation_zone.py) - 10 comprehensive tests
- [ARCHITECTURE.md](ARCHITECTURE.md) - Four-layer system overview

---

## Why This Matters

**Before**: 50.1% efficiency = same capital as 50.0% (cliff edge)  
**After**: 50–65% faces 75% penalty (graduated pressure)  
**Result**: Operators can't camp in mediocrity—must climb or exit

---

## Safety Notes

- Hard floor (< 50%) unchanged—absolute circuit breaker
- Starvation zone multiplier (0.25) is fixed, not discretionary
- Works with all other penalties (independent, stacks multiplicatively)
- Mathematically precise at boundaries (50% and 65%)

