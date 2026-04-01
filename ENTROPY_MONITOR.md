# Entropy Monitor: Structural Leakage Detection

**Implementation Date:** March 30, 2026  
**Status:** ✅ Production Ready  
**Integration:** revenue_engine.py + policy_execution_engine.py  

---

## Overview

The **Entropy Monitor** detects structural revenue leakage through consistent under-reporting patterns. It works in tandem with **Gradual Squeeze** to suppress dishonest operators while maintaining incentive for improvement.

---

## Core Principle

**Structural Leakage Detection Formula:**

1. **Record variance**: actual_revenue - expected_revenue (daily)
2. **Capture sign**: Negative (-1) for under-reporting, Positive (+1) for over-reporting
3. **Check pattern**: All signs negative in rolling window → structural leakage
4. **Apply penalty**: 0.9× multiplier (10% reduction to advance rate)

---

## Architecture

### Data Model

```python
@dataclass
class VarianceRecord:
    date: str          # ISO-8601 date
    variance: float    # actual - expected (negative = under-reporting)
    variance_sign: int # -1 or +1
```

### EntropyMonitor Class

**Location:** `backend/revenue_engine.py`

```python
class EntropyMonitor:
    def __init__(self, mill_id: str, window_days: int = 7):
        """Initialize monitor with rolling window (default: 7 days)"""
    
    def record_variance(self, date: str, variance: float) -> None:
        """Record daily revenue variance"""
    
    def is_structural_leakage(self) -> bool:
        """Detect if all signs in window are negative"""
    
    def get_penalty_multiplier(self, applying_penalty: bool = True) -> float:
        """Return 0.9 if leakage, else 1.0"""
    
    def get_leakage_status(self) -> Dict:
        """Return detailed diagnostics"""
```

---

## How It Works

### Example: 7-Day Pattern

#### Scenario A: All Negative (Structural Leakage)

```
Day 1: actual=Mk5,200  expected=Mk5,500  → variance=-300  (sign=-1)
Day 2: actual=Mk5,350  expected=Mk5,500  → variance=-150  (sign=-1)
Day 3: actual=Mk5,000  expected=Mk5,500  → variance=-500  (sign=-1)
Day 4: actual=Mk5,100  expected=Mk5,500  → variance=-400  (sign=-1)
Day 5: actual=Mk5,200  expected=Mk5,500  → variance=-300  (sign=-1)
Day 6: actual=Mk5,150  expected=Mk5,500  → variance=-350  (sign=-1)
Day 7: actual=Mk5,050  expected=Mk5,500  → variance=-450  (sign=-1)

Window Status:
  Negative Count: 7/7
  Leakage: TRUE ✗
  Penalty Multiplier: 0.9 (10% reduction)
```

**Interpretation**: Operator consistently under-reporting revenue across all 7 days. Likely holding cash informally rather than depositing digitally.

#### Scenario B: Mixed Variance (No Leakage)

```
Day 1: variance=-300  (sign=-1)
Day 2: variance=+200  (sign=+1)  ← Positive!
Day 3: variance=-150  (sign=-1)
Day 4: variance=+100  (sign=+1)  ← Positive!
Day 5: variance=-200  (sign=-1)
Day 6: variance=+50   (sign=+1)  ← Positive!
Day 7: variance=-400  (sign=-1)

Window Status:
  Negative Count: 5/7 (not all)
  Leakage: FALSE ✓
  Penalty Multiplier: 1.0 (no penalty)
```

**Interpretation**: Mixed pattern suggests operational volatility, not structural dishonesty. Variance is temporary fluctuation, not systematic under-reporting.

---

## Integration with PXE

### Data Flow

```
Revenue Engine
    ↓
Calculate variance = actual_revenue - expected_revenue
    ↓
EntropyMonitor.record_variance(date, variance)
    ↓
is_structural_leakage? Check pattern
    ↓
structural_penalty = 0.9 if leakage else 1.0
    ↓
PXEInput(structural_penalty_multiplier=0.9)
    ↓
PolicyExecutionEngine.execute()
    ↓
Step 4b: Apply penalty
final_rate = computed_rate × structural_penalty_multiplier
```

### PXE Integration Code

**In policy_execution_engine.py:**

```python
# Step 4: Gradual Squeeze
computed_rate = compute_advance_rate(trust, digital_efficiency, base_rate)
merged_actions["advance_rate"] = computed_rate

# Step 4b: Entropy Monitor Penalty
if merged_actions["credit_decision"] in [APPROVE, CONDITIONAL]:
    penalty = pxe_input.structural_penalty_multiplier
    final_rate = computed_rate × penalty
    merged_actions["advance_rate"] = final_rate
```

---

## Example: Complete Penalty Chain

**Scenario:** Mill with structural leakage

```
Input Parameters:
  Digital Efficiency: 85%
  Trust Score: 85
  Policy Base Rate: 50%
  Structural Leakage: YES (all 7 days negative)

Penalty Calculation:
  Step 1. Base Rate = 50%
  Step 2. Gradual Squeeze = 50% × (85/100) × (0.85²) = 30.7%
  Step 3. Entropy Penalty = 30.7% × 0.9 = 27.6%
  
Final Advance Rate: 27.6% (down from 50%)
```

**Impact on Capital Disbursement:**

```
Expected Revenue: Mk 5,535,000
Advance Rate: 27.6%
Disbursement: Mk 5,535,000 × 27.6% = Mk 1,527,660

Without Entropy Penalty (30.7%):
Disbursement would be: Mk 1,695,045 (+Mk 167,385)
```

The entropy penalty suppresses dishonest operator by **Mk 167,385** (10% reduction).

---

## Recovery Mechanism

An operator under structural leakage can recover by improving digital collection:

### Week 1 (Leakage Phase)
```
Days 1-7: All negative variance
Penalty: 0.9× (10% reduction)
```

### Week 2 (Recovery Phase)
```
Days 8-14: New window includes positive variances
If ANY positive variance detected → leakage cleared
Penalty: 1.0× (no penalty)
```

**Key Insight**: Recovery is immediate once pattern breaks. Incentivizes fast behavioral change.

---

## Implementation Details

### VarianceRecord Dataclass

```python
@dataclass
class VarianceRecord:
    date: str              # When variance occurred
    variance: float        # $ amount (negative = under)
    variance_sign: int    # 1 or -1 (computed from variance)
```

### Window Management

- **Default window:** 7 days
- **Configurable:** Can be 3, 7, 14, 30 days depending on policy
- **Rolling:** Oldest record drops when new one added beyond window size
- **Minimum:** Requires full window of negative to detect (no false positives)

### Status Diagnostics

```python
monitor.get_leakage_status() → {
    "mill_id": "NABIWI_MKWINDA",
    "structural_leakage": True,
    "window_days": 7,
    "records_in_window": 7,
    "negative_count": 7,
    "leakage_percentage": 100.0,
    "penalty_multiplier": 0.9,
    "variance_history": [
        {"date": "2026-03-24", "variance": -300, "sign": "UNDER"},
        ...
    ]
}
```

---

## Test Coverage

### Test 1: Entropy Monitor Basics ✅
- Initialize monitor
- Verify no leakage with empty window
- Check default penalty = 1.0

### Test 2: Positive Variance ✅
- Record 7 days of positive variance (over-reporting)
- Verify NOT flagged as leakage
- Penalty remains 1.0

### Test 3: Negative Variance ✅
- Record 7 days of negative variance (under-reporting)
- Verify structural leakage detected
- Penalty applied: 0.9

### Test 4: Mixed Variance ✅
- Record mixture of positive and negative
- Verify NOT flagged as leakage
- Penalty remains 1.0

### Test 5: Rolling Window ✅
- Add records beyond window size
- Verify oldest records drop
- Window size maintained

### Test 6: Penalty Chain ✅
- Verify penalty multiplies with Gradual Squeeze
- 40% × 0.9 = 36%

### Test 7: Status Output ✅
- Detailed diagnostics
- Variance history
- Complete auditability

### Integration Test ✅
- Squeeze + Entropy together
- Recovery scenario
- Advanced scenarios

---

## Operational Behavior

### Dishonest Operator Under Leakage

```
Week 1:
  Daily variance: -300, -250, -280, -320, -290, -310, -300
  Pattern: Consistently under-reporting
  Detection: Structural leakage TRUE
  Penalty: 10%
  
Week 2 (no change):
  Daily variance: -280, -270, -310, -290, -300, -320, -310
  Pattern: Still consistent under-reporting
  Detection: Structural leakage TRUE
  Penalty: 10%
  
Result: Operator remains constrained until behavior changes
```

### Honest Operator with Volatility

```
Week 1:
  Daily variance: -50, +100, -80, +120, -30, +90, -60
  Pattern: Mixed (volatility, not structure)
  Detection: Structural leakage FALSE
  Penalty: None
  
Week 2:
  Daily variance: +200, +150, +180, +160, +190, +170, +185
  Pattern: Positive trend
  Detection: Structural leakage FALSE
  Penalty: None
  
Result: Operator remains at approved advance rate
```

---

## Configuration

### Per-Mill Customization

```python
# Standard (7-day window)
monitor = EntropyMonitor("NABIWI_MKWINDA", window_days=7)

# Aggressive monitoring (3-day window)
monitor = EntropyMonitor("RISKY_MILL", window_days=3)

# Long-term tracking (30-day window)
monitor = EntropyMonitor("STABLE_MILL", window_days=30)
```

### Penalty Customization

```python
class EntropyMonitor:
    def __init__(self, ...):
        self.penalty_multiplier_value = 0.9  # 10% reduction
        # Can adjust if needed: 0.85 (15%), 0.80 (20%), etc.
```

---

## Audit Trail

### CAO Integration

1. **PXEInput field**: `structural_penalty_multiplier` included in input hash
2. **Execution trace**: Penalty multiplier recorded
3. **Capital ledger**: Final advance rate reflects penalty
4. **Diagnosis**: `get_leakage_status()` provides full history

Example CAO:

```json
{
  "mill_id": "NABIWI_MKWINDA",
  "advance_rate": 0.276,
  "input_hash": "sha256(...structural_penalty_multiplier=0.9...)",
  "execution_trace": {
    "structural_penalty_applied": true,
    "leakage_detection": "STRUCTURAL",
    "window_days": 7,
    "negative_percentage": 100.0
  }
}
```

---

## Performance

- **Computation**: O(D) where D = window_days (linear scan)
- **Storage**: D records per mill (~1KB per 7-day window)
- **Latency**: < 1ms to record variance and check leakage
- **Scalability**: Practical for 10,000+ mills (rolling windows bounded)

---

## Compliance

- ✅ Deterministic (identical variance → identical detection)
- ✅ Transparent (algorithm publicly documented)
- ✅ Auditable (included in CAO hash and ledger)
- ✅ Non-arbitrary (threshold is mathematical, not subjective)
- ✅ Reversible (operators can improve and recover)

---

## Status Summary

| Component | Status | Notes |
|---|---|---|
| VarianceRecord dataclass | ✅ Implemented | Immutable record |
| EntropyMonitor class | ✅ Implemented | Full functionality |
| RevenueGateway integration | ✅ Implemented | Per-mill monitors |
| PXEInput extension | ✅ Implemented | structural_penalty_multiplier field |
| PXE integration | ✅ Implemented | Step 4b in execute flow |
| Unit tests | ✅ Complete | 7 test suites (all pass) |
| Integration tests | ✅ Complete | Squeeze + Entropy working together |
| Documentation | ✅ Complete | This document |

---

**Status**: ✅ Ready for Production

**Last Updated:** March 30, 2026 / 04:30 UTC
