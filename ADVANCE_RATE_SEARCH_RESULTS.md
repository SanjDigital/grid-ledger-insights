# Gridledger Advance Rate Implementation - Complete Search Results

**Date:** March 30, 2026  
**Scope:** Analysis of `compute_advance_rate()`, digital_efficiency metrics, and threshold implementations

---

## 1. COMPUTE_ADVANCE_RATE FUNCTION

**File Path:** [backend/policy_execution_engine.py](backend/policy_execution_engine.py#L241)  
**Lines:** [241-290](backend/policy_execution_engine.py#L241-L290)

### Function Signature
```python
def compute_advance_rate(
    trust_score: float,
    digital_efficiency: float,
    base_rate: float = 0.5
) -> float:
```

### Full Implementation
```python
def compute_advance_rate(
    trust_score: float,
    digital_efficiency: float,
    base_rate: float = 0.5
) -> float:
    """
    Compute advance rate with squared digital efficiency penalty.
    
    Implements "Gradual Squeeze" mechanism:
    - Higher digital_efficiency → higher advance rate
    - Lower digital_efficiency → rapidly penalized (squared)
    - Trust score modulates the effective rate
    
    Formula:
        advance_rate = base_rate × (trust_score / 100.0) × (digital_efficiency²)
    
    Args:
        trust_score: Operator integrity score (0-100)
        digital_efficiency: Ratio of verified_deposit to expected_revenue
                          = actual_revenue / expected_revenue (0.0 - 2.0)
        base_rate: Maximum achievable advance rate (default: 0.5 = 50%)
    
    Returns:
        Advance rate (0.0 – base_rate)
    
    Examples:
        # Perfect efficiency, high trust
        compute_advance_rate(90.0, 1.0, 0.50) → 0.45
        
        # Lower efficiency drops quickly (squared penalty)
        compute_advance_rate(90.0, 0.8, 0.50) → 0.288  (not 0.36)
        
        # Zero efficiency → zero advance
        compute_advance_rate(90.0, 0.0, 0.50) → 0.0
        
        # Split efficiency (50%)
        compute_advance_rate(80.0, 0.5, 0.50) → 0.10  (base × 0.8 × 0.25)
    """
    if digital_efficiency <= 0.0:
        return 0.0
    
    # Squared penalty on efficiency: drops fast at low efficiency
    efficiency_factor = digital_efficiency ** 2
    
    # Scale by trust score and apply base rate
    effective_rate = base_rate * (trust_score / 100.0) * efficiency_factor
    
    # Clamp to valid range [0.0, base_rate]
    return min(base_rate, max(0.0, effective_rate))
```

### Key Features
- **Non-linear penalty:** Uses squared efficiency factor `digital_efficiency²` for rapid degradation at low efficiency
- **Three-factor model:** `base_rate × (trust_score/100) × (digital_efficiency²)`
- **Default base_rate:** 0.5 (50%)
- **Bounds:** Returns value in range `[0.0, base_rate]`
- **Zero handling:** Returns 0.0 if `digital_efficiency <= 0.0`

---

## 2. DIGITAL_EFFICIENCY METRICS

**Definition:** Ratio of verified deposits to expected revenue  
**Formula:** `digital_efficiency = verified_deposit / expected_revenue` or `actual_revenue / expected_revenue`  
**Range:** 0.0 to 2.0 (allows for over-reporting detection)  
**Type:** Gradual Squeeze input parameter

### Where Digital Efficiency Comes From

#### In the Revenue Engine
**File:** [backend/revenue_engine.py](backend/revenue_engine.py#L200)

```python
@staticmethod
def compute_efficiency(actual_revenue: float, expected_revenue: float) -> float:
    """
    Compute revenue efficiency ratio.
    
    Formula: efficiency = actual_revenue / expected_revenue
    
    - 1.0 = perfect match (operator reported truthfully)
    - < 1.0 = under-reporting (operator hiding revenue)
    - > 1.0 = over-reporting (impossible, unless meter fault)
    """
    if expected_revenue <= 0:
        raise ValueError(f"Expected revenue must be > 0, got {expected_revenue}")
    
    return actual_revenue / expected_revenue
```

#### Expected Revenue Computation
```python
@staticmethod
def compute_expected_revenue(verified_kwh: float, budgeted_rate: float) -> float:
    """
    Compute expected revenue.
    
    Formula: expected_revenue = verified_kwh × budgeted_rate
    """
    if verified_kwh < 0 or budgeted_rate < 0:
        raise ValueError(f"Invalid inputs: kwh={verified_kwh}, rate={budgeted_rate}")
    return verified_kwh * budgeted_rate
```

### In Policy Execution Engine (PXE)
**File:** [backend/policy_execution_engine.py](backend/policy_execution_engine.py#L195-L199)

**Field Definition in PXEInput:**
```python
# Gradual Squeeze Input (default: perfect efficiency)
digital_efficiency: float = 1.0  # verified_deposit / expected_revenue (0-2.0)
```

**Validation Constraint:**
```python
if not (0 <= self.digital_efficiency <= 2.0):
    errors.append("digital_efficiency must be 0-2.0 (verified_deposit / expected_revenue)")
```

### Usage in PXE Execution
**File:** [backend/policy_execution_engine.py](backend/policy_execution_engine.py#L661-L671)

```python
# Override policy base_rate with compute_advance_rate using digital_efficiency
computed_rate = compute_advance_rate(
    trust_score=pxe_input.trust_score,
    digital_efficiency=pxe_input.digital_efficiency,
    base_rate=policy_actions.get("advance_rate", 0.5),
)
```

### Impact Examples (with base_rate=0.50, trust_score=90)
| Digital Efficiency | Efficiency Factor | Result | Impact |
|---|---|---|---|
| 1.0 (100%) | 1.0² = 1.0 | 0.45 (45%) | Full advance rate |
| 0.8 (80%) | 0.8² = 0.64 | 0.288 (28.8%) | -36% penalty |
| 0.5 (50%) | 0.5² = 0.25 | 0.1125 (11.25%) | -75% penalty |
| 0.3 (30%) | 0.3² = 0.09 | 0.0405 (4.05%) | -91% penalty |
| 0.0 (0%) | 0.0² = 0.0 | 0.0 (0%) | FROZEN |

---

## 3. CAPITAL_AT_RISK.PY IMPLEMENTATION

**File Path:** [backend/capital_at_risk.py](backend/capital_at_risk.py)

### Default Capital Control Parameters
```python
DEFAULT_CASH_SWEEP_PRIORITY = 0.9  # Sweep 90% of incoming revenue
DEFAULT_PENALTY_RATE_BPS = 500     # +500 basis points (+5%)
DEFAULT_CREDIT_COMPRESSION_RATE = 1.0  # Compress to zero immediately
```

### State Transition Capital Controls

**Main Entry Point:**
```python
def handle_state_transition(
    cls,
    mill_id: str,
    old_state: str,
    new_state: str,
    breach_reason: str,
) -> List[Dict]:
    """
    Trigger capital control actions when mill enters BREACH/COMPROMISED/SUSPENDED state.
    
    Actions (escalated by severity):
    - SUSPENDED: cash_sweep + credit_compression + pricing_escalation
    - COMPROMISED: cash_sweep + pricing_escalation
    - BREACH: handled via credit tier downgrade in DCE module
    """
```

### Capital Control Actions

1. **CASH_SWEEP:** Redirect 90% of incoming revenue to reduce exposure
2. **CREDIT_COMPRESSION:** Set remaining credit to zero
3. **PRICING_ESCALATION:** Apply +500 bps penalty rate to outstanding balance

---

## 4. REVENUE_ENGINE.PY IMPLEMENTATION

**File Path:** [backend/revenue_engine.py](backend/revenue_engine.py)

### Core Revenue Truth Functions

#### Revenue Snapshot with Efficiency Calculation
```python
@dataclass
class RevenueSnapshot:
    """Immutable revenue computation snapshot."""
    mill_id: str
    timestamp: str
    verified_kwh: float
    budgeted_rate_per_kwh: float
    expected_revenue: float
    actual_revenue: float
    revenue_efficiency_ratio: float  # actual / expected
```

#### Expected Revenue Formula
```python
expected_revenue = verified_kwh × budgeted_rate_per_kwh
```

#### Efficiency Computation
```python
efficiency = actual_revenue / expected_revenue
```

### PXEInput Construction (Direct Mapping)
- No transformation of revenue data
- Direct pass-through from Trust Scorecard
- No calculation happens during mapping

**File:** [backend/revenue_engine.py](backend/revenue_engine.py#L300+)

---

## 5. ADVANCE RATE THRESHOLDS & POLICY DECISION TREE

**File Path:** [backend/policy_execution_engine.py](backend/policy_execution_engine.py#L315-L397)

### STANDARD_COMMERCIAL Policy (Default)

#### Rule 1: SOVEREIGN_UNLOCK
```
Conditions:
  - trust_score >= 90
  - mill_state == VERIFIED

Actions:
  - credit_decision: APPROVE
  - advance_rate: 0.60 (60%)
  - tenor_days: 45
  - capital_state: OPEN
  - audit_frequency: NONE
```

#### Rule 2: COMMERCIAL_APPROVE
```
Conditions:
  - trust_score >= 75 AND < 90

Actions:
  - credit_decision: APPROVE
  - advance_rate: 0.50 (50%)
  - tenor_days: 30
  - capital_state: OPEN
  - audit_frequency: QUARTERLY
```

#### Rule 3: CONDITIONAL_CONTROL
```
Conditions:
  - trust_score >= 60 AND < 75

Actions:
  - credit_decision: CONDITIONAL
  - advance_rate: 0.45 (45%)
  - tenor_days: 21
  - capital_state: CONSTRAINED
  - audit_frequency: MONTHLY
```

#### Rule 4: DECLINE
```
Conditions:
  - trust_score < 60

Actions:
  - credit_decision: DECLINE
  - advance_rate: 0.00 (0%)
  - capital_state: FROZEN
  - audit_frequency: IMMEDIATE
```

---

## 6. CIRCUIT BREAKERS & BREACH OVERRIDE LAYER

**File Path:** [backend/revenue_engine.py](backend/revenue_engine.py#L400+)

### Breach Override (Pre-PXE Layer)

Executes **BEFORE** policy evaluation with absolute authority.

#### Breach Type 1: MILL_SUSPENDED
```python
if pxe_input.mill_state == "SUSPENDED":
    return {
        "breach_detected": True,
        "override_action": "REJECT",
        "reason": "Mill is in SUSPENDED state. No credit available."
    }
```

#### Breach Type 2: ENERGY_MISMATCH
```python
if "ENERGY_MISMATCH" in pxe_input.breach_flags:
    return {
        "breach_detected": True,
        "override_action": "REQUIRE_AUDIT",
        "reason": "Energy mismatch detected. Requires immediate audit."
    }
```

#### Breach Type 3: REVENUE_FRAUD
```python
if "REVENUE_FRAUD" in pxe_input.breach_flags:
    return {
        "breach_detected": True,
        "override_action": "REJECT",
        "reason": "Revenue under-reporting detected. Credit frozen."
    }
```

#### Breach Type 4: REVENUE EFFICIENCY THRESHOLD
```python
# Critical circuit breaker
if pxe_input.revenue_efficiency_ratio < 0.85:  # <85% efficiency = fraud signal
    return {
        "breach_detected": True,
        "override_action": "REJECT",
        "reason": f"Revenue efficiency {efficiency:.2%} below 85% threshold."
    }
```

#### Breach Type 5: GOVERNANCE_FAILURE
```python
if pxe_input.governance_score < 50:
    return {
        "breach_detected": True,
        "override_action": "REQUIRE_AUDIT",
        "reason": "Governance score critically low. RBAC/signature failures."
    }
```

---

## 7. EAR THRESHOLD CONFIGURATION

**File Path:** [backend/ear_thresholds.py](backend/ear_thresholds.py)

### Energy Accountability Ratio (EAR) Tiers

#### Tier 1: FULL_CREDIT_UNLOCK
```
Min EAR: 0.95 (95%)
Max EAR: 1.01
DCE Multiplier: 1.0 (no penalty)
Description: Excellent accountability, minimal measurement error
```

#### Tier 2: CONDITIONAL_FINANCEABLE
```
Min EAR: 0.90 (90%)
Max EAR: 0.95
DCE Multiplier: 0.95 (5% penalty)
Description: Acceptable accountability with minor discrepancies (normal in distribution)
```

#### Tier 3: RESTRICTED
```
Min EAR: 0.0
Max EAR: 0.90
DCE Multiplier: 0.80 (20% penalty)
Description: Material discrepancies, elevated monitoring required
```

### Capital Tier Thresholds (DCE-Based)

```python
CAPITAL_TIER_THRESHOLDS = {
    "TIER_1_INSTITUTIONAL": {
        "dce_pct_min": 0.60,
        "ear_min": 0.95,
        "breach_count_max": 0,
    },
    "TIER_2_COMMERCIAL": {
        "dce_pct_min": 0.40,
        "ear_min": 0.85,
        "breach_count_max": None,
    },
    "TIER_3_SUBPRIME": {
        "dce_pct_min": 0.20,
        "ear_min": 0.70,
        "breach_count_max": None,
    },
    "TIER_4_RESTRICTED": {
        "dce_pct_min": 0.0,
        "ear_min": 0.0,
        "breach_count_max": None,
    }
}
```

---

## 8. CAPITAL CONTROLS DCE FORMULA

**File Path:** [backend/capital_controls.py](backend/capital_controls.py#L45)

### Dynamic Credit Envelope Calculation

```
DCE = α × VR × EAR × (1 − RiskPenalty)

Where:
  α = advance_rate (default 0.6 = 60%)
  VR = Verified Revenue (VT × ERR)
  EAR = Energy Accountability Ratio (0.0 - 1.0)
  RiskPenalty = breach-based + volatility-based (capped at 0.5)
```

### Default Advance Rate (Capital Controls)
```python
DEFAULT_ADVANCE_RATE = 0.6  # 60% max exposure
```

### Effective Revenue Rate (ERR)
```python
ERR = cash_collected / metered_kwh
```

### Verified Revenue
```python
VR = Verified Throughput (kWh) × ERR
```

---

## 9. ENTROPY MONITOR PENALTY (Structural Leakage Detection)

**File:** [backend/policy_execution_engine.py](backend/policy_execution_engine.py#L199-L200)

```python
# Entropy Monitor Input (default: no penalty)
structural_penalty_multiplier: float = 1.0  # From EntropyMonitor (0.9 if leakage detected)
structural_leakage_flag: bool = False  # True if structural leakage detected (all-negative variance pattern)

# Validation
if not (0.0 < self.structural_penalty_multiplier <= 1.0):
    errors.append("structural_penalty_multiplier must be 0.0 < x <= 1.0")
```

---

## 10. SUMMARY: ADVANCE RATE CALCULATION PIPELINE

```
1. Revenue Engine
   └─ compute_expected_revenue(verified_kwh, budgeted_rate)
   └─ compute_efficiency(actual_revenue, expected_revenue)
   └─ digital_efficiency = actual_revenue / expected_revenue

2. Trust Scorecard
   └─ trust_score (0-100)
   └─ mill_state (VERIFIED, UNDER_REVIEW, COMPROMISED, SUSPENDED)

3. Breach Override (Pre-PXE)
   └─ Check: revenue_efficiency < 0.85 → REJECT
   └─ Check: mill_state == SUSPENDED → REJECT
   └─ Check: governance_score < 50 → REQUIRE_AUDIT

4. Policy Execution Engine
   ├─ Match trust_score against policy rules
   │  └─ >= 90 → advance_rate = 0.60 (SOVEREIGN)
   │  └─ 75-90 → advance_rate = 0.50 (COMMERCIAL)
   │  └─ 60-75 → advance_rate = 0.45 (CONDITIONAL)
   │  └─ < 60 → advance_rate = 0.00 (DECLINE)
   └─ Compute: compute_advance_rate(trust_score, digital_efficiency, base_rate)

5. Capital Controls (DCE)
   └─ DCE = α × VR × EAR × (1 - RiskPenalty)
   └─ Final advance_amount = expected_revenue × final_advance_rate
```

---

## TEST FILES

**Test Coverage:**
- [test_gradual_squeeze.py](test_gradual_squeeze.py) - compute_advance_rate() correctness
- [test_squeeze.py](test_squeeze.py) - Gradual Squeeze formula verification
- [test_squeeze_entropy_integration.py](test_squeeze_entropy_integration.py) - Entropy × Squeeze integration
- [GRADUAL_SQUEEZE.md](GRADUAL_SQUEEZE.md) - Specification and examples

