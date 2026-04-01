# GridLedger Codebase Audit: Penalty Mechanisms, State Storage & Deviation Tracking

**Date**: March 30, 2026  
**Scope**: backend/core_engine.py, backend/consistency_engine.py, backend/revenue_engine.py, scripts/init_db.py, plus supporting modules  
**Status**: Complete system architecture analysis

---

## I. OPERATOR/MILL STATE TRACKING

### A. MillIntegrityState (Persistent Control Surface)

**File**: [scripts/init_db.py](scripts/init_db.py) (lines ~265-280)  
**Database Table**: `MillIntegrityState`

The mill enforcement state machine:

```sql
CREATE TABLE MillIntegrityState (
    mill_id: str           -- PRIMARY KEY (FK to Mill)
    state: str             -- VERIFIED | UNDER_REVIEW | COMPROMISED | SUSPENDED
    severity_level: int    -- 1 (informational) .. 4 (critical)
    last_trigger: str      -- GAP_BREACH | VARIANCE_BREACH | ECONOMIC_DEFICIT | ...
    last_reason: str       -- Human-readable explanation
    updated_at: datetime   -- Track state change history
)
```

**State Transitions** ([backend/enforcement_engine.py](backend/enforcement_engine.py)):
- `VERIFIED` → `UNDER_REVIEW` → `COMPROMISED` → `SUSPENDED` (monotonic escalation only)
- Defined in `EnforcementEngine._escalate_state()` (line 45)

**State Types**:
| State | Meaning | Action |
|-------|---------|--------|
| **VERIFIED** | Normal operation, no issues | Continue normal operations |
| **UNDER_REVIEW** | Variance breach or warning detected | Begin audit, reduce new credit |
| **COMPROMISED** | Gap breach or economic deficit | CASH_SWEEP + PRICING_ESCALATION |
| **SUSPENDED** | Critical failure | CASH_SWEEP + CREDIT_COMPRESSION + ESCALATION |

### B. OperatorProfile (Statistical State)

**File**: [backend/consistency_engine.py](backend/consistency_engine.py) (lines 1-60)  
**Database Table**: `OperatorProfile`

Welford's online algorithm for running statistics:

```python
@dataclass
class OperatorProfile:
    operator_id: str      -- PK
    n_reports: int        -- Sample count
    mean_yield: float     -- E[cash / kwh]
    m2_yield: float       -- Accumulated squared deviations (Welford)
    mean_opex: float      -- E[operational expenses]
    m2_opex: float        -- Accumulated squared deviations
    updated_at: datetime  -- Last update
```

**Variance Calculation**:
```python
variance = m2 / (n - 1)  # Unbiased estimator
std_dev = sqrt(variance)
```

**Usage**: Z-score outlier detection in fraud detection (line 68-95 consistency_engine.py)

### C. CycleManager (Multi-Day Cycle State)

**File**: [scripts/init_db.py](scripts/init_db.py) (lines ~195-230)  
**Database Table**: `Cycle`

```sql
CREATE TABLE Cycle (
    id: int                    -- PK
    mill_id: str              -- FK
    cycle_start: datetime     -- Window start
    cycle_end: datetime       -- Window end
    total_usage_kwh: float    -- Energy consumed in window
    total_actual_cash: float  -- Revenue collected
    expected_revenue: float   -- Budgeted based on efficiency baseline
    variance: float           -- gap = actual - expected (MWK)
    gap_breach_detected: bool -- Breach flag (used for 30-day rolling breach count)
    status: str               -- SOVEREIGN | UNDER_REVIEW
    reconciled_at: datetime   -- When reconciliation completed
)
```

---

## II. CURRENT PENALTY MECHANISMS

### A. Dynamic Credit Envelope (DCE) Risk Penalty

**File**: [backend/capital_controls.py](backend/capital_controls.py) (lines 180-210)

**Formula**:
```
DCE = α × VR × EAR × (1 − RiskPenalty)

where:
  α = advance rate (default 0.6, configurable per mill)
  VR = Verified Revenue (VT × ERR)
  EAR = Energy Accountability Ratio (0-1)
  RiskPenalty = min(0.5, breach_count×0.1 + volatility×0.05)
```

**RiskPenalty Composition**:
```python
def calculate_risk_penalty(breach_count: int, volatility: float) -> float:
    breach_penalty = breach_count * 0.1      # Each breach = 10% reduction
    volatility_penalty = volatility * 0.05   # Per unit volatility = 5% reduction
    total_penalty = breach_penalty + volatility_penalty
    return min(0.5, total_penalty)           # Cap at 50% maximum
```

**Penalty Thresholds**:
- 0 breaches + low volatility (0.1) = 0.5% penalty (nearly zero)
- 1 breach + medium volatility (0.5) = 15% penalty (0.1 + 0.025)
- 5 breaches + high volatility (1.0) = **50% penalty (capped)** = 50% DCE reduction

**Storage**: `CreditMetrics` table (line 350-380 init_db.py)

### B. Breach Detection & State Management

**File**: [backend/enforcement_engine.py](backend/enforcement_engine.py) (lines 105-150)

**Breach Types**:

```python
BreachType = Literal[
    "INFO",                 # Informational (no penalty)
    "WARNING",             # Potential issue (stay in VERIFIED)
    "GAP_BREACH",          # Energy gap > tolerance → COMPROMISED (severity 3)
    "VARIANCE_BREACH",     # Variance unusual → UNDER_REVIEW (severity 3)
    "ECONOMIC_DEFICIT",    # Revenue < cost → COMPROMISED (severity 3)
    "GOVERNANCE_FAILURE"   # Event signature invalid → UNDER_REVIEW (severity 2)
]
```

**Breach Detection Flow**:
```
1. check_economic_ceiling() → Detects energy gap
   ↓ if gap > tolerance
2. EnforcementEngine.classify_gap_breach()
   ↓ sets state = COMPROMISED, severity = 3
3. CapitalAtRisk.handle_state_transition()
   ↓ triggers CASH_SWEEP + PRICING_ESCALATION
```

### C. Capital Control Actions

**File**: [backend/capital_at_risk.py](backend/capital_at_risk.py) (lines 40-150)

**Triggered on State Escalation**:

| Action | Trigger State | Effect | Parameters |
|--------|---------------|--------|------------|
| **CASH_SWEEP** | COMPROMISED, SUSPENDED | Redirect 90% incoming revenue to reduce exposure | `sweep_rate=0.9` |
| **CREDIT_COMPRESSION** | SUSPENDED | Set remaining credit to zero immediately | `compression_rate=1.0` |
| **PRICING_ESCALATION** | COMPROMISED, SUSPENDED | Apply +500 basis points to outstanding balance | `penalty_rate_bps=500` |

**Storage**: `CreditEvent` table (line 330-350 init_db.py)

### D. Entropy Monitor (Structural Leakage Penalty)

**File**: [backend/revenue_engine.py](backend/revenue_engine.py) (lines 837-950)

**Detection Mechanism**:
```python
class EntropyMonitor:
    def record_variance(date: str, variance: float) -> float:
        # Track sign of (actual_revenue - expected_revenue)
        variance_sign = -1 if variance < 0 else 1
        # Rolling 7-day window
        self.variance_records.append(VarianceRecord(date, variance, variance_sign))
        
    def is_structural_leakage() -> bool:
        # ALL 7 days negative = structural leakage detected
        return all(v.variance_sign < 0 for v in self.variance_records)
    
    def get_penalty_multiplier() -> float:
        if is_structural_leakage():
            return 0.9  # 10% penalty multiplier
        else:
            return 1.0 - (sticky_decay * recovery_rate)
```

**Penalty Rules**:
- **All negative for 7 days** → `structural_penalty_multiplier = 0.9` (10% reduction)
- **Recovery rate** → 5% per day (takes ~20 days to recover from 0.9 to 1.0)
- **Threshold** → Window size = 7 days (configurable)

**Integration with PXE**: `structural_penalty_multiplier` passed to `CapitalActionObject` (policy_execution_engine.py line ~95)

### E. Z-Score Fraud Detection

**File**: [backend/consistency_engine.py](backend/consistency_engine.py) (lines 50-100)

**Outlier Scoring**:
```python
def calculate_suspicion_score(payload, profile):
    z_yield = (current_yield - mean_yield) / yield_std
    z_opex = (opex - mean_opex) / opex_std
    
    score = 0.0
    
    if abs(z_yield) > 2.5:  # > 2.5σ = outlier
        score += 20
    if abs(z_opex) > 2.5:
        score += 20
    
    # Synthetic fraud detection (low variability + perfect match)
    if profile.n_reports >= 5:
        yield_cv = yield_std / abs(mean_yield)
        opex_cv = opex_std / abs(mean_opex)
        if yield_cv < 0.35 and opex_cv < 0.25:  # Too consistent
            score += 50  # "Too perfect" = synthetic
    
    return SuspicionReport(
        z_score_yield=z_yield,
        z_score_opex=z_opex,
        score=score,
        is_synthetic_fraud=score >= 50,
        is_outlier=abs(z_yield) > 2.5 or abs(z_opex) > 2.5
    )
```

---

## III. DATABASE SCHEMA FOR STORING HISTORICAL METRICS

### A. Core Efficiency Tracking Tables

**ReconciliationRecord** ([scripts/init_db.py](scripts/init_db.py), lines 240-270):
```sql
CREATE TABLE ReconciliationRecord (
    id: int                          -- PK
    mill_id: str (FK)               -- Mill identifier
    timestamp: datetime             -- Record timestamp
    physical_reading: float         -- Cumulative meter reading (kWh)
    physical_consumed: float        -- Daily consumption
    reported_kwh: float             -- Operator reported
    variance_pct: float             -- % mismatch
    energy_accountability_ratio: float  -- EAR = reported / metered [0,1]
    verified_throughput: float      -- VT = metered × EAR
    status: str                     -- SOVEREIGN | UNDER_REVIEW
    root_hash: str                  -- Merkle root of events in window
    event_count: int                -- Number of events in window
    created_at: datetime
)
```

**CreditMetrics** ([scripts/init_db.py](scripts/init_db.py), lines 280-330):
```sql
CREATE TABLE CreditMetrics (
    id: int                         -- PK
    mill_id: str (FK)              -- Mill identifier
    timestamp: datetime            -- Snapshot time (enables time-series)
    
    -- Input Parameters
    advance_rate: float            -- α (configurable, default 0.6)
    effective_revenue_rate: float  -- ERR = cash / metered_kwh
    energy_accountability_ratio: float -- EAR [0,1]
    verified_throughput: float     -- VT (kWh)
    verified_revenue: float        -- VR = VT × ERR
    
    -- Risk Assessment (30-day rolling windows)
    breach_count_30d: int          -- Count of breaches in last 30 days
    volatility_score: float        -- Coefficient of variation [0,1]
    risk_penalty: float            -- Combined penalty [0, 0.5]
    
    -- Result
    dynamic_credit_envelope: float -- Final DCE value
    
    -- Status
    status: str                    -- CALCULATED | APPLIED | SUSPENDED
    reconciliation_record_id: int (FK)  -- Link to source reconciliation
)
```

### B. How Historical Metrics Are Queried

**30-Day Rolling Breach Count** ([backend/capital_controls.py](backend/capital_controls.py), line 102-131):
```python
def count_breaches_30d(mill_id: str) -> int:
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
    breach_cycles = session.exec(
        select(Cycle)
        .where(Cycle.mill_id == mill_id)
        .where(Cycle.gap_breach_detected == True)  # Breach flag
        .where(Cycle.reconciled_at >= cutoff_date)
    ).all()
    return len(breach_cycles)
```

**30-Day Volatility Score** ([backend/capital_controls.py](backend/capital_controls.py), line 134-180):
```python
def calculate_volatility_score(mill_id: str, window_days: int = 30) -> float:
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=window_days)
    records = session.exec(
        select(ReconciliationRecord)
        .where(ReconciliationRecord.mill_id == mill_id)
        .where(ReconciliationRecord.created_at >= cutoff_date)
        .order_by(ReconciliationRecord.created_at)
    ).all()
    
    variances = [r.variance_pct for r in records]
    mean_variance = sum(variances) / len(variances)
    
    # Coefficient of variation
    sq_deviations = [(v - mean_variance) ** 2 for v in variances]
    variance_of_variance = sum(sq_deviations) / len(sq_deviations)
    volatility = sqrt(variance_of_variance) / mean_variance
    
    return min(volatility, 1.0)  # Cap at 1.0
```

### C. EventLog (Append-Only Forensic Record)

**File**: [scripts/init_db.py](scripts/init_db.py) (lines 160-175)

```sql
CREATE TABLE EventLog (
    sequence_id: int (PK)      -- Monotonic sequence number
    mill_id: str (FK)          -- Mill identifier
    operator_id: str (FK)      -- Operator who submitted event
    payload_json: str          -- Full event payload
    payload_hash: str          -- SHA256(payload_json + signature)
    signature: str             -- Proof of origin
    prev_hash: str             -- Hash chain (blockchain-style)
    status: str                -- VERIFIED | FLAGGED_TEMPORAL_WARNING | FLAGGED_TEMPORAL_BREACH
    event_time: datetime       -- ISO-8601 timestamp (from payload)
)
```

**Historical Query** ([backend/reconciliation_engine.py](backend/reconciliation_engine.py), lines 80-120):
```python
def run_daily_recon(mill_id, physical_reading, start_time, end_time):
    # Fetch ALL verified events in window for Merkle proof
    events = session.exec(
        select(EventLog)
        .where(EventLog.mill_id == mill_id)
        .where(EventLog.status == "VERIFIED")
        .where(EventLog.event_time >= start_time)
        .where(EventLog.event_time < end_time)
        .order_by(EventLog.event_time)
    ).all()
    
    # Build Merkle root (proves no events deleted/inserted)
    root_hash = cls._build_event_merkle_root(events)
```

---

## IV. VARIANCE & DEVIATION CALCULATION METHODS

### A. Energy Accountabilty Ratio (EAR)

**File**: [backend/revenue_engine.py](backend/revenue_engine.py) & [backend/reconciliation_engine.py](backend/reconciliation_engine.py)

**Formula**:
```
EAR = reported_kwh / metered_kwh

Constraints:
- reported_kwh from operator system
- metered_kwh from independent physical meter (ground truth)
- Result clipped to [0, 1] (no over-reporting allowed)
```

**Implementation**:
```python
def compute_ear(reported_kwh: float, metered_kwh: float) -> float:
    if metered_kwh <= 0:
        raise ValueError("Metered reading must be > 0")
    raw_ear = reported_kwh / metered_kwh
    return min(1.0, max(0.0, raw_ear))  # Clip to [0, 1]
```

**Storage**: `ReconciliationRecord.energy_accountability_ratio` (timestamped)

### B. Verified Throughput (VT)

**Formula**:
```
VT = metered_kwh × EAR

Effect:
- If EAR = 1.0 (perfect match) → VT = metered_kwh (full credit for energy consumed)
- If EAR = 0.5 (50% reported) → VT = 0.5 × metered_kwh (halved throughput)
- If EAR = 0.0 (nothing reported) → VT = 0 (no throughput credit)
```

**Storage**: `ReconciliationRecord.verified_throughput` (timestamped)

### C. Variance Calculations

**Cycle Variance** ([backend/cycle_manager.py](backend/cycle_manager.py)):
```python
def compute_cycle_variance(actual_cash: float, expected_revenue: float) -> float:
    return actual_cash - expected_revenue
```

**Variance Percentage** ([backend/capital_controls.py](backend/capital_controls.py)):
```python
def calculate_variance_pct(reported_kwh: float, metered_kwh: float) -> float:
    if metered_kwh <= 0:
        return 0.0
    mismatch = abs(reported_kwh - metered_kwh) / metered_kwh
    return min(mismatch * 100.0, 100.0)  # Capped at 100%
```

### D. Revenue Efficiency Ratio

**File**: [backend/revenue_engine.py](backend/revenue_engine.py) (lines 250-280)

**Formula**:
```
efficiency = actual_revenue / expected_revenue

Interpretation:
- 1.0 = 100% (perfect match, operator reported truthfully)
- < 1.0 = under-reporting (operator hiding revenue)
- > 1.0 = impossible (or meter fault)
```

**Implementation**:
```python
def compute_efficiency(actual_revenue: float, expected_revenue: float) -> float:
    if expected_revenue <= 0:
        raise ValueError("Expected revenue must be > 0")
    return actual_revenue / expected_revenue
```

### E. Welford's Running Variance (Operator Profiles)

**File**: [backend/consistency_engine.py](backend/consistency_engine.py) (lines 20-50)

```python
def update_profile(operator_id: str, new_yield: float, new_opex: float):
    n += 1
    
    # Welford update for yield mean
    delta_yield = new_yield - mean_yield
    mean_yield += delta_yield / n
    delta2_yield = new_yield - mean_yield
    m2_yield += delta_yield * delta2_yield
    
    # Variance computed as: m2 / (n - 1)
    variance = m2_yield / (n - 1) if n > 1 else 0
    std_dev = sqrt(variance)
```

**Properties**:
- Single-pass online algorithm (no need to store all history)
- Numerically stable (avoids catastrophic cancellation)
- Unbiased variance estimator (divides by n-1)

---

## V. BREACH FLAGS & ANOMALY DETECTION

### A. Multi-Layer Breaches

**Gap Breach** ([backend/enforcement_engine.py](backend/enforcement_engine.py), lines 105-120):
- **Trigger**: Energy mismatch exceeds tolerance (typically 2%)
- **Detection**: `check_economic_ceiling()` compares token_kwh vs meter_kwh
- **Action**: State → COMPROMISED, severity = 3, `audit_required=True`, `block_token_purchase=True`

**Variance Breach**:
- **Trigger**: Cycle variance exceeds configurable threshold
- **Detection**: `variance_pct > tolerance_pct`
- **Action**: State → UNDER_REVIEW, severity = 3, `audit_required=True`

**Economic Deficit**:
- **Trigger**: Actual revenue < opex (negative profit)
- **Detection**: `actual_cash < opex_mwk`
- **Action**: State → COMPROMISED, severity = 3

**Temporal Breach** ([backend/temporal_guard.py](backend/temporal_guard.py)):
- **Trigger**: Clock drift > ±5 minutes for 3+ consecutive events in 24h
- **Detection**: NTP sync check on incoming event timestamps
- **Action**: Status → FLAGGED_TEMPORAL_BREACH, may escalate state

### B. Flagging System

**BreachFlags Dataclass** ([backend/policy_execution_engine.py](backend/policy_execution_engine.py), lines 50-65):
```python
@dataclass
class BreachFlags:
    gap_breach: bool = False
    variance_breach: bool = False
    economic_deficit: bool = False
    completeness_breach: bool = False
    
    def any_breach(self) -> bool:
        return any([gap_breach, variance_breach, economic_deficit, completeness_breach])
```

**Storage**: Passed to PXE as part of input contract; if `any_breach()` = True, PXE applies override penalties

### C. Anomaly Detection System

**AnomalyDetection** ([backend/core_engine.py](backend/core_engine.py), lines 145-200):

```python
class AnomalyDetection:
    def check_micro_skimming(reported_kwh):
        # Fiduciary Baseline Check (Golden Standard = 59.9 kWh)
        deviation = abs(reported_kwh - golden_standard) / golden_standard
        
        if reported_kwh < 15.0:
            return {"status": "BLOCKED", "risk_level": "CRITICAL"}
        
        if deviation > 0.05:  # 5% threshold
            return {"status": "FLAGGED", "risk_level": "MODERATE"}
        
        return {"status": "VERIFIED", "risk_level": "LOW"}
```

**Anomaly Categories**:
| Finding | Condition | Status | Risk Level | Action |
|---------|-----------|--------|-----------|--------|
| Micro-skimming | < 15 kWh | BLOCKED | CRITICAL | Reject transaction |
| Variance | 5%+ deviation | FLAGGED | MODERATE | Flag for review |
| Compliant | ≤ 5% deviation | VERIFIED | LOW | Proceed normally |

---

## VI. ENFORCEMENT & CONTROL FLOW

### A. Decision Tree

```
Cycle Receipt
    ↓
[Layer 0] TimeGuard.check_drift() 
    ├─ If drift > ±5min → FLAGGED_TEMPORAL_WARNING
    └─ If 3+ violations → FLAGGED_TEMPORAL_BREACH (escalate state)
    ↓
[Layer 1] ReconciliationEngine.run_daily_recon()
    ├─ EAR = reported / metered (clip [0,1])
    ├─ VT = metered × EAR
    └─ variance_pct = |reported - metered| / metered
    ↓
[Layer 2] EnforcementEngine.check_economic_ceiling()
    ├─ If variance > 2% → GAP_BREACH (state → COMPROMISED)
    └─ If actual < opex → ECONOMIC_DEFICIT (state → COMPROMISED)
    ↓
[Layer 3] CapitalControls.calculate_dce()
    ├─ breach_count_30d = count(gap_breach_detected=True, last 30d)
    ├─ volatility = stdev(variance_pct) / mean(variance_pct)
    ├─ risk_penalty = min(0.5, breach_count×0.1 + volatility×0.05)
    └─ DCE = 0.6 × VR × EAR × (1 - risk_penalty)
    ↓
[Layer 4] EntropyMonitor.record_variance()
    ├─ If all negative 7d → structural_leakage = True
    └─ Penalty multiplier = 0.9 (if leakage) or 1.0 (normal)
    ↓
[Layer 5] PolicyExecutionEngine.execute()
    ├─ Apply breach flag overrides
    ├─ Apply structural_penalty_multiplier
    └─ Output CapitalActionObject (final credit decision)
    ↓
[Layer 6] CapitalAtRisk.handle_state_transition()
    ├─ State = COMPROMISED → CASH_SWEEP + PRICING_ESCALATION
    └─ State = SUSPENDED → CASH_SWEEP + CREDIT_COMPRESSION + ESCALATION
```

### B. State Machine Visualization

```
VERIFIED ─ (GAP_BREACH) ─→ COMPROMISED ─ (no recovery) ─→ SUSPENDED
    ↑          (VARIANCE_BREACH)           ↓                  ↑
    └──────── UNDER_REVIEW ◄──────────────┘                  │
         (minor issues)            (escalation)              (critical)
```

---

## VII. KEY FILES SUMMARY

| Component | File | Lines | Key Methods |
|-----------|------|-------|-------------|
| **State Management** | [scripts/init_db.py](scripts/init_db.py) | 250-350 | `MillIntegrityState`, `CreditMetrics`, `ReconciliationRecord` tables |
| **Operator Stats** | [backend/consistency_engine.py](backend/consistency_engine.py) | 1-110 | `update_profile()`, `calculate_suspicion_score()` (Z-scores) |
| **Energy Verification** | [backend/revenue_engine.py](backend/revenue_engine.py) | 100-250 | `EnergyVerifier`, `RevenueTruthEngine`, `EntropyMonitor` |
| **Capital Controls** | [backend/capital_controls.py](backend/capital_controls.py) | 1-345 | `calculate_dce()`, `count_breaches_30d()`, `calculate_volatility_score()` |
| **Enforcement** | [backend/enforcement_engine.py](backend/enforcement_engine.py) | 1-200 | `EnforcementEngine.apply_decision()`, breach classification |
| **Enforcement Actions** | [backend/capital_at_risk.py](backend/capital_at_risk.py) | 1-220 | `trigger_cash_sweep()`, `trigger_pricing_escalation()` |
| **Reconciliation** | [backend/reconciliation_engine.py](backend/reconciliation_engine.py) | 1-150 | `run_daily_recon()`, Merkle root, EAR/VT calculation |
| **Temporal Guard** | [backend/temporal_guard.py](backend/temporal_guard.py) | 1-177 | `TemporalGuard.check_drift()`, NTP sync |
| **Policy Execution** | [backend/policy_execution_engine.py](backend/policy_execution_engine.py) | 1-400 | `CapitalActionObject`, input contract, PXE logic |
| **API Reports** | [backend/api_reports.py](backend/api_reports.py) | 1-400 | `get_mill_credit_history()`, `get_dce_history()` |

---

## VIII. CRITICAL FORMULAS REFERENCE

```
Energy Accountability Ratio (EAR)
├─ EAR = reported_kwh / metered_kwh
├─ Range: [0, 1] (clipped)
└─ Impact: Reduces VT if operator under-reports

Verified Throughput (VT)
├─ VT = metered_kwh × EAR
├─ Effect: Couples forward settlement to verified energy
└─ Storage: ReconciliationRecord.verified_throughput

Effective Revenue Rate (ERR)
├─ ERR = total_cash_collected / metered_kwh
└─ Unit: Currency per kWh

Verified Revenue (VR)
├─ VR = VT × ERR
├─ Formula: (metered_kwh × EAR) × (cash / metered_kwh)
└─ Effect: Only revenue backed by verified energy counts

Risk Penalty
├─ breach_penalty = breach_count × 0.1
├─ volatility_penalty = volatility_score × 0.05
├─ RiskPenalty = min(0.5, breach_penalty + volatility_penalty)
└─ Cap: Maximum 50% reduction to credit

Dynamic Credit Envelope (DCE)
├─ DCE = α × VR × EAR × (1 − RiskPenalty)
├─ α = advance rate (default 0.6)
├─ EAR multiplier = energy accountability coupling
└─ RiskPenalty multiplier = breach/volatility reduction

Entropy Penalty Multiplier
├─ If all(variance < 0 for 7 days) = structural leakage
├─ structural_penalty_multiplier = 0.9 (else 1.0)
├─ Recovery: +5% per day toward 1.0
└─ Final: Multiplied into PXE output

Z-Score (Fraud Detection)
├─ z = (value - mean) / std_dev
├─ Outlier threshold: |z| > 2.5 (> 2.5σ from center)
└─ Synthetic fraud: Low CV + high consistency = +50 points
```

---

## IX. INTEGRATION POINTS

1. **Cycle ingestion** → TimeGuard (Layer 0) → Reconciliation (Layer 1) → Enforcement (Layer 2)
2. **Daily reconciliation** → EAR/VT calculation → CreditMetrics storage
3. **DCE calculation** → Fetch breach_count_30d + volatility_score → Store in CreditMetrics
4. **Entropy monitoring** → Continuous variance tracking → Penalty multiplier to PXE
5. **PXE execution** → Consume all inputs → Output CapitalActionObject
6. **State transition** → Enforcement escalates state → CapitalAtRisk triggers actions

---

## X. NEXT STEPS FOR IMPLEMENTATION

- [ ] Audit trail verification (EventLog Merkle proofs are calculated but not validated)
- [ ] State recovery protocol (define rules for UNDER_REVIEW → VERIFIED recovery)
- [ ] Per-mill advance rate configuration (MillConfig table + registry)
- [ ] Historical breach/volatility backfilling (populate CreditMetrics for existing cycles)
- [ ] Entropy monitor persistence (currently in-memory; database persistence optional)
- [ ] Capital controls integration with actual payment systems (currently log-only)

