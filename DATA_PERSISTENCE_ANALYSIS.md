# GridLedger Data Persistence & Efficiency Tracking Analysis

**Analysis Date**: March 30, 2026  
**Scope**: Complete database schema, state management, and efficiency history tracking

---

## EXECUTIVE SUMMARY

The GridLedger codebase implements a **SQLite database (via SQLModel ORM)** with four core stateful components that track efficiency, operator integrity, and capital risk. All efficiency history is persisted in `CreditMetrics` and `ReconciliationRecord` tables with timestamps, enabling time-series analysis and 30-day rolling calculations.

---

## 1. DATA PERSISTENCE LAYER

### 1.1 Database Configuration

| Property | Value |
|----------|-------|
| **Type** | SQLite ORM (SQLModel) |
| **Location** | `data/gridledger.db` |
| **Engine** | `scripts/init_db.py` (lines 1-50) |
| **Initialization** | `SQLModel.metadata.create_all(engine)` |
| **Tables** | 11 core tables + append-only EventLog |

### 1.2 Core Data Tables

#### Mill (Asset Registry)
**File**: [scripts/init_db.py](scripts/init_db.py) - lines 13-24

```python
class Mill(SQLModel, table=True):
    id: str (PK)
    name: str
    location: str
    meter_type: str
    efficiency_baseline: float  # MK per kWh (e.g., 1350.0)
    public_key: Optional[str]
    device_id: Optional[str]
```

**Role**: Defines mill/operator asset with baseline efficiency rate.

#### DailyReport (Time-Series Input)
**File**: [scripts/init_db.py](scripts/init_db.py) - lines 95-105

```python
class DailyReport(SQLModel, table=True):
    id: Optional[int] (PK)
    mill_id: str (FK → Mill.id)
    operator_id: Optional[str] (FK → Operator)
    opening_kwh: float
    closing_kwh: float
    actual_cash: float
    report_date: datetime
```

**Role**: Operator daily meter readings (kWh consumed, cash collected).

#### Cycle (Energy Cycle Reconciliation)
**File**: [scripts/init_db.py](scripts/init_db.py) - lines 108-138

```python
class Cycle(SQLModel, table=True):
    id: Optional[int] (PK)
    mill_id: str (FK)
    cycle_start: datetime
    cycle_end: datetime
    total_usage_kwh: float
    total_actual_cash: float
    expected_revenue: float          # budget
    variance: float                  # actual - expected gap
    status: str
    gap_breach_detected: bool        # FLAGGED IF VARIANCE < THRESHOLD
    reconciled_at: datetime
```

**Role**: Multi-day cycle reconciliation with variance and breach detection.

#### ReconciliationRecord (Verified Efficiency Data)
**File**: [scripts/init_db.py](scripts/init_db.py) - lines 180-206

```python
class ReconciliationRecord(SQLModel, table=True):
    id: Optional[int] (PK)
    mill_id: str (FK)
    timestamp: datetime              # ← ENABLES TIME-SERIES QUERIES
    physical_reading: float          # meter measured
    physical_consumed: float
    reported_kwh: float
    variance_pct: float
    energy_accountability_ratio: float  # EAR = reported / metered
    verified_throughput: float          # VT (kWh after leakage audit)
    status: str
```

**Role**: Verified energy metrics with timestamps for efficiency history.

#### CreditMetrics (Efficiency History - Time-Series)
**File**: [scripts/init_db.py](scripts/init_db.py) - lines 263-310

```python
class CreditMetrics(SQLModel, table=True):
    id: Optional[int] (PK)
    mill_id: str (FK)
    timestamp: datetime              # ← CRITICAL FOR HISTORICAL QUERIES
    
    # Input parameters
    advance_rate: float              # α (default 0.6)
    effective_revenue_rate: float    # ERR = cash / metered_kwh
    energy_accountability_ratio: float  # EAR (0-1)
    verified_throughput: float       # VT in kWh
    verified_revenue: float          # VR = VT × ERR
    
    # Risk Assessment (30-day rolling)
    breach_count_30d: int            # ROLLING COUNT OF BREACHES
    volatility_score: float          # ROLLING VARIANCE METRIC
    risk_penalty: float              # CALCULATED FROM HISTORY
    
    # DCE Result
    dynamic_credit_envelope: float   # FINAL DCE VALUE
    
    # Metadata
    reconciliation_record_id: Optional[int]
    status: str
```

**Role**: Complete DCE calculation history, timestamped for time-series analysis.

**Constraints**:
- `advance_rate` ∈ [0, 1]
- `energy_accountability_ratio` ∈ [0, 1]
- `risk_penalty` ∈ [0, 0.5]

#### MillIntegrityState (Enforcement State Machine)
**File**: [scripts/init_db.py](scripts/init_db.py) - lines 220-235

```python
class MillIntegrityState(SQLModel, table=True):
    mill_id: str (PK, FK → Mill)
    
    state: str  # VERIFIED | UNDER_REVIEW | COMPROMISED | SUSPENDED
    severity_level: int  # 1-4 (informational to critical)
    last_trigger: Optional[str]      # e.g., GAP_BREACH, VARIANCE_BREACH
    last_reason: Optional[str]
    updated_at: datetime
```

**Role**: Control surface for enforcement policy engines (token gating, audits, capital controls).

#### EventLog (Append-Only Forensic Record)
**File**: [scripts/init_db.py](scripts/init_db.py) - lines 155-172

```python
class EventLog(SQLModel, table=True):
    sequence_id: Optional[int] (PK)
    mill_id: str (FK)
    operator_id: str (FK)
    payload_json: str
    payload_hash: str
    signature: str
    prev_hash: str                   # Chain of custody
    status: str
    event_time: datetime
```

**Role**: Immutable source of truth (prevented from updates/deletes).

#### CreditEvent (Capital Control Actions)
**File**: [scripts/init_db.py](scripts/init_db.py) - lines 312-345

```python
class CreditEvent(SQLModel, table=True):
    id: Optional[int] (PK)
    mill_id: str (FK)
    timestamp: datetime
    
    action_type: str  # CASH_SWEEP, CREDIT_COMPRESSION, PRICING_ESCALATION
    trigger_state: str  # State that triggered action
    trigger_reason: str
    
    outstanding_balance: float
    action_amount: float
    penalty_rate_bps: int
    
    action_status: str  # LOGGED, INITIATED, COMPLETED, FAILED
    execution_timestamp: Optional[datetime]
```

**Role**: Tracks capital control actions triggered by state transitions.

---

## 2. EFFICIENCY HISTORY TRACKING

### 2.1 Current Storage Methods

#### Method 1: CreditMetrics Table (DCE History)
**Query**: [backend/capital_controls.py](backend/capital_controls.py) - `get_dce_history()` method

```python
def get_dce_history(mill_id: str, days: int = 30) -> list:
    """Retrieve DCE calculation history for a mill."""
    with Session(engine) as session:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        records = session.exec(
            select(CreditMetrics)
            .where(CreditMetrics.mill_id == mill_id)
            .where(CreditMetrics.timestamp >= cutoff_date)
            .order_by(CreditMetrics.timestamp.desc())
        ).all()
        
        return [
            {
                "timestamp": r.timestamp.isoformat(),
                "dce": round(r.dynamic_credit_envelope, 2),
                "vr": round(r.verified_revenue, 2),
                "ear": round(r.energy_accountability_ratio, 4),
                "risk_penalty": round(r.risk_penalty, 4),
                "breach_count": r.breach_count_30d,
            }
            for r in records
        ]
```

**Returns**: List of DCE snapshots, newest first, for analysis/charting.

#### Method 2: ReconciliationRecord Table (Raw Efficiency Data)
**Query**: [backend/api_reports.py](backend/api_reports.py) - lines 62-90

```python
# Get average EAR from last 5 reconciliations
recon_records = session.exec(
    select(ReconciliationRecord)
    .where(ReconciliationRecord.mill_id == mill_id)
    .order_by(ReconciliationRecord.timestamp.desc())
).all()[:5]

avg_ear = sum(r.energy_accountability_ratio for r in recon_records) / len(recon_records)
total_vt = sum(r.verified_throughput for r in recon_records)
```

**Returns**: Rolling energy accountability metrics.

#### Method 3: Cycle Table (Variance History)
**Query**: [backend/api_reports.py](backend/api_reports.py) - lines 40-60

```python
# Get last 5 cycles
cycle_records = session.exec(
    select(Cycle)
    .where(Cycle.mill_id == mill_id)
    .order_by(Cycle.reconciled_at.desc())
).all()[:5]

for cycle in cycle_records:
    variance = cycle.variance  # actual - expected in MWK
    total_leakage += abs(variance) if variance < 0 else 0
```

**Returns**: Historical variance and leakage trends.

### 2.2 Rolling Average Calculations

#### Breach Count (30-day rolling)
**Location**: [backend/capital_controls.py](backend/capital_controls.py) - `count_breaches_30d()` method

```python
def count_breaches_30d(mill_id: str) -> int:
    """Count enforcement breaches in last 30 days."""
    with Session(engine) as session:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        
        breach_cycles = session.exec(
            select(Cycle)
            .where(Cycle.mill_id == mill_id)
            .where(Cycle.gap_breach_detected == True)
            .where(Cycle.reconciled_at >= cutoff_date)
        ).all()
        
        return len(breach_cycles)
```

**Logic**: Count `gap_breach_detected=True` flags in last 30 days.

#### Volatility Score (30-day rolling)
**Location**: [backend/capital_controls.py](backend/capital_controls.py) - `calculate_volatility_score()` method

```python
def calculate_volatility_score(mill_id: str, window_days: int = 30) -> float:
    """Calculate volatility from variance consistency."""
    with Session(engine) as session:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=window_days)
        
        records = session.exec(
            select(ReconciliationRecord)
            .where(ReconciliationRecord.mill_id == mill_id)
            .where(ReconciliationRecord.created_at >= cutoff_date)
            .order_by(ReconciliationRecord.created_at)
        ).all()
    
    # Coefficient of variation: stdev(variance_pct) / mean(variance_pct)
    variances = [r.variance_pct for r in records]
    mean_variance = sum(variances) / len(variances)
    
    sq_deviations = [(v - mean_variance) ** 2 for v in variances]
    variance_of_variance = sum(sq_deviations) / len(sq_deviations)
    stddev = variance_of_variance ** 0.5
    
    cv = min(1.0, stddev / mean_variance) if mean_variance > 0 else 0.0
    return cv
```

**Formula**: `volatility = min(1.0, stdev / mean)` (capped at 1.0)

#### Risk Penalty (Composite)
**Location**: [backend/capital_controls.py](backend/capital_controls.py) - `calculate_risk_penalty()` method

```python
def calculate_risk_penalty(breach_count: int, volatility: float) -> float:
    """Calculate risk penalty from breach history and volatility."""
    breach_penalty = breach_count * 0.1
    volatility_penalty = volatility * 0.05
    total_penalty = breach_penalty + volatility_penalty
    return min(0.5, total_penalty)  # CAPPED AT 50%
```

**Components**:
- Each 30-day breach: +0.1 penalty
- Volatility score: +0.05 max
- **Cap**: 0.5 (50% maximum penalty)

---

## 3. STATEFUL COMPONENTS FOR EFFICIENCY TRACKING

### 3.1 EntropyMonitor (Structural Leakage Detection)
**File**: [backend/revenue_engine.py](backend/revenue_engine.py) - lines 837-950

**Purpose**: Detects structural revenue leakage via negative variance patterns.

**State Variables**:
```python
class EntropyMonitor:
    mill_id: str
    window_days: int = 7              # Rolling window size
    variance_records: List[VarianceRecord]  # In-memory rolling window
    penalty_multiplier_value: float = 1.0  # Current penalty (0.9-1.0)
    recovery_rate: float = 0.05       # 5% per day recovery
```

**VarianceRecord (Data Class)**:
```python
@dataclass
class VarianceRecord:
    date: str                          # ISO-8601
    variance: float                    # actual_revenue - expected_revenue
    variance_sign: int                 # -1 (negative), 1 (positive/zero)
```

**Key Methods**:

1. **`record_variance(date, variance)`**
   - Adds variance to rolling window
   - Maintains window size (drops oldest if > window_days)
   - Updates penalty multiplier
   - Returns updated multiplier

2. **`is_structural_leakage()`**
   - REQUIRES full window (e.g., 7 days)
   - Returns `True` if ALL variance signs are -1
   - Returns `False` if window not full OR any positive variance

3. **`get_penalty_multiplier()`**
   - Returns current penalty (0.9-1.0)
   - **Sticky decay**: Once penalty activated (0.9), recovery is gradual (+5% per day)
   - NOT binary reset on first positive variance

**Example Flow**:
```
Day 1-7: All negative → penalty = 0.9
Day 8: Positive variance → penalty stays 0.9, begins recovery
Day 9: penalty = 0.95 (+0.05 recovery)
Day 10: penalty = 1.0 (fully recovered)
```

**Persistence**: 
- ⚠️ **NOT persisted to database** (in-memory only)
- Requires stateful wrapper to persist penalty history

### 3.2 OperatorProfile (Welford Online Statistics)
**File**: [backend/consistency_engine.py](backend/consistency_engine.py) - lines 14-90

**Purpose**: Track operator integrity via running mean/variance statistics.

**State Variables** (SQLModel - persisted):
```python
class OperatorProfile(SQLModel, table=True):
    operator_id: str (PK, FK → Operator)
    n_reports: int                     # Sample count
    mean_yield: float                  # Average revenue/kWh
    m2_yield: float                    # Variance accumulator (Welford)
    mean_opex: float                   # Average operational expense
    m2_opex: float                     # Variance accumulator
    updated_at: datetime
```

**Key Methods**:

1. **`ConsistencyEngine.update_profile(operator_id, new_yield, new_opex)`**
   - Implements Welford's online algorithm
   - Updates mean and M2 incrementally
   - Persists to database
   - Returns updated profile

2. **`calculate_suspicion_score(payload, profile)`**
   - Computes Z-scores for yield and opex
   - Detects synthetic fraud (too-perfect patterns)
   - Returns SuspicionReport with breach flags

**Welford Algorithm**:
```python
delta_yield = new_yield - mean_yield
mean_yield += delta_yield / n_reports
delta2_yield = new_yield - mean_yield
m2_yield += delta_yield * delta2_yield

# Later: variance = m2_yield / (n_reports - 1)
# Std dev = sqrt(variance)
```

**Persistence**: ✅ **Stored in `OperatorProfile` table** (timestamped in `updated_at`)

### 3.3 MillIntegrityState (State Machine)
**File**: [scripts/init_db.py](scripts/init_db.py) - lines 220-235

**Purpose**: Track mill compliance state for enforcement policies.

**States**:
```
VERIFIED       → Normal operation
UNDER_REVIEW   → Investigation ongoing
COMPROMISED    → Breach confirmed
SUSPENDED      → No credit available
```

**Transitions**:
- Triggered by breach conditions (gap_breach, variance_breach, etc.)
- Recorded with timestamp and reason
- Consumed by capital controls and policy engines

**Persistence**: ✅ **Stored in `MillIntegrityState` table**

### 3.4 CycleManager (Multi-Day Reconciliation)
**File**: [backend/cycle_manager.py](backend/cycle_manager.py)

**Purpose**: Reconcile multi-day energy cycles with variance tracking.

**State**:
```python
class Cycle(SQLModel, table=True):
    cycle_start: datetime
    cycle_end: datetime
    total_usage_kwh: float
    total_actual_cash: float
    expected_revenue: float            # From mill.efficiency_baseline
    variance: float                    # actual_cash - expected_revenue
    gap_breach_detected: bool          # FLAGGED IF VARIANCE EXCEEDS THRESHOLD
    status: str                        # SOVEREIGN | UNDER_REVIEW
    reconciled_at: datetime
```

**Breach Detection**:
- Computes variance between expected and actual
- Sets `gap_breach_detected=True` if variance exceeds policy threshold
- Used to populate 30-day breach count

**Persistence**: ✅ **Stored in `Cycle` table**

---

## 4. EFFICIENCY TRACKING DATA FLOW

```
┌─────────────────────────────┐
│   DailyReport               │ (operator meter readings)
│   opening_kwh, closing_kwh  │
│   actual_cash               │
└──────────┬──────────────────┘
           │
           ↓
┌─────────────────────────────┐
│   Cycle (Multi-Day)         │ (reconciliation)
│   total_usage_kwh           │
│   total_actual_cash         │
│   expected_revenue          │ ← mill.efficiency_baseline
│   variance = actual - expect│
│   gap_breach_detected       │ ← flag if variance > threshold
└──────────┬──────────────────┘
           │
           ↓
┌─────────────────────────────┐
│  ReconciliationRecord       │ (verified energy metrics)
│  energy_accountability_ratio│ = reported / metered
│  verified_throughput        │ = metered * EAR
│  timestamp                  │ ← timestamp
│  variance_pct               │
└──────────┬──────────────────┘
           │
           ↓
┌─────────────────────────────┐
│  CreditMetrics              │ (DCE history)
│  timestamp                  │ ← timestamp
│  advance_rate               │
│  effective_revenue_rate     │
│  energy_accountability_ratio│
│  verified_revenue           │
│  breach_count_30d           │ ← rolling count
│  volatility_score           │ ← rolling variance
│  risk_penalty               │
│  dynamic_credit_envelope    │
└──────────┬──────────────────┘
           │
           ↓
┌─────────────────────────────┐
│  EntropyMonitor (optional)  │ (in-memory penalty)
│  penalty_multiplier         │ (0.9-1.0, sticky decay)
│  variance_records (7-day)   │ (rolling window)
└──────────┬──────────────────┘
           │
           ↓
┌─────────────────────────────┐
│  PXE (Policy Execution)     │ (final decision)
│  × digital_efficiency       │
│  × penalty_multiplier       │
└──────────┬──────────────────┘
           │
           ↓
┌─────────────────────────────┐
│  CapitalActionObject (CAO)  │ (advance rate & amount)
│  decision: APPROVE/DECLINE  │
│  advance_rate               │
│  advance_amount (in MWK)    │
└─────────────────────────────┘
```

---

## 5. API ENDPOINTS FOR EFFICIENCY HISTORY

**File**: [backend/main.py](backend/main.py) and [backend/api_reports.py](backend/api_reports.py)

### 5.1 Credit History Endpoint
```
GET /api/v1/mills/{mill_id}/credit/history?days=30
```

**Handler**: [backend/api_reports.py](backend/api_reports.py) - `get_mill_credit_history()`

**Returns**:
```json
{
  "mill_id": "NABIWI",
  "mill_name": "Nabiwi Mkwinda",
  "period_days": 30,
  "dce_history": [
    {
      "timestamp": "2026-03-30T10:00:00Z",
      "dce": 50000.00,
      "vr": 75000.00,
      "ear": 0.85,
      "risk_penalty": 0.1,
      "breach_count": 1
    }
  ]
}
```

### 5.2 Performance Summary Endpoint
```
GET /api/v1/mills/{mill_id}/performance
```

**Handler**: [backend/api_reports.py](backend/api_reports.py) - `get_mill_performance_summary()`

**Returns**: Last 5 cycles with variance trends.

### 5.3 Credit Metrics (Current DCE) Endpoint
```
GET /api/v1/mills/{mill_id}/credit/metrics
```

**Handler**: [backend/api_reports.py](backend/api_reports.py) - `get_mill_credit_metrics()`

**Calculates**: Fresh DCE with 30-day rolling components.

---

## 6. SUMMARY TABLE: STATE MANAGEMENT

| Component | File | Table/Class | Persistence | Update Frequency | Rolling Window |
|-----------|------|-----------|-------------|-----------------|-----------------|
| **EntropyMonitor** | `backend/revenue_engine.py` | `EntropyMonitor` | ❌ In-memory | per variance record | 7 days |
| **OperatorProfile** | `backend/consistency_engine.py` | `OperatorProfile` | ✅ SQLModel | per operator report | n_reports (unbounded) |
| **MillIntegrityState** | `scripts/init_db.py` | `MillIntegrityState` | ✅ SQLModel | state transition | single state |
| **Cycle (Variance)** | `scripts/init_db.py` | `Cycle` | ✅ SQLModel | per cycle (~weekly) | gap_breach_detected flag |
| **ReconciliationRecord** | `scripts/init_db.py` | `ReconciliationRecord` | ✅ SQLModel (timestamped) | per reconciliation | timestamp indexed |
| **CreditMetrics** | `scripts/init_db.py` | `CreditMetrics` | ✅ SQLModel (timestamped) | per DCE calc | timestamp indexed |
| **Breach Count** | `backend/capital_controls.py` | derived from `Cycle` | ✅ Database query | on-demand | 30 days |
| **Volatility Score** | `backend/capital_controls.py` | derived from `ReconciliationRecord` | ✅ Database query | on-demand | 30 days |

---

## 7. KEY FILES & LINE REFERENCES

### Database Schema
- **All tables**: [scripts/init_db.py](scripts/init_db.py) (lines 13-345)
- **Engine config**: [scripts/init_db.py](scripts/init_db.py) (lines 348-370)

### Stateful Components
- **EntropyMonitor**: [backend/revenue_engine.py](backend/revenue_engine.py) (lines 825-958)
- **VarianceRecord**: [backend/revenue_engine.py](backend/revenue_engine.py) (line 825)
- **OperatorProfile**: [scripts/init_db.py](scripts/init_db.py) (lines 60-67)
- **MillIntegrityState**: [scripts/init_db.py](scripts/init_db.py) (lines 220-235)
- **Cycle**: [scripts/init_db.py](scripts/init_db.py) (lines 108-138)

### Efficiency Tracking
- **Calculate DCE**: [backend/capital_controls.py](backend/capital_controls.py) (lines 210-320)
- **Get DCE history**: [backend/capital_controls.py](backend/capital_controls.py) (lines 373-395)
- **Volatility calculation**: [backend/capital_controls.py](backend/capital_controls.py) (lines 130-165)
- **Breach count**: [backend/capital_controls.py](backend/capital_controls.py) (lines 100-125)

### API Endpoints
- **Mill credit history**: [backend/api_reports.py](backend/api_reports.py) (lines 201-225)
- **Performance summary**: [backend/api_reports.py](backend/api_reports.py) (lines 20-95)
- **Credit metrics**: [backend/api_reports.py](backend/api_reports.py) (lines 177-196)

---

## 8. INITIALIZATION CHECKLIST

To enable full persistence and efficiency tracking:

```bash
# 1. Create database and tables
python scripts/init_db.py
# OR
python -c "from scripts.init_db import create_db_and_tables; create_db_and_tables()"

# 2. Verify database created
ls -la data/gridledger.db

# 3. Run initial tests to populate sample data
pytest test_capital_impact.py -v

# 4. Query efficiency history
python -c "
from scripts.init_db import engine, CreditMetrics
from sqlmodel import Session, select
with Session(engine) as session:
    records = session.exec(select(CreditMetrics)).all()
    print(f'CreditMetrics records: {len(records)}')
"
```

---

## 9. CONCLUSIONS & RECOMMENDATIONS

✅ **Strengths**:
- Comprehensive time-series persistence via `CreditMetrics` and `ReconciliationRecord` tables
- Rolling 30-day window calculations for volatility and breach counts
- Three-layer efficiency tracking: raw data (ReconciliationRecord) → calculated metrics (CreditMetrics) → policy execution
- Immutable audit trail (EventLog, WalletLineage)

⚠️ **Gaps**:
- **EntropyMonitor** penalty history NOT persisted to database (in-memory only)
- No explicit "rolling average efficiency" table (calculated on-demand from ReconciliationRecord)
- No time-series persistence of digital_efficiency values (3-layer efficiency penalty chain)

💡 **Recommendations**:
1. Extend `CreditMetrics` to store `digital_efficiency` for penalty tracking
2. Add `EntropyMonitor` snapshots to database for complete audit trail
3. Create indexed views for fast 7-day, 30-day, 90-day efficiency aggregations
4. Document mill configuration registry (`MillConfigRegistry` in `backend/revenue_engine.py`)

