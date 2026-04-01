# GridLedger Database Structure & Forensic Data Query Guide

**Date**: March 30, 2026  
**Scope**: Complete schema, operator metrics storage, and query patterns for forensic analysis

---

## EXECUTIVE SUMMARY

GridLedger uses **SQLite with SQLModel ORM** persisted at `data/gridledger.db`. The database contains **13 core tables** organized into:

1. **Asset Registry** — Mills, Operators, Wallets
2. **Production Telemetry** — Daily meter readings and token purchases
3. **Reconciliation & Efficiency** — Energy metrics, variance tracking, DCE calculations
4. **Enforcement State** — Mill integrity state machine, credit controls
5. **Forensic Audit Trail** — Append-only event logs and credit actions

All operator metrics are **timestamped and immutable**, enabling forensic reconstruction of energy accountability, revenue collection, and capital risk decisions.

---

## TABLE 1: CORE DATA REGISTRY TABLES

### **Mill** (Asset Definition)

```python
class Mill(SQLModel, table=True):
    id: str (PRIMARY KEY)              # meter_id, e.g., "37154345799", "NABIWI"
    name: str                          # e.g., "Nabiwi Mkwinda"
    location: str                      # e.g., "District X, Region Y"
    meter_type: str                    # Device model: "Inhemeter", "Clou", "Chint"
    efficiency_baseline: float         # MWK per kWh; e.g., 1350.0
    public_key: Optional[str]          # For signature verification
    device_id: Optional[str]           # Hardware identifier
    last_nonce: Optional[str]          # Replay prevention
    last_event_hash: Optional[str]     # Chain integrity
```

**Query Operator Metrics by Mill**:
```sql
-- Get all operators and their mills
SELECT DISTINCT 
    m.id as mill_id,
    m.name as mill_name,
    m.location,
    m.efficiency_baseline,
    o.operator_id,
    o.name as operator_name
FROM mill m
LEFT JOIN operator o ON o.mill_id = m.id
ORDER BY m.name;
```

---

### **Operator** (Operator Registry)

```python
class Operator(SQLModel, table=True):
    operator_id: str (PRIMARY KEY)     # e.g., "OP_001_MUKONAZWI"
    name: str                          # Operator name
    phone: str                         # Contact number
    mill_id: str (FOREIGN KEY)         # Reference to Mill.id
    role_id: Optional[str] (FK)        # Role/permission level
    public_key: Optional[str]          # For event signature verification
    device_id: Optional[str]           # Mobile/device identifier
    last_nonce: Optional[str]          # Replay attack prevention
    last_event_hash: Optional[str]     # Chain of custody
```

---

### **TokenPurchase** (ESCOM Token/Energy Purchase Tracking)

```python
class TokenPurchase(SQLModel, table=True):
    token_id: str (PRIMARY KEY)        # Receipt number, e.g., "592152026031381201737"
    mill_id: str (FOREIGN KEY)         # Reference to Mill.id
    units_kwh: float                   # Energy purchased (kWh), e.g., 59.9
    cost_mwk: float                    # Cash paid (MWK), e.g., 20000.0
    revenue_wallet_id: str (FK)        # Wallet for revenue allocation
    opex_wallet_id: str (FK)           # Wallet for operational expenses
    purchase_date: datetime            # ISO timestamp of token purchase
    
    CONSTRAINT: revenue_wallet_id != opex_wallet_id
```

**Key Fields for Forensic Analysis**:
- `units_kwh` — Total energy purchased
- `cost_mwk` — Cash payment (in Malawi Kwacha)
- `purchase_date` — When token was activated
- Enables tracking: **Energy available** vs. **Energy reported** (leakage detection)

**Query Token Purchase History**:
```python
# Get all ESCOM token purchases for a mill
from sqlmodel import Session, select
from scripts.init_db import engine, TokenPurchase

with Session(engine) as session:
    tokens = session.exec(
        select(TokenPurchase)
        .where(TokenPurchase.mill_id == "37154345799")  # mil_id
        .order_by(TokenPurchase.purchase_date.desc())
    ).all()
    
    for token in tokens:
        print(f"Token {token.token_id}: {token.units_kwh} kWh @ {token.cost_mwk} MWK on {token.purchase_date}")
```

**Query Token Purchases in Date Range**:
```python
from datetime import datetime, timedelta

cutoff = datetime(2026, 1, 1)
tokens = session.exec(
    select(TokenPurchase)
    .where(TokenPurchase.mill_id == mill_id)
    .where(TokenPurchase.purchase_date >= cutoff)
    .order_by(TokenPurchase.purchase_date)
).all()
```

---

## TABLE 2: PRODUCTION TELEMETRY (Daily Meter Readings)

### **DailyReport** (Time-Series Meter Data)

```python
class DailyReport(SQLModel, table=True):
    id: Optional[int] (PRIMARY KEY)    # Auto-increment
    mill_id: str (FOREIGN KEY)         # Reference to Mill.id
    operator_id: Optional[str] (FK)    # Operator who submitted report
    opening_kwh: float                 # Meter reading at cycle start
    closing_kwh: float                 # Meter reading at cycle end
    actual_cash: float                 # Cash collected (MWK)
    report_date: datetime              # ISO timestamp (daily)
```

**Calculated Metrics**:
- `metered_energy = closing_kwh - opening_kwh` — Total energy measured
- `reported_cash = actual_cash`
- `reported_yield = actual_cash / metered_energy` — Revenue per kWh

**Query Daily Energy Consumption**:
```python
# Get last 30 days of metered energy for a mill
from datetime import datetime, timedelta

cutoff = datetime.now() - timedelta(days=30)

reports = session.exec(
    select(DailyReport)
    .where(DailyReport.mill_id == mill_id)
    .where(DailyReport.report_date >= cutoff)
    .order_by(DailyReport.report_date)
).all()

total_metered_kwh = sum(r.closing_kwh - r.opening_kwh for r in reports)
total_cash = sum(r.actual_cash for r in reports)
avg_yield = total_cash / max(total_metered_kwh, 0.001)

print(f"Total metered: {total_metered_kwh} kWh")
print(f"Total cash: {total_cash} MWK")
print(f"Avg yield: {avg_yield:.2f} MWK/kWh")
```

**Query for Forensic Gap Detection**:
```python
# Detect gaps in daily reporting (missing days)
from datetime import timedelta

reports = session.exec(
    select(DailyReport)
    .where(DailyReport.mill_id == mill_id)
    .order_by(DailyReport.report_date)
).all()

gaps = []
for i in range(1, len(reports)):
    days_since = (reports[i].report_date - reports[i-1].report_date).days
    if days_since > 1:
        gaps.append({
            'gap_days': days_since,
            'from_date': reports[i-1].report_date,
            'to_date': reports[i].report_date,
        })

for gap in gaps:
    print(f"⚠️ Gap detected: {gap['gap_days']} days ({gap['from_date']} → {gap['to_date']})")
```

---

## TABLE 3: RECONCILIATION & EFFICIENCY METRICS

### **ReconciliationRecord** (Verified Energy Accountability)

This is the **primary source for forensic energy analysis**.

```python
class ReconciliationRecord(SQLModel, table=True):
    id: Optional[int] (PRIMARY KEY)    # Auto-increment
    mill_id: str (FOREIGN KEY)         # Mill ID
    timestamp: datetime                # ⭐ KEY: When reconciliation occurred (immutable record)
    
    # Metering data
    physical_reading: float            # Meter reading (kWh)
    physical_consumed: float           # Energy consumed (kWh) = closing - opening
    reported_kwh: float                # Operator-reported kWh
    variance_pct: float                # (reported - metered) / metered × 100
    
    # Efficiency metrics
    status: str                        # "SOVEREIGN" | "UNDER_REVIEW"
    event_count: int                   # Number of events in window
    total_cash: float                  # Total cash collected (MWK)
    root_hash: str                     # Hash of last EventLog entry (chain of custody)
    
    # ACCOUNTABILITY METRICS (Critical for forensics)
    energy_accountability_ratio: float # EAR = reported_kwh / physical_consumed [0-1]
    verified_throughput: float         # VT = physical_consumed × EAR (verified energy)
    
    created_at: datetime               # Record creation timestamp
```

**EAR Interpretation**:
- **EAR = 1.0**: Operator reported 100% of metered energy (perfect accountability)
- **EAR = 0.85**: Operator reported 85% (15% unaccounted leakage/theft)
- **EAR < 0.5**: Severe under-reporting (below "auditable" threshold)

**Query for Energy Accountability Over Time**:
```python
# 30-day rolling EAR history for forensic audit
from datetime import datetime, timedelta

cutoff = datetime.now() - timedelta(days=30)

recon_records = session.exec(
    select(ReconciliationRecord)
    .where(ReconciliationRecord.mill_id == mill_id)
    .where(ReconciliationRecord.timestamp >= cutoff)
    .order_by(ReconciliationRecord.timestamp)
).all()

for record in recon_records:
    print(f"{record.timestamp.date()}: "
          f"EAR={record.energy_accountability_ratio:.2%}, "
          f"VT={record.verified_throughput:.1f} kWh, "
          f"Status={record.status}")

# Calculate average EAR
avg_ear = sum(r.energy_accountability_ratio for r in recon_records) / len(recon_records)
print(f"\n30-day avg EAR: {avg_ear:.2%}")
```

**Query for Leakage Detection**:
```python
# Identify structural leakage (consistent under-reporting)
recon_records = session.exec(
    select(ReconciliationRecord)
    .where(ReconciliationRecord.mill_id == mill_id)
    .order_by(ReconciliationRecord.timestamp.desc())
).all()[:30]

consistent_under_reporting = all(r.energy_accountability_ratio < 0.90 for r in recon_records)
if consistent_under_reporting:
    print("⚠️ STRUCTURAL LEAKAGE: Consistent under-reporting detected over 30 days")
    
    total_metered = sum(r.physical_consumed for r in recon_records)
    total_reportable = sum(r.verified_throughput for r in recon_records)
    leakage = total_metered - total_reportable
    
    print(f"  Total metered energy: {total_metered:.0f} kWh")
    print(f"  Reported energy (VT): {total_reportable:.0f} kWh")
    print(f"  Unaccounted energy: {leakage:.0f} kWh ({leakage/total_metered*100:.1f}%)")
```

---

### **Cycle** (Multi-Day Energy Cycle Reconciliation)

Reconciles multiple daily reports into a **cost cycle** (typically tied to token purchases).

```python
class Cycle(SQLModel, table=True):
    id: Optional[int] (PRIMARY KEY)    # Auto-increment
    mill_id: str (FOREIGN KEY)         # Mill ID
    token_id: Optional[str] (FK)       # Reference to TokenPurchase.token_id (if applicable)
    
    # Time window
    cycle_start: datetime              # Token purchase date or period start
    cycle_end: datetime                # End of reconciliation period
    
    # Energy metrics
    total_usage_kwh: float             # Sum of (closing - opening) from DailyReports
    total_actual_cash: float           # Sum of actual_cash from DailyReports (MWK)
    expected_revenue: float            # total_usage_kwh × Mill.efficiency_baseline
    
    # Variance analysis (leakage indicator)
    variance: float                    # actual_cash - expected_revenue (MWK gap)
    status: str                        # "RECONCILED" | "RESTRICTED" | "BLOCKED"
    integrity_score: float             # 100.0 (reconciled) → 50.0 (blocked)
    
    # Gap detection (meter continuity)
    gap_breach_detected: bool          # True if DailyReport gaps exist
    gap_breach_details: Optional[str]  # Details of detected gaps
    
    # Audit trail
    reconciled_at: datetime            # When cycle was closed
    audit_summary: str                 # Human-readable summary
    
    # Wallet allocation
    revenue_wallet_id: str (FK)        # Revenue destination
    opex_wallet_id: str (FK)           # OpEx destination
```

**Query Cycle Variance History**:
```python
# Analyze revenue variance (actual vs expected) over last 10 cycles
cycles = session.exec(
    select(Cycle)
    .where(Cycle.mill_id == mill_id)
    .order_by(Cycle.reconciled_at.desc())
).all()[:10]

total_variance = 0
for cycle in cycles:
    print(f"Cycle {cycle.cycle_start.date()} → {cycle.cycle_end.date()}:")
    print(f"  Usage: {cycle.total_usage_kwh:.1f} kWh")
    print(f"  Cash: {cycle.total_actual_cash:.0f} MWK")
    print(f"  Expected: {cycle.expected_revenue:.0f} MWK")
    print(f"  Variance: {cycle.variance:+.0f} MWK ({cycle.variance/cycle.expected_revenue*100:+.1f}%)")
    print(f"  Status: {cycle.status}")
    total_variance += cycle.variance

print(f"\nTotal 10-cycle variance: {total_variance:+.0f} MWK")
```

**Query Gap Breaches (Meter Continuity)**:
```python
# Find all cycles with meter continuity gaps
from sqlmodel import and_

breached_cycles = session.exec(
    select(Cycle)
    .where(and_(
        Cycle.mill_id == mill_id,
        Cycle.gap_breach_detected == True
    ))
    .order_by(Cycle.reconciled_at.desc())
).all()

print(f"Found {len(breached_cycles)} cycles with gap breaches:")
for cycle in breached_cycles:
    print(f"  {cycle.cycle_start.date()}: {cycle.gap_breach_details}")
```

---

## TABLE 4: CREDIT & EFFICIENCY HISTORY

### **CreditMetrics** (Dynamic Credit Envelope History)

This table stores **timestamped DCE calculations** for forensic reconstruction.

```python
class CreditMetrics(SQLModel, table=True):
    id: Optional[int] (PRIMARY KEY)    # Auto-increment
    mill_id: str (FOREIGN KEY)         # Mill ID
    timestamp: datetime                # ⭐ Snapshot timestamp (immutable records)
    
    # Input parameters
    advance_rate: float                # α (default 0.6, configurable per mill)
    effective_revenue_rate: float      # ERR = total_cash / metered_kwh
    energy_accountability_ratio: float # EAR (from ReconciliationRecord)
    verified_throughput: float         # VT in kWh (metered × EAR)
    verified_revenue: float            # VR = VT × ERR
    
    # Risk assessment
    breach_count_30d: int              # Number of breaches in last 30 days
    volatility_score: float            # Coefficient of variation (0-1)
    risk_penalty: float                # Combined penalty (0-0.5 cap)
    
    # DCE Formula
    dynamic_credit_envelope: float     # DCE = α × VR × EAR × (1 - RiskPenalty)
    
    # Metadata
    reconciliation_record_id: Optional[int]  # Reference to ReconciliationRecord.id
    status: str                        # "CALCULATED" | "APPLIED" | "SUSPENDED"
    created_at: datetime               # Auto-timestamp
```

**DCE Calculation Breakdown**:
$$\text{DCE} = \alpha \times \text{VR} \times \text{EAR} \times (1 - \text{RiskPenalty})$$

Where:
- **α (advance_rate)**: Configurable (typically 0.6 = 60% advance on verified revenue)
- **VR (verified_revenue)**: VT × ERR (energy that passed accountability × revenue rate)
- **EAR**: Energy accountability ratio (reported / metered)
- **RiskPenalty**: 0.1 per breach + 0.05 × volatility (capped at 0.5)

**Query DCE History (30 Days)**:
```python
# Get complete DCE calculation history for forensic audit
from datetime import datetime, timedelta

cutoff = datetime.now() - timedelta(days=30)

dce_records = session.exec(
    select(CreditMetrics)
    .where(and_(
        CreditMetrics.mill_id == mill_id,
        CreditMetrics.timestamp >= cutoff
    ))
    .order_by(CreditMetrics.timestamp)
).all()

print("DCE History (30 days):")
print("Date       | DCE        | VR        | EAR     | Risk Penalty | Breaches")
print("-" * 75)
for record in dce_records:
    print(f"{record.timestamp.date()} | "
          f"{record.dynamic_credit_envelope:>9.0f} | "
          f"{record.verified_revenue:>9.0f} | "
          f"{record.energy_accountability_ratio:>7.2%} | "
          f"{record.risk_penalty:>12.4f} | "
          f"{record.breach_count_30d}")

# Calculate average DCE
avg_dce = sum(r.dynamic_credit_envelope for r in dce_records) / len(dce_records)
print(f"\nAverage DCE (30 days): {avg_dce:.0f} MWK")
```

**Query Risk Penalty Drivers**:
```python
# Identify what's driving risk penalties
latest = dce_records[-1]

print(f"Latest DCE Calculation ({latest.timestamp.date()}):")
print(f"  Breaches (30d): {latest.breach_count_30d} × 0.1 = {latest.breach_count_30d * 0.1:.3f}")
print(f"  Volatility: {latest.volatility_score:.4f} × 0.05 = {latest.volatility_score * 0.05:.4f}")
print(f"  Total penalty: {latest.risk_penalty:.4f} (capped at 0.5)")
print(f"  Effective multiplier: {1 - latest.risk_penalty:.4f}")
```

---

## TABLE 5: ENFORCEMENT & STATE TRACKING

### **MillIntegrityState** (Operator Compliance State Machine)

Central control surface for enforcement policies.

```python
class MillIntegrityState(SQLModel, table=True):
    mill_id: str (PRIMARY KEY, FK)     # Reference to Mill.id
    
    # State machine
    state: str                         # "VERIFIED" → "UNDER_REVIEW" → "COMPROMISED" → "SUSPENDED"
    severity_level: int                # 1 (info) → 4 (critical)
    
    # Trigger information
    last_trigger: Optional[str]        # e.g., "GAP_BREACH", "VARIANCE_BREACH", "ECONOMIC_DEFICIT"
    last_reason: Optional[str]         # Human-readable explanation
    
    # Suspicion tracking (temporal)
    suspicion_score: float             # Cumulative 0-10, decays daily
    suspicion_updated_at: datetime     # Last update timestamp
    
    # Audit trail
    updated_at: datetime               # Last state change
```

**State Transitions**:
```
VERIFIED  → Normal operation, full credit access
UNDER_REVIEW → Investigation ongoing, reduced credit
COMPROMISED → Breach confirmed, no new tokens
SUSPENDED → Enforcement action, liquidation path
```

**Query Current Compliance State**:
```python
# Get enforcement state for all mills
from sqlmodel import and_

states = session.exec(
    select(MillIntegrityState)
    .order_by(MillIntegrityState.state)
).all()

print("Mill Integrity States:")
print("Mill         | State           | Severity | Last Trigger          | Suspicion")
print("-" * 85)
for state in states:
    mill = session.get(Mill, state.mill_id)
    print(f"{state.mill_id:12} | {state.state:15} | {state.severity_level}        | "
          f"{state.last_trigger:20} | {state.suspicion_score:.1f}/10")
```

**Query at-Risk Mills (UNDER_REVIEW or worse)**:
```python
from sqlalchemy import or_

at_risk = session.exec(
    select(MillIntegrityState)
    .where(or_(
        MillIntegrityState.state == "UNDER_REVIEW",
        MillIntegrityState.state == "COMPROMISED",
        MillIntegrityState.state == "SUSPENDED"
    ))
).all()

print(f"Found {len(at_risk)} mills with enforcement action needed:")
for state in at_risk:
    print(f"  {state.mill_id}: {state.state} (severity {state.severity_level}) - {state.last_reason}")
```

---

### **CreditEvent** (Capital Control Action Log)

Immutable record of enforcement actions triggered by state transitions.

```python
class CreditEvent(SQLModel, table=True):
    id: Optional[int] (PRIMARY KEY)    # Auto-increment
    mill_id: str (FOREIGN KEY)         # Mill subject to action
    timestamp: datetime                # When action was logged
    
    # Action details
    action_type: str                   # "CASH_SWEEP" | "CREDIT_COMPRESSION" | "PRICING_ESCALATION"
    trigger_state: str                 # Mill state that triggered action
    trigger_reason: str                # Specific reason code
    
    # Financial impact
    outstanding_balance: float         # Balance before action (MWK)
    action_amount: float               # Amount swept/compressed (MWK)
    penalty_rate_bps: int              # Basis points (500 = +5%)
    
    # Execution status
    action_status: str                 # "LOGGED" | "INITIATED" | "COMPLETED" | "FAILED"
    execution_timestamp: Optional[datetime]  # When executed
    notes: Optional[str]               # Additional context
    
    # Cross-reference
    credit_metric_id: Optional[int]    # Reference to CreditMetrics.id
```

**Query Capital Control Actions (Last 30 Days)**:
```python
# Audit trail of enforcement actions
from datetime import datetime, timedelta

cutoff = datetime.now() - timedelta(days=30)

events = session.exec(
    select(CreditEvent)
    .where(CreditEvent.timestamp >= cutoff)
    .order_by(CreditEvent.timestamp.desc())
).all()

print("Capital Control Actions (Last 30 Days):")
print("Timestamp       | Mill       | Action Type          | Amount   | Status")
print("-" * 80)
for event in events:
    print(f"{event.timestamp.date()} | {event.mill_id:10} | "
          f"{event.action_type:20} | {event.action_amount:>8.0f} | {event.action_status}")
```

**Query Impact by Mill**:
```python
# Total enforcement impact per mill
from sqlalchemy import func

impacts = session.exec(
    select(
        CreditEvent.mill_id,
        func.count(CreditEvent.id).label('action_count'),
        func.sum(CreditEvent.action_amount).label('total_amount'),
    )
    .where(CreditEvent.action_status == "COMPLETED")
    .group_by(CreditEvent.mill_id)
).all()

print("Enforcement Impact by Mill:")
for mill_id, count, amount in impacts:
    print(f"  {mill_id}: {count} actions, {amount:.0f} MWK swept/compressed")
```

---

## TABLE 6: FORENSIC AUDIT TRAIL

### **EventLog** (Append-Only Cryptographic Record)

Immutable source of truth for all operator submissions.

```python
class EventLog(SQLModel, table=True):
    sequence_id: Optional[int] (PK)    # Auto-increment, unbounded
    mill_id: str (FOREIGN KEY)         # Mill ID
    operator_id: str (FOREIGN KEY)     # Operator ID
    
    # Payload and signature
    payload_json: str                  # Original JSON submission
    payload_hash: str                  # SHA256 hash of payload
    signature: str                     # Base64 ed25519 signature
    
    # Chain of custody
    prev_hash: str                     # Hash of previous event (chain)
    
    # Status and timing
    status: str                        # "VERIFIED" | "FLAGGED_*" | "REJECTED_*"
    event_time: datetime               # Timestamp of submission
    
    # Prevent modification
    # ⚠️ Database constraints prevent updates/deletes
```

**Status Values**:
- `VERIFIED` — Event accepted, passed all validation
- `FLAGGED_SUSPICION` — Suspicious pattern detected (high fraud score)
- `FLAGGED_TEMPORAL_BREACH` — Clock manipulation detected
- `FLAGGED_TEMPORAL_WARNING` — Minor timestamp inconsistency
- `REJECTED_SIGNATURE` — Invalid cryptographic signature
- `REJECTED_REPLAY` — Duplicate nonce (replay attack)
- `FLAGGED_ECONOMIC_DEFICIT` — Token gap violation

**Query Forensic Event Chain**:
```python
# Reconstruct cryptographic chain for a mill
events = session.exec(
    select(EventLog)
    .where(EventLog.mill_id == mill_id)
    .order_by(EventLog.sequence_id)
).all()

print("Forensic Event Chain:")
for i, event in enumerate(events):
    print(f"Event {event.sequence_id}:")
    print(f"  Timestamp: {event.event_time}")
    print(f"  Operator: {event.operator_id}")
    print(f"  Status: {event.status}")
    print(f"  Payload hash: {event.payload_hash[:16]}...")
    print(f"  Previous hash: {event.prev_hash[:16]}...")
    
    # Verify chain continuity
    if i > 0 and event.prev_hash != events[i-1].payload_hash:
        print(f"  ⚠️ CHAIN BREAK DETECTED at event {event.sequence_id}")
```

**Query Flagged or Rejected Events**:
```python
# Security incidents: anomalies or rejections
from sqlalchemy import or_

flagged = session.exec(
    select(EventLog)
    .where(or_(
        EventLog.status.startswith("FLAGGED_"),
        EventLog.status.startswith("REJECTED_")
    ))
    .order_by(EventLog.event_time.desc())
).all()

print(f"Found {len(flagged)} anomalous events:")
for event in flagged:
    print(f"  {event.event_time}: {event.mill_id}/{event.operator_id} → {event.status}")
```

---

## COMPLETE QUERY RECIPES

### Recipe 1: Monthly Energy & Revenue Summary

**Use Case**: Monthly audit report with key metrics by mill.

```python
from datetime import datetime, timedelta

def monthly_summary(mill_id: str, year: int, month: int):
    """Generate monthly energy and revenue summary."""
    
    start = datetime(year, month, 1)
    end = datetime(year, month, 28) if month < 12 else datetime(year + 1, 1, 1)
    
    with Session(engine) as session:
        # 1. Energy metrics from DailyReports
        daily_reports = session.exec(
            select(DailyReport)
            .where(and_(
                DailyReport.mill_id == mill_id,
                DailyReport.report_date >= start,
                DailyReport.report_date < end
            ))
            .order_by(DailyReport.report_date)
        ).all()
        
        metered_kwh = sum(r.closing_kwh - r.opening_kwh for r in daily_reports)
        cash_collected = sum(r.actual_cash for r in daily_reports)
        
        # 2. Accountability from ReconciliationRecords
        recon_records = session.exec(
            select(ReconciliationRecord)
            .where(and_(
                ReconciliationRecord.mill_id == mill_id,
                ReconciliationRecord.timestamp >= start,
                ReconciliationRecord.timestamp < end
            ))
        ).all()
        
        avg_ear = sum(r.energy_accountability_ratio for r in recon_records) / len(recon_records) if recon_records else 0
        total_vt = sum(r.verified_throughput for r in recon_records)
        
        # 3. Token purchases
        tokens = session.exec(
            select(TokenPurchase)
            .where(and_(
                TokenPurchase.mill_id == mill_id,
                TokenPurchase.purchase_date >= start,
                TokenPurchase.purchase_date < end
            ))
        ).all()
        
        energy_purchased = sum(t.units_kwh for t in tokens)
        cash_paid = sum(t.cost_mwk for t in tokens)
        
        # 4. DCE snapshot
        dce = session.exec(
            select(CreditMetrics)
            .where(and_(
                CreditMetrics.mill_id == mill_id,
                CreditMetrics.timestamp >= start,
                CreditMetrics.timestamp < end
            ))
            .order_by(CreditMetrics.timestamp.desc())
        ).first()
        
        return {
            "period": f"{year}-{month:02d}",
            "metered_kwh": metered_kwh,
            "energy_purchased_kwh": energy_purchased,
            "cash_collected": cash_collected,
            "cash_paid": cash_paid,
            "avg_ear": round(avg_ear, 4),
            "total_verified_throughput": total_vt,
            "dce_latest": dce.dynamic_credit_envelope if dce else 0,
            "compliance_status": "✓ Auditable" if avg_ear >= 0.9 else "⚠️ Monitor",
        }

# Usage
summary = monthly_summary("NABIWI", 2026, 3)
print(summary)
```

---

### Recipe 2: Forensic Leakage Analysis

**Use Case**: Detect and quantify structural energy loss.

```python
def forensic_leakage_analysis(mill_id: str, months: int = 3):
    """Identify and quantify energy leakage over rolling period."""
    
    with Session(engine) as session:
        cutoff = datetime.now() - timedelta(days=30 * months)
        
        # Get all token purchases and daily reports in period
        tokens = session.exec(
            select(TokenPurchase)
            .where(and_(
                TokenPurchase.mill_id == mill_id,
                TokenPurchase.purchase_date >= cutoff
            ))
            .order_by(TokenPurchase.purchase_date)
        ).all()
        
        daily_reports = session.exec(
            select(DailyReport)
            .where(and_(
                DailyReport.mill_id == mill_id,
                DailyReport.report_date >= cutoff
            ))
            .order_by(DailyReport.report_date)
        ).all()
        
        # Energy balance
        energy_purchased = sum(t.units_kwh for t in tokens)
        energy_metered = sum(r.closing_kwh - r.opening_kwh for r in daily_reports)
        energy_reported = sum(r.actual_cash / mill.efficiency_baseline for r in daily_reports)  # Proxy
        
        # Leakage types
        purchased_to_metered = energy_purchased - energy_metered  # Over-purchase or meter lag
        metered_to_reported = energy_metered - energy_reported    # Structural leakage
        
        return {
            "energy_purchased": energy_purchased,
            "energy_metered": energy_metered,
            "energy_reported": energy_reported,
            "purchased_to_metered_gap": purchased_to_metered,
            "metered_to_reported_gap": metered_to_reported,
            "total_unaccounted_kwh": purchased_to_metered + metered_to_reported,
            "leakage_percentage": (metered_to_reported / energy_metered * 100) if energy_metered > 0 else 0,
            "classification": (
                "🟢 CLEAN" if metered_to_reported < 0 else
                "🟡 MINOR" if metered_to_reported < energy_metered * 0.05 else
                "🔴 SEVERE"
            ),
        }

analysis = forensic_leakage_analysis("NABIWI", months=3)
print(f"{analysis['classification']}: {analysis['leakage_percentage']:.1f}% leakage")
```

---

### Recipe 3: Capital Risk Assessment

**Use Case**: Calculate current DCE and identify risk drivers.

```python
def capital_risk_assessment(mill_id: str):
    """Assess current credit envelope and risk factors."""
    
    with Session(engine) as session:
        mill = session.get(Mill, mill_id)
        if not mill:
            return {"error": f"Mill {mill_id} not found"}
        
        # Get latest metrics
        latest_dce = session.exec(
            select(CreditMetrics)
            .where(CreditMetrics.mill_id == mill_id)
            .order_by(CreditMetrics.timestamp.desc())
        ).first()
        
        if not latest_dce:
            return {"error": "No DCE records found"}
        
        # Get state
        integrity_state = session.get(MillIntegrityState, mill_id)
        
        # Get recent capital actions
        recent_actions = session.exec(
            select(CreditEvent)
            .where(CreditEvent.mill_id == mill_id)
            .order_by(CreditEvent.timestamp.desc())
        ).all()[:5]
        
        # Calculate trend
        dce_trend = session.exec(
            select(CreditMetrics)
            .where(CreditMetrics.mill_id == mill_id)
            .order_by(CreditMetrics.timestamp.desc())
        ).all()[:10]
        
        dce_change = (dce_trend[0].dynamic_credit_envelope - dce_trend[-1].dynamic_credit_envelope) \
            if len(dce_trend) >= 2 else 0
        
        return {
            "mill_id": mill_id,
            "mill_name": mill.name,
            "current_dce": latest_dce.dynamic_credit_envelope,
            "dce_trend": "📈 IMPROVING" if dce_change > 0 else "📉 DETERIORATING",
            "compliance_state": integrity_state.state if integrity_state else "UNKNOWN",
            "risk_factors": {
                "breaches_30d": latest_dce.breach_count_30d,
                "volatility_score": latest_dce.volatility_score,
                "risk_penalty": latest_dce.risk_penalty,
                "ear": latest_dce.energy_accountability_ratio,
            },
            "recent_actions": [
                {"date": a.timestamp.date(), "type": a.action_type, "amount": a.action_amount}
                for a in recent_actions
            ],
            "recommendation": (
                "🟢 APPROVE: Excellent standing" if latest_dce.dynamic_credit_envelope > 100000 else
                "🟡 CONDITIONAL: Monitor closely" if latest_dce.dynamic_credit_envelope > 25000 else
                "🔴 DECLINE: Risk exceeds threshold"
            ),
        }

assessment = capital_risk_assessment("NABIWI")
print(f"DCE: {assessment['current_dce']:.0f} MWK → {assessment['recommendation']}")
```

---

## INITIALIZATION & ACCESS

### Setup Database

```bash
# From workspace root
python -c "from scripts.init_db import create_db_and_tables; create_db_and_tables()"
```

This creates `data/gridledger.db` with all 13 tables schema.

### Python Access Pattern

```python
from sqlmodel import Session, select, and_
from datetime import datetime, timedelta
from scripts.init_db import engine, Mill, DailyReport, Cycle, ReconciliationRecord, CreditMetrics
from scripts.init_db import TokenPurchase, MillIntegrityState, CreditEvent, EventLog

# All queries use this pattern
with Session(engine) as session:
    # Query
    records = session.exec(
        select(TableName)
        .where(condition)
        .order_by(column)
    ).all()
    
    # Process results
    for record in records:
        print(record.field_name)
```

---

## SUMMARY TABLE

| **Data Category** | **Primary Table** | **Key Timestamps** | **Forensic Use** |
|---|---|---|---|
| **Mill Assets** | Mill | — | Master registry |
| **ESCOM Tokens** | TokenPurchase | `purchase_date` | Energy purchased (source) |
| **Daily Meter** | DailyReport | `report_date` | Energy metered (consumed) |
| **Energy Accountability** | ReconciliationRecord | `timestamp` | EAR trends, leakage detection |
| **Cost Reconciliation** | Cycle | `reconciled_at` | Revenue variance, gap breaches |
| **Credit Envelope** | CreditMetrics | `timestamp` | DCE history, risk trends (⭐ primary) |
| **Compliance State** | MillIntegrityState | `updated_at` | Enforcement triggers |
| **Capital Actions** | CreditEvent | `timestamp` | Enforcement audit trail |
| **Operator Events** | EventLog | `event_time` | Cryptographic audit trail |

---

## KEY INSIGHTS

1. **Metered Energy Source**: `DailyReport` + `ReconciliationRecord` (timestamped)
2. **Reported Energy Proxy**: Cash collected / efficiency baseline
3. **Token Purchases**: `TokenPurchase.units_kwh` and `cost_mwk` (ESCOM record)
4. **EAR Calculation**: `reported_kwh / physical_consumed` (stored in ReconciliationRecord)
5. **Monthly Aggregation**: Query DailyReport + ReconciliationRecord by date range
6. **Leakage Detection**: Compare sum(TokenPurchase.units_kwh) vs. sum(DailyReport.metered_kwh)
7. **Capital Risk**: Latest CreditMetrics record + breach history from Cycle table
8. **Forensic Audit**: EventLog (immutable) + CreditEvent (action trail)

---

**Generated**: March 30, 2026  
**Author**: GridLedger Analytics  
**Version**: 1.0 (Complete Schema)
