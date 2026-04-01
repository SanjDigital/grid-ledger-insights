# GridLedger Penalty Mechanisms - Quick Reference

## 1. WHERE OPERATOR/MILL STATE IS TRACKED

| Component | Storage | Type | States |
|-----------|---------|------|--------|
| **MillIntegrityState** | SQLModel table | Persistent | VERIFIED → UNDER_REVIEW → COMPROMISED → SUSPENDED |
| **OperatorProfile** | SQLModel table | Persistent (Welford stats) | n_reports, mean_yield, m2_yield, mean_opex, m2_opex |
| **Cycle** | SQLModel table | Persistent | gap_breach_detected (bool), status (SOVEREIGN/UNDER_REVIEW) |

**Key File**: [scripts/init_db.py](scripts/init_db.py)

---

## 2. HOW PENALTIES ARE CURRENTLY APPLIED

### A. DYNAMIC CREDIT ENVELOPE (DCE) FORMULA
```
DCE = 0.6 × VR × EAR × (1 − RiskPenalty)

RiskPenalty = min(0.5, breach_count×0.1 + volatility×0.05)
```

### B. BREACH-BASED PENALTY
- **1 breach in 30 days** → -10% to credit
- **5+ breaches** → -50% to credit (capped)
- **Source**: `count_breaches_30d()` in [backend/capital_controls.py](backend/capital_controls.py)

### C. VOLATILITY-BASED PENALTY
- **Formula**: `penalty = volatility_score × 0.05`
- **Volatility**: Coefficient of variation of variance(%)
- **Source**: `calculate_volatility_score()` in [backend/capital_controls.py](backend/capital_controls.py)

### D. ENTROPY PENALTY (STRUCTURAL LEAKAGE)
- **Trigger**: All daily variances negative for 7+ consecutive days
- **Penalty**: `structural_penalty_multiplier = 0.9` (10% reduction)
- **Recovery**: +5% per day toward 1.0 (20 days to full recovery)
- **Source**: `EntropyMonitor` class in [backend/revenue_engine.py](backend/revenue_engine.py)

### E. STATE-BASED CAPITAL CONTROLS
| State | Actions | Files |
|-------|---------|-------|
| **COMPROMISED** | CASH_SWEEP + PRICING_ESCALATION (+500 bps) | [backend/capital_at_risk.py](backend/capital_at_risk.py) |
| **SUSPENDED** | CASH_SWEEP + CREDIT_COMPRESSION + ESCALATION | [backend/capital_at_risk.py](backend/capital_at_risk.py) |

---

## 3. DATABASE SCHEMA FOR HISTORICAL OPERATOR METRICS

### ReconciliationRecord (Daily Energy Accounting)
```sql
mill_id, timestamp, physical_consumed, reported_kwh, 
variance_pct, energy_accountability_ratio (EAR), 
verified_throughput (VT), root_hash (Merkle)
```
**File**: [scripts/init_db.py](scripts/init_db.py), lines 240-270

### CreditMetrics (Historical DCE Snapshots)
```sql
mill_id, timestamp, advance_rate, effective_revenue_rate,
energy_accountability_ratio (EAR), verified_throughput (VT),
verified_revenue (VR), breach_count_30d, volatility_score,
risk_penalty, dynamic_credit_envelope
```
**File**: [scripts/init_db.py](scripts/init_db.py), lines 280-330

### OperatorProfile (Running Statistics)
```sql
operator_id, n_reports, mean_yield, m2_yield, 
mean_opex, m2_opex, updated_at
```
**Implementation**: Welford's online algorithm (single-pass variance computation)  
**File**: [backend/consistency_engine.py](backend/consistency_engine.py)

---

## 4. WHERE VARIANCE/DEVIATION METRICS ARE CALCULATED

| Metric | Formula | Calculation File | Storage |
|--------|---------|------------------|---------|
| **EAR** | reported_kwh / metered_kwh [0,1] | [backend/revenue_engine.py](backend/revenue_engine.py) L250+ | ReconciliationRecord |
| **VT** | metered_kwh × EAR | [backend/reconciliation_engine.py](backend/reconciliation_engine.py) | ReconciliationRecord |
| **ERR** | total_cash / metered_kwh | [backend/capital_controls.py](backend/capital_controls.py) | CreditMetrics |
| **VR** | VT × ERR | [backend/capital_controls.py](backend/capital_controls.py) | CreditMetrics |
| **Variance %** | &#124;reported - metered&#124; / metered × 100 | [backend/capital_controls.py](backend/capital_controls.py) L155+ | ReconciliationRecord |
| **Volatility** | stdev(variance%) / mean(variance%) [0,1] | [backend/capital_controls.py](backend/capital_controls.py) L134-180 | CreditMetrics |
| **Z-Score** | (value - mean) / std_dev | [backend/consistency_engine.py](backend/consistency_engine.py) L68-95 | SuspicionReport |

---

## 5. HOW BREACH FLAGS & ANOMALIES ARE DETECTED

### Breach Types & Detection

| Breach Type | Trigger | Severity | Action | File |
|------------|---------|----------|--------|------|
| **GAP_BREACH** | Energy variance > 2% | 3 (critical) | State → COMPROMISED | [backend/enforcement_engine.py](backend/enforcement_engine.py) |
| **VARIANCE_BREACH** | Cycle variance unusual | 3 (critical) | State → UNDER_REVIEW | [backend/enforcement_engine.py](backend/enforcement_engine.py) |
| **ECONOMIC_DEFICIT** | Revenue < opex | 3 (critical) | State → COMPROMISED | [backend/enforcement_engine.py](backend/enforcement_engine.py) |
| **GOVERNANCE_FAILURE** | Event signature invalid | 2 (warning) | State → UNDER_REVIEW | [backend/enforcement_engine.py](backend/enforcement_engine.py) |
| **TEMPORAL_BREACH** | Clock drift > ±5min (3+ events) | 2 (warning) | Flag event, escalate state | [backend/temporal_guard.py](backend/temporal_guard.py) |

### Anomaly Detection

**Micro-Skimming Detection** ([backend/core_engine.py](backend/core_engine.py)):
```
if reported_kwh < 15 kWh:
    → status = BLOCKED, risk_level = CRITICAL
elif deviation > 5%:
    → status = FLAGGED, risk_level = MODERATE
else:
    → status = VERIFIED, risk_level = LOW
```

**Synthetic Fraud Detection** ([backend/consistency_engine.py](backend/consistency_engine.py)):
```
if yield_cv < 0.35 AND opex_cv < 0.25:  # Too consistent
    → score += 50 (synthetic fraud flag)
```

**Outlier Detection** (Z-score method):
```
if |z_yield| > 2.5 OR |z_opex| > 2.5:
    → score += 20 (outlier flag)
```

---

## 6. PENALTY ESCALATION FLOWCHART

```
Event Receipt
    ↓
Variance Detected
    ↓
variance > 2%? ──NO──→ Continue normal
    ↓ YES
GAP_BREACH Triggered
    ├─ Severity = 3
    ├─ State escalates to COMPROMISED
    └─ breach_count_30d += 1
    ↓
Risk Penalty Calculated
    ├─ breach_penalty = breach_count × 0.1
    ├─ volatility_penalty = volatility × 0.05
    ├─ RiskPenalty = min(0.5, total) [capped]
    └─ DCE reduced by (1 - RiskPenalty)
    ↓
3+ Consecutive Days Leakage?
    ├─ YES → structural_penalty = 0.9 (10% reduction)
    └─ NO → structural_penalty = 1.0
    ↓
PXE Output
    ├─ Advance Rate × (1 - risk_penalty) × (1 - structural_penalty)
    └─ CapitalActionObject with reduced DCE
    ↓
State = COMPROMISED?
    ├─ YES → CapitalAtRisk.trigger_cash_sweep()
    │        CapitalAtRisk.trigger_pricing_escalation(+500 bps)
    └─ NO → Normal operations
```

---

## 7. 30-DAY ROLLING WINDOW QUERIES

### Breach Count Query
```python
# From backend/capital_controls.py line 102-131
cutoff = now - 30 days
breach_count = count(
    Cycle 
    where mill_id = X 
    AND gap_breach_detected = True
    AND reconciled_at >= cutoff
)
```

### Volatility Calculation
```python
# From backend/capital_controls.py line 134-180
cutoff = now - 30 days
records = ReconciliationRecord
    where mill_id = X AND created_at >= cutoff

variances = [r.variance_pct for r in records]
mean = sum(variances) / len(variances)
variance = sum((v - mean)²) / len(variances)
volatility = sqrt(variance) / mean
return min(volatility, 1.0)
```

---

## 8. KEY DATABASE CONSTRAINTS

| Constraint | Table | Rule | Purpose |
|-----------|-------|------|---------|
| `energy_accountability_ratio` | ReconciliationRecord | [0, 1] clipped | Prevent over-reporting |
| `volatility_score` | CreditMetrics | [0, 1] capped | Cap historical volatility |
| `risk_penalty` | CreditMetrics | [0, 0.5] capped | Maximum 50% credit reduction |
| `breach_count_30d` | CreditMetrics | Rolling 30-day window | Time-bound breach history |
| State escalation | MillIntegrityState | Monotonic only | Cannot downgrade without recovery |
| EventLog immutability | EventLog | Append-only + Merkle | Forensic audit trail |

---

## 9. IMPLEMENTATION CHECKLIST

- [x] **State Storage**: MillIntegrityState table implemented
- [x] **Operator Stats**: OperatorProfile with Welford algorithm
- [x] **Energy Metrics**: EAR, VT, ERR, VR calculations working
- [x] **DCE Formula**: DCE = α × VR × EAR × (1 - RiskPenalty)
- [x] **Risk Penalty**: breach_count × 0.1 + volatility × 0.05 (capped 0.5)
- [x] **Breach Detection**: GAP_BREACH, VARIANCE_BREACH, ECONOMIC_DEFICIT, TEMPORAL_BREACH
- [x] **Entropy Monitoring**: 7-day rolling variance signs; 0.9 multiplier if all negative
- [x] **Capital Controls**: CASH_SWEEP, CREDIT_COMPRESSION, PRICING_ESCALATION
- [x] **Historical Tracking**: CreditMetrics + ReconciliationRecord timestamped
- [x] **Volatility Calculation**: Coefficient of variation (30-day rolling)
- [x] **Z-Score Detection**: Outlier + synthetic fraud detection
- [x] **Merkle Proofs**: EventLog hash chain + reconciliation root

---

## 10. FILES AT A GLANCE

```
Core State Management
├─ scripts/init_db.py........Database schema (13 tables)
├─ backend/enforcement_engine.py...State machine, breach classification
└─ backend/capital_at_risk.py....Capital control actions

Penalty Calculation
├─ backend/capital_controls.py....DCE, risk_penalty, volatility
├─ backend/revenue_engine.py.....Revenue truth, entropy monitor
└─ backend/consistency_engine.py..Operator profiles, z-scores

Verification & Detection
├─ backend/reconciliation_engine.py..EAR/VT, Merkle roots
├─ backend/temporal_guard.py......Temporal breach detection
└─ backend/core_engine.py........Micro-skimming, anomalies

Policy & Execution
├─ backend/policy_execution_engine.py..PXE, CapitalActionObject
└─ backend/api_reports.py.......History queries, credit reports
```

