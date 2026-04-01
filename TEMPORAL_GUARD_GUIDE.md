# Temporal Integrity Layer (Layer 0) - Implementation Guide

## Overview
The Temporal Guard (`backend/temporal_guard.py`) enforces time synchronization for all events in GridLedger, detecting and preventing timestamp-based attacks such as:
- Clock desynchronization (operator clock drifting)
- Event backdating/postdating attacks
- Systematic time manipulation for fraudulent reporting

## Architecture

### Layer 0 Placement
```
┌─────────────────────────────────────────────┐
│ TEMPORAL INTEGRITY CHECK (Layer 0)          │  <- NEW
│ - NTP time verification                      │
│ - Timestamp drift detection (±5 min)        │
│ - Breach escalation (3+ violations)         │
└────────────────────↓────────────────────────┘
│
├─ Authority Verification (Layer 1)
│  - Role-based permissions (RBAC)
│  - Gap breach detection
│
├─ Signature Verification (Layer 2)
│  - Cryptographic signature validation
│
├─ Nonce Verification (Layer 3)
│  - Replay attack prevention
│
├─ Economic Ceiling (Layer 4)
│  - Token gap enforcement
│
└─ Consistency Check (Layer 5)
   - Statistical anomaly detection
```

## Key Components

### 1. TemporalGuard Class
Main coordinator for temporal integrity checks.

**Methods:**
- `get_ntp_time()`: Fetch authoritative NTP time
  - Tries: pool.ntp.org → time.nist.gov → time.google.com
  - Fallback: System clock if all fail
  - Returns: UTC datetime
  
- `extract_timestamp_from_payload(payload_json)`: Extract timestamp from event
  - Expected format: ISO 8601 UTC (e.g., "2026-03-29T12:30:45.123456Z")
  - Returns: datetime or None
  
- `check_timestamp_drift(mill_id, event_timestamp, source)`: Main validation function
  - Compares event timestamp against NTP time
  - Tracks violations per mill (24-hour window)
  - Returns: (drift_seconds, status)
  - Raises: `TemporalWarning` or `TemporalBreach`

- `reset_drift_history(mill_id)`: Clear violation history (manual remediation)
- `get_drift_history(mill_id)`: Retrieve audit trail

### 2. Exception Classes

**TemporalWarning**
- Single timestamp violation (drift > ±300 seconds)
- First or second offense
- Event flagged but processed (reduced trust)
- Status: `FLAGGED_TEMPORAL_WARNING`

**TemporalBreach**
- 3+ violations within 24 hours
- Indicates systematic time manipulation
- Event rejected, mill set to `UNDER_REVIEW`
- Status: `FLAGGED_TEMPORAL_BREACH`
- Severity: 3/4 (high)

### 3. Thresholds

```python
DRIFT_TOLERANCE_SECONDS = 300      # ±5 minutes
BREACH_THRESHOLD = 3               # Violations to escalate
TRACKING_WINDOW = 24 hours         # Historical tracking
```

## Integration: cycle_manager.ingest_event()

### Execution Order (Layer Stack)
1. **Payload JSON parsing**
2. **Operator validation** (exists check)
3. **→ LAYER 0: Temporal Guard** (NEW)
   - Extract timestamp from payload
   - Fetch NTP time
   - Compare and track drift
   - Handle violations
4. **LAYER 1: Authority** (role-based permissions)
5. **LAYER 2: Signature** (cryptographic verification)
6. **LAYER 3: Nonce** (replay protection)
7. **LAYER 4: Economic** (token ceiling)
8. **LAYER 5: Consistency** (statistical anomalies)

### Event Status Mappings

| Status | Trigger | Consequence |
|--------|---------|-------------|
| VERIFIED | All checks pass | Event accepted, operator state updated |
| FLAGGED_TEMPORAL_WARNING | Single drift violation | Event logged, reduced trust |
| FLAGGED_TEMPORAL_BREACH | 3+ violations in 24h | Event rejected, mill → UNDER_REVIEW |
| FLAGGED_TEMPORAL_WARNING | (after warning processing) | Allowed if authority passes |
| FLAGGED_TEMPORAL_BREACH | (immediate) | Rejected, enforcement triggered |

### Mill State Transitions

```
Initial or VERIFIED
        ↓
    [Temporal Check]
        ↓
    ┌───┴───┐
    ↓       ↓
SYNCHRONIZED  VIOLATION
    ↓       ↓
 VERIFIED  [Count 24h violations]
            ↓
        ┌───┴──────┐
        ↓          ↓
     <3 (WARN)    >=3 (BREACH)
        ↓          ↓
   Continue     UNDER_REVIEW
   Process      (with severity=3)
```

## Event Payload Format

All events must include an ISO 8601 UTC timestamp:

```json
{
  "timestamp": "2026-03-29T12:30:45.123456Z",
  "nonce": "abc123def456...",
  "reported_kwh": 100.5,
  "reported_cash": 130650.0,
  "opex_mwk": 8000.0,
  "...": "other fields"
}
```

**Timestamp Parsing Rules:**
- Must be UTC (Z suffix or +00:00)
- Supports microseconds or seconds precision
- ISO 8601 format required
- Missing timestamp → ValueError raised

## Violation Tracking

### Per-Mill History
```python
_drift_history: Dict[str, list]
# Example: "mill_001" -> [(timestamp, drift_seconds), ...]

# 24-hour window: old violations auto-purged
# Max tracked: unlimited (garbage collected)
```

### Audit Interface
```python
violations = TemporalGuard.get_drift_history("mill_001")
# Returns: [(datetime, -45.2), (datetime, 280.1), ...]

# Clear history after remediation
TemporalGuard.reset_drift_history("mill_001")
```

## NTP Fallback Chain

```
Request 1: pool.ntp.org
    ├─ Success → Return time
    └─ Timeout/Error
        ↓
Request 2: time.nist.gov
    ├─ Success → Return time
    └─ Timeout/Error
        ↓
Request 3: time.google.com
    ├─ Success → Return time
    └─ Timeout/Error
        ↓
Fallback: System clock (datetime.now(timezone.utc))
```

## Dependencies
- `ntplib>=0.4.0`: NTP client
- `cryptography`: (pre-existing)
- `sqlmodel`: (pre-existing)

## Testing

### Basic Drift Check
```python
from backend.temporal_guard import TemporalGuard
from datetime import datetime, timezone, timedelta

# Current time → SYNCHRONIZED
now = datetime.now(timezone.utc)
drift, status = TemporalGuard.check_timestamp_drift("mill_1", now, "test")
assert status == "SYNCHRONIZED"

# 10 minutes in future → TemporalWarning
future = now + timedelta(minutes=10)
try:
    TemporalGuard.check_timestamp_drift("mill_2", future, "test")
except TemporalWarning as e:
    print(f"Warning raised: {e}")
```

### Breach Escalation
```python
# Simulate 3 violations
from datetime import timedelta

for i in range(3):
    old_time = now - timedelta(minutes=10+i)
    try:
        TemporalGuard.check_timestamp_drift("mill_3", old_time, "test")
    except TemporalWarning:
        pass
    except TemporalBreachError:
        print("Breach detected on 3rd violation")
```

## Monitoring & Operations

### Check Violation History
```python
from backend.temporal_guard import TemporalGuard

violations = TemporalGuard.get_drift_history("mkwinda")
print(f"Mill mkwinda has {len(violations)} violations in 24h")
for ts, drift in violations:
    print(f"  {ts}: {drift:.1f}s drift")
```

### Manual Remediation
```python
# After operator fixes their clock
TemporalGuard.reset_drift_history("mill_001")

# Mill integrity state remains UNDER_REVIEW until manually cleared
# (requires admin action in enforcement engine)
```

## Production Considerations

1. **NTP Server Selection**: Use organization-specific NTP servers if available
2. **Timeout Tuning**: Adjust timeout=2 if network latency is high
3. **Logging**: Integrate with system logging for audit trails
4. **Alerts**: Configure alerts on first TemporalWarning to operator
5. **Clock Sync**: Operators should run NTP daemon (ntpd) locally
6. **Timezone**: All times UTC; no local timezone conversions

## Related Files
- `backend/cycle_manager.py`: Integration point
- `scripts/init_db.py`: MillIntegrityState schema
- `backend/enforcement_engine.py`: Enforcement decisions
- `backend/temporal_guard.py`: Implementation
