# GridLedger Penalty Mechanisms - Code Reference Map

## QUICK NAVIGATION BY FEATURE

---

## 1️⃣ OPERATOR/MILL STATE TRACKING

### MillIntegrityState (The Control Surface)
**File**: `scripts/init_db.py`  
**Lines**: 265-280

```python
class MillIntegrityState(SQLModel, table=True):
    mill_id: str = Field(primary_key=True, foreign_key="mill.id")
    state: str = Field(default="VERIFIED")  # VERIFIED | UNDER_REVIEW | COMPROMISED | SUSPENDED
    severity_level: int = Field(default=1)  # 1..4
    last_trigger: Optional[str] = None      # GAP_BREACH | VARIANCE_BREACH | ...
    last_reason: Optional[str] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### State Transitions
**File**: `backend/enforcement_engine.py`  
**Lines**: 40-50

```python
@staticmethod
def _escalate_state(current: MillState, target: MillState) -> MillState:
    order: List[MillState] = ["VERIFIED", "UNDER_REVIEW", "COMPROMISED", "SUSPENDED"]
    return order[max(order.index(current), order.index(target))]
```

**How it's used**: 
```python
# Line 55-70
state.state = cls._escalate_state(state.state, decision.next_state)
state.severity_level = max(int(state.severity_level), int(decision.severity_level))
state.last_trigger = decision.breach_type
state.last_reason = decision.reason
state.updated_at = datetime.now(timezone.utc)
```

### OperatorProfile (Welford Statistics)
**File**: `backend/consistency_engine.py`  
**Lines**: 1-50

```python
# Update method (Welford algorithm)
@staticmethod
def update_profile(operator_id: str, new_yield: float, new_opex: float) -> OperatorProfile:
    # Line 22-46: Welford update for yield
    delta_yield = new_yield - profile.mean_yield
    profile.mean_yield += delta_yield / profile.n_reports
    delta2_yield = new_yield - profile.mean_yield
    profile.m2_yield += delta_yield * delta2_yield
    
    # Similar for opex...
```

**Variance extraction** (Line 62-65):
```python
yield_variance = (profile.m2_yield / (profile.n_reports - 1)) if profile.n_reports > 1 else 0.0
yield_std = yield_variance ** 0.5
```

---

## 2️⃣ PENALTY MECHANISMS

### A. Dynamic Credit Envelope (DCE) Formula

**File**: `backend/capital_controls.py`  
**Lines**: 1-30 (documentation)

Formula with all components:
```
DCE = α × VR × EAR × (1 − RiskPenalty)

Where:
α = advance_rate (0.6 default, configurable)
VR = verified_revenue = VT × ERR
EAR = energy_accountability_ratio [0, 1]
RiskPenalty = min(0.5, breach_count×0.1 + volatility×0.05)
```

### Risk Penalty Calculation

**File**: `backend/capital_controls.py`  
**Lines**: 180-210

```python
@staticmethod
def calculate_risk_penalty(breach_count: int, volatility: float) -> float:
    """
    RiskPenalty = min(0.5, breach_count × 0.1 + volatility × 0.05)
    
    Interpretation:
    - Each breach adds 0.1 (10% penalty)
    - Each unit volatility adds 0.05 (5% penalty)
    - Capped at 0.5 (50% maximum reduction)
    """
    breach_penalty = breach_count * 0.1
    volatility_penalty = volatility * 0.05
    total_penalty = breach_penalty + volatility_penalty
    return min(0.5, total_penalty)
```

### Breach Count (30-Day Rolling)

**File**: `backend/capital_controls.py`  
**Lines**: 102-131

```python
@staticmethod
def count_breaches_30d(mill_id: str) -> int:
    """Count enforcement breaches in last 30 days."""
    with Session(engine) as session:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Query: count cycles with gap_breach_detected=True in window
        breach_cycles = session.exec(
            select(Cycle)
            .where(Cycle.mill_id == mill_id)
            .where(Cycle.gap_breach_detected == True)
            .where(Cycle.reconciled_at >= cutoff_date)
        ).all()
        
        return len(breach_cycles)
```

### Volatility Score (30-Day Rolling)

**File**: `backend/capital_controls.py`  
**Lines**: 134-180

```python
@staticmethod
def calculate_volatility_score(mill_id: str, window_days: int = 30) -> float:
    """
    Volatility = stdev(variance_pct) / mean(variance_pct)
    
    Measures historical consistency:
    - Low (0.1): Stable, consistent reporting
    - High (1.0): Erratic, unstable reporting
    """
    # Line 144-150: Query reconciliation records in window
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=window_days)
    records = session.exec(
        select(ReconciliationRecord)
        .where(ReconciliationRecord.mill_id == mill_id)
        .where(ReconciliationRecord.created_at >= cutoff_date)
        .order_by(ReconciliationRecord.created_at)
    ).all()
    
    # Line 152-165: Calculate coefficient of variation
    variances = [r.variance_pct for r in records]
    mean_variance = sum(variances) / len(variances)
    sq_deviations = [(v - mean_variance) ** 2 for v in variances]
    variance_of_variance = sum(sq_deviations) / len(sq_deviations)
    volatility = (variance_of_variance ** 0.5) / mean_variance
    
    return min(volatility, 1.0)  # Cap at 1.0
```

### B. Entropy Monitor (Structural Leakage Penalty)

**File**: `backend/revenue_engine.py`  
**Lines**: 837-950

**VarianceRecord Dataclass** (Line 837-845):
```python
@dataclass
class VarianceRecord:
    date: str              # ISO-8601
    variance: float        # actual_revenue - expected_revenue
    variance_sign: int     # -1 (negative) or 1 (positive/zero)
```

**EntropyMonitor Class** (Line 847-950):
```python
class EntropyMonitor:
    def __init__(self, window_size: int = 7):
        self.window_size = window_size
        self.variance_records: List[VarianceRecord] = []
        self.current_penalty = 1.0
        self.last_update = None
    
    # Line 870-885: Record daily variance
    def record_variance(self, date: str, variance: float) -> float:
        variance_sign = -1 if variance < 0 else 1
        self.variance_records.append(VarianceRecord(date, variance, variance_sign))
        
        # Keep rolling window
        if len(self.variance_records) > self.window_size:
            self.variance_records.pop(0)
        
        # Update penalty (sticky decay recovery)
        self._update_penalty()
        return self.current_penalty
    
    # Line 887-895: Check for structural leakage
    def is_structural_leakage(self) -> bool:
        if len(self.variance_records) < self.window_size:
            return False
        return all(v.variance_sign < 0 for v in self.variance_records)
    
    # Line 897-910: Apply recovery
    def _update_penalty(self) -> None:
        if self.is_structural_leakage():
            self.current_penalty = 0.9  # 10% penalty when leakage detected
        else:
            # Recovery: +5% per day toward 1.0
            self.current_penalty = min(1.0, self.current_penalty + 0.05)
```

**Integration with PXE** ([backend/policy_execution_engine.py](backend/policy_execution_engine.py), Line 95):
```python
# Input to PXE
structural_penalty_multiplier: float = 1.0  # From EntropyMonitor (0.9 if leakage)
```

### C. Capital Control Actions

**File**: `backend/capital_at_risk.py`  
**Lines**: 40-220

**CASH_SWEEP** (Line 95-155):
```python
@classmethod
def trigger_cash_sweep(
    cls,
    mill_id: str,
    trigger_state: str,
    trigger_reason: str,
    sweep_rate: float = DEFAULT_CASH_SWEEP_PRIORITY,  # 0.9 (90%)
) -> List[Dict]:
    """
    Redirect 90% of incoming revenue to reduce outstanding exposure.
    
    Process:
    1. Outstanding balance = DCE value or credit extended
    2. sweep_amount = estimated_daily_revenue × 0.9
    3. Log in CreditEvent table
    4. Ready for payment processing system
    """
```

**PRICING_ESCALATION** (Line 175-210):
```python
@classmethod
def trigger_pricing_escalation(
    cls,
    mill_id: str,
    trigger_state: str,
    trigger_reason: str,
    penalty_rate_bps: int = DEFAULT_PENALTY_RATE_BPS,  # 500 (= +5%)
):
    """
    Apply +500 basis points to outstanding balance.
    
    Effect: Interest rate on remaining debt increases by 5%
    """
```

**Escalation Matrix** (Line 55-80):
```python
if new_state == "SUSPENDED":
    # Maximum enforcement
    executed_events.extend(
        cls.trigger_cash_sweep(mill_id, new_state, breach_reason)
    )
    executed_events.extend(
        cls.trigger_credit_compression(mill_id, new_state, breach_reason)
    )
    executed_events.extend(
        cls.trigger_pricing_escalation(mill_id, new_state, breach_reason)
    )
elif new_state == "COMPROMISED":
    # Medium enforcement
    executed_events.extend(
        cls.trigger_cash_sweep(mill_id, new_state, breach_reason)
    )
    executed_events.extend(
        cls.trigger_pricing_escalation(mill_id, new_state, breach_reason)
    )
```

---

## 3️⃣ DATABASE SCHEMA FOR HISTORICAL METRICS

### ReconciliationRecord Table

**File**: `scripts/init_db.py`  
**Lines**: 240-270

```python
class ReconciliationRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mill_id: str = Field(foreign_key="mill.id")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Physical measurements
    physical_reading: float      # Cumulative meter reading (kWh)
    physical_consumed: float     # Daily consumption
    reported_kwh: float         # Operator reported
    
    # Variance tracking
    variance_pct: float         # % mismatch
    status: str                 # SOVEREIGN | UNDER_REVIEW
    
    # Energy accountability metrics
    energy_accountability_ratio: float  # EAR = reported / metered [0,1]
    verified_throughput: float         # VT = metered × EAR
    
    # Forensic anchor
    root_hash: str              # Merkle root of events in window
    event_count: int            # Number of events in window
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### CreditMetrics Table

**File**: `scripts/init_db.py`  
**Lines**: 280-330

```python
class CreditMetrics(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mill_id: str = Field(foreign_key="mill.id")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Input parameters
    advance_rate: float = Field(default=0.6)  # α
    effective_revenue_rate: float = Field(default=0.0)  # ERR
    energy_accountability_ratio: float = Field(default=0.0)  # EAR
    verified_throughput: float = Field(default=0.0)  # VT in kWh
    verified_revenue: float = Field(default=0.0)  # VR = VT × ERR
    
    # Risk metrics (30-day rolling)
    breach_count_30d: int = Field(default=0)
    volatility_score: float = Field(default=0.0)
    risk_penalty: float = Field(default=0.0)
    
    # Result
    dynamic_credit_envelope: float = Field(default=0.0)
    
    # Status
    status: str = Field(default="CALCULATED")  # CALCULATED | APPLIED | SUSPENDED
    reconciliation_record_id: Optional[int] = Field(
        default=None, 
        foreign_key="reconciliationrecord.id"
    )
```

### Cycle Table (Gap Breach Tracking)

**File**: `scripts/init_db.py`  
**Lines**: 195-230

```python
class Cycle(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mill_id: str = Field(foreign_key="mill.id")
    
    # Time window
    cycle_start: datetime
    cycle_end: datetime
    
    # Energy & revenue
    total_usage_kwh: float
    total_actual_cash: float
    expected_revenue: float
    variance: float
    
    # Breach detection
    gap_breach_detected: bool = Field(default=False)  # ← CRITICAL: used for breach_count_30d
    gap_breach_details: Optional[str] = None
    
    status: str
    reconciled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

---

## 4️⃣ VARIANCE & DEVIATION CALCULATIONS

### Energy Accountability Ratio (EAR)

**File**: `backend/revenue_engine.py`  
**Lines**: 200-230

```python
class EnergyVerifier:
    TOLERANCE = 0.02  # 2% tolerance
    
    @staticmethod
    def compute_verified_kwh(
        token_kwh: float,
        meter_kwh: float
    ) -> float:
        """
        EAR coupled coefficient:
        - If meter > token: under-reporting (EAR reduced)
        - If meter = token: 1.0 (truthful)
        - If meter < token: error (rejected)
        """
        if meter_kwh <= 0:
            raise MeterVerificationError(f"Meter reading must be > 0")
        
        mismatch = abs(token_kwh - meter_kwh)
        mismatch_pct = mismatch / token_kwh
        
        if mismatch_pct > EnergyVerifier.TOLERANCE:
            raise MeterVerificationError(
                f"Energy mismatch {mismatch_pct:.2%} exceeds tolerance"
            )
        
        return meter_kwh  # Meter is ground truth
```

### Verified Throughput (VT) Calculation

**File**: `backend/reconciliation_engine.py`  
**Lines**: 120-150 (implicit in Cycle calculation)

```python
# VT calculation (in run_daily_recon):
# VT = physical_consumed × EAR
# Where EAR = reported_kwh / physical_consumed [clipped to [0,1]]

ear = min(1.0, reported_kwh / physical_consumed)
verified_throughput = physical_consumed * ear
```

### Revenue Efficiency Ratio

**File**: `backend/revenue_engine.py`  
**Lines**: 250-280

```python
class RevenueTruthEngine:
    @staticmethod
    def compute_efficiency(actual_revenue: float, expected_revenue: float) -> float:
        """
        efficiency = actual / expected
        
        - 1.0 = truthful (perfect match)
        - < 1.0 = under-reporting
        - > 1.0 = impossible (or meter fault)
        """
        if expected_revenue <= 0:
            raise ValueError("Expected revenue must be > 0")
        return actual_revenue / expected_revenue
```

### Volatility (Coefficient of Variation)

**File**: `backend/capital_controls.py`  
**Lines**: 152-175

```python
# Standard deviation of variance_pct
variance_records = [...]  # From ReconciliationRecord, last 30 days

mean_variance = sum(variances) / len(variances)
sq_deviations = [(v - mean_variance) ** 2 for v in variances]
std_variance = sqrt(sum(sq_deviations) / len(sq_deviations))

# Coefficient of variation
volatility = std_variance / mean_variance  # Capped at 1.0
```

---

## 5️⃣ BREACH FLAGS & ANOMALY DETECTION

### Breach Classification

**File**: `backend/enforcement_engine.py`  
**Lines**: 85-150

```python
@classmethod
def classify_gap_breach(cls, detail: str) -> EnforcementDecision:
    """Energy gap > 2%"""
    return EnforcementDecision(
        breach_type="GAP_BREACH",
        severity_level=3,
        next_state="COMPROMISED",
        reason=detail,
        audit_required=True,
        freeze_outputs=True,
        block_token_purchase=True,
    )

@classmethod
def classify_variance_breach(cls, variance_pct: float, tolerance_pct: float):
    """Cycle variance unusual"""
    return EnforcementDecision(
        breach_type="VARIANCE_BREACH",
        severity_level=3,
        next_state="UNDER_REVIEW",
        reason=f"variance_pct={variance_pct:.2f} exceeded tolerance_pct={tolerance_pct:.2f}",
        audit_required=True,
        freeze_outputs=False,
        block_token_purchase=False,
    )

@classmethod
def classify_governance_failure(cls, status: str):
    """Event signature invalid"""
    return EnforcementDecision(
        breach_type="GOVERNANCE_FAILURE",
        severity_level=2,
        next_state="UNDER_REVIEW",
        reason=f"event status={status}",
        audit_required=False,
        freeze_outputs=False,
        block_token_purchase=False,
    )
```

### Gap Breach Detection

**File**: `backend/enforcement_engine.py`  
**Lines**: 155-185

```python
@classmethod
def check_economic_ceiling(
    cls,
    mill_id: str,
    *,
    tolerance_pct: float = 2.0,
) -> Optional[EnforcementDecision]:
    """
    Soft/hard enforcement hook for the Token Gap Engine.
    
    Compares:
    - token_kwh (operator claim)
    - meter_kwh (physical measurement)
    
    If mismatch > tolerance_pct:
        → GAP_BREACH (COMPROMISED state, severity 3)
    """
    # Implementation details...
```

### Micro-Skimming Detection

**File**: `backend/core_engine.py`  
**Lines**: 145-200

```python
class AnomalyDetection:
    def check_micro_skimming(self, reported_kwh):
        """
        Golden Standard Check:
        - Exact match (59.9 kWh): VERIFIED
        - < 15 kWh: BLOCKED (micro-skimming signature)
        - 5%+ deviation: FLAGGED (red flag)
        """
        if reported_kwh < 15.0:
            return {
                "status": "BLOCKED",
                "risk_level": "CRITICAL",
                "reason": "Micro-Skimming Signature detected"
            }
        
        deviation = abs(reported_kwh - self.golden_standard) / self.golden_standard
        
        if deviation > 0.05:  # 5% threshold
            return {
                "status": "FLAGGED",
                "risk_level": "MODERATE",
                "reason": f"Variance of {deviation:.2%} exceeds 5% Fiduciary Threshold"
            }
        
        return {"status": "VERIFIED", "risk_level": "LOW"}
```

### Z-Score Fraud Detection

**File**: `backend/consistency_engine.py`  
**Lines**: 68-95

```python
# Z-score calculation
z_yield = (current_yield - profile.mean_yield) / yield_std
z_opex = (opex - profile.mean_opex) / opex_std

score = 0.0

# Outlier detection: |z| > 2.5
if abs(z_yield) > 2.5:
    score += 20
if abs(z_opex) > 2.5:
    score += 20

# Synthetic fraud: too perfect (low CV + high consistency)
if profile.n_reports >= 5:
    yield_cv = (yield_std / abs(profile.mean_yield)) if profile.mean_yield else float("inf")
    opex_cv = (opex_std / abs(profile.mean_opex)) if profile.mean_opex else float("inf")
    if yield_cv < 0.35 and opex_cv < 0.25:
        score += 50  # Large synthetic fraud penalty
```

### Temporal Breach Detection

**File**: `backend/temporal_guard.py`  
**Lines**: 1-177

```python
class TemporalGuard:
    TOLERANCE_SECONDS = 300  # ±5 minutes
    BREACH_THRESHOLD = 3     # 3+ violations in 24h → breach
    
    @classmethod
    def check_drift(cls, event_timestamp: str) -> Dict[str, Any]:
        """
        Check clock drift using NTP pool
        
        If drift > ±5min:
            → Increment violation counter
        If 3+ violations in 24h:
            → TemporalBreach (escalate state)
        """
```

---

## 6️⃣ POLICY EXECUTION ENGINE (PXE) INPUT CONTRACT

**File**: `backend/policy_execution_engine.py`  
**Lines**: 125-180

```python
@dataclass
class PXEInput:
    # Identity
    mill_id: str
    timestamp: str  # ISO-8601
    
    # Trust Scorecard Inputs
    trust_score: float  # 0-100
    reconciliation_score: float  # 0-100
    consistency_score: float  # 0-100
    governance_score: float  # 0-100
    
    # Revenue & Efficiency
    ear: float  # [0, 1]
    ear_tier: EARTier
    dce: float  # Numeric
    risk_penalty: float  # [0, 1]
    
    # State
    mill_state: MillState
    breach_flags: BreachFlags
    
    # Audit Reference
    event_metadata_hash: str  # Merkle root reference
    
    # Policy Selection
    policy_id: str
    
    # Gradual Squeeze Input
    digital_efficiency: float = 1.0
    
    # Entropy Monitor Input
    structural_penalty_multiplier: float = 1.0  # 0.9 if leakage detected
    structural_leakage_flag: bool = False
```

---

## 7️⃣ QUICK COMMAND REFERENCE

### Run Tests
```bash
# Test DCE calculation
python test_capital_impact.py

# Test entropy monitor
python test_entropy_monitor.py

# Test squeeze mechanism
python test_squeeze.py

# Quick validation
python test_quick.py
```

### Query Examples

```python
# Count breaches in last 30 days
from backend.capital_controls import CapitalControls
breaches = CapitalControls.count_breaches_30d("NABIWI_01")

# Calculate volatility
volatility = CapitalControls.calculate_volatility_score("NABIWI_01", window_days=30)

# Calculate risk penalty
penalty = CapitalControls.calculate_risk_penalty(
    breach_count=2,
    volatility=0.5
)  # Returns: 0.275 (=0.2 + 0.025)

# Get DCE for mill
from backend.capital_controls import CapitalControls
dce = CapitalControls.calculate_dce("NABIWI_01")
```

---

## 8️⃣ INTEGRATION FLOW DIAGRAM

```
Event Input
    ↓
[Layer 0] TimeGuard.check_drift()
    → EventLog.status = VERIFIED or FLAGGED_TEMPORAL_BREACH
    ↓
[Layer 1] ReconciliationEngine.run_daily_recon()
    → Calculate EAR = reported / metered [0,1]
    → Calculate VT = metered × EAR
    → Store in ReconciliationRecord
    ↓
[Layer 2] EnforcementEngine.check_economic_ceiling()
    → Detect GAP_BREACH (variance > 2%)
    → Escalate MillIntegrityState if breach
    ↓
[Layer 3] CapitalControls.calculate_dce()
    → Query breach_count_30d from Cycle table
    → Query volatility from ReconciliationRecord (30d window)
    → Calculate risk_penalty = min(0.5, breach×0.1 + volatility×0.05)
    → Calculate DCE = 0.6 × VR × EAR × (1 - risk_penalty)
    → Store in CreditMetrics (timestamped)
    ↓
[Layer 4] EntropyMonitor.record_variance()
    → Track variance sign (positive/negative)
    → If all negative 7 days → leakage detected
    → Penalty multiplier = 0.9 (else 1.0)
    ↓
[Layer 5] PolicyExecutionEngine.execute()
    → Consume PXEInput (all metrics above)
    → Apply breach_flags overrides
    → Apply structural_penalty_multiplier
    → Output CapitalActionObject
    ↓
[Layer 6] CapitalAtRisk.handle_state_transition()
    → If state = COMPROMISED → CASH_SWEEP + ESCALATION
    → If state = SUSPENDED → SWEEP + COMPRESS + ESCALATION
    → Log in CreditEvent
```

