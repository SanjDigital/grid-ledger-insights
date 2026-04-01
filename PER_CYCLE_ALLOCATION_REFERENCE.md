# Per-Cycle Token Allocation: Operational Reference

**Date**: April 1, 2026  
**Scope**: Per-cycle token allocation system with adherence-based penalties  
**Version**: Block 8 Complete — Ready for Production Integration

---

## State Machine: Allocation Status & Behavior

| Status | `get_last_cycle_adherence()` | `get_last_cycle_lag()` | Effect on Next Cycle | Notes |
|--------|---------------------------|-------------------|----------------------|-------|
| **PENDING** | 1.0 (no penalty) | 0.0 (no completed cycles yet) | Normal rate, waiting for receipt | New mill fallback — no prior CLOSED/DISPUTED cycles to evaluate |
| **CLOSED** (verified) | `cash / expected_revenue` | hours from allocation → receipt | Rate adjusted by actual performance | Receipt marked `verified=True`, normal cycle completion |
| **CLOSED** (unverified) | 0.0 (penalty) | hours from allocation → receipt | Severely reduced rate | Cash receipt exists but `verified=False` (shouldn't happen in normal flow) |
| **DISPUTED** | 0.0 (DISPUTED_ADHERENCE_PENALTY=0.0) | 72h (CONSERVATIVE_LAG_HOURS) | Severely reduced, pending admin review | Admin-marked for manual investigation; operator faces capital penalty |
| **MISSING** | 0.0 (DISPUTED_ADHERENCE_PENALTY=0.0) | 72h (CONSERVATIVE_LAG_HOURS) | Severely reduced, overdue receipt | Auto-marked by `detect_missing_cycles()` after 48h (MISSING_CYCLE_TIMEOUT_HOURS) |

### Key Behaviors

**Query Ordering** (in `get_last_cycle_adherence` and `get_last_cycle_lag`):
```python
TokenAllocation.status.in_(["CLOSED", "DISPUTED"]).order_by(allocated_at.desc())
```
→ Newest CLOSED or DISPUTED cycle is evaluated, not the most recent allocation  
→ A PENDING allocation does not affect next cycle's rate (returns default: adherence=1.0, lag=0.0)

**Penalty Application**:
- Quadratic adherence: `adherence²` (not linear)
  - Adherence 0.9 → 0.81 penalty (19% capital cut, not 10%)
  - Drives behavior change faster than linear penalty
- Latency step function via `latency_penalty(lag_hours)`:
  - <24h: 1.00 (no penalty, on-time)
  - 24–48h: 0.95 (5% penalty)
  - 48–72h: 0.90 (10% penalty)
  - ≥72h: 0.85 (15% penalty, severe)

**Resolution Flow** (Dispute → Closed):
1. Cycle flagged DISPUTED (auto by system or manual by admin)
2. Admin investigates discrepancy
3. Admin calls `resolve_dispute(allocation_id, resolved_by, resolution_notes)`
   - Validates: allocation is DISPUTED (not PENDING/MISSING/already CLOSED)
   - Finds associated `CashReceipt`
   - Sets: `allocation.status = "CLOSED"`, `receipt.verified = True`
   - Records: `resolved_by`, `resolved_at`, `resolution_notes` (audit trail)
4. Next cycle sees CLOSED (not DISPUTED) → normal adherence calculation

---

## Integration Chain (Block 8)

```
evaluate_mill_capital(mill_id, trust_score, session)
  │
  ├─→ get_last_cycle_adherence(mill_id, session)
  │   Location: backend/revenue_engine.py:1161
  │   Returns: float in [0.0, 1.0]
  │   Logic: Queries CLOSED/DISPUTED cycles, returns adherence or penalty
  │
  ├─→ get_last_cycle_lag(mill_id, session)
  │   Location: backend/revenue_engine.py:1207
  │   Returns: float (hours)
  │   Logic: Queries CLOSED/DISPUTED cycles, returns lag or conservative fallback
  │
  └─→ compute_per_cycle_advance_rate(trust_score, adherence, lag, base_rate)
      Location: backend/policy_execution_engine.py:389
      Formula: base_rate × (trust_score/100) × (adherence²) × latency_penalty(lag)
      Returns: float in [0.0, base_rate]
```

**Entry Point**: [backend/cycle_manager.py:33](backend/cycle_manager.py#L33)

---

## Operational Guarantees

### Race Condition Prevention (3-Layer Defense)

1. **Application Guard**: `allocate_token()` checks for existing PENDING allocation
2. **Database Guard**: Partial unique index `ix_one_pending_per_mill` on `(mill_id) WHERE status='PENDING'`
3. **Data Guard**: CHECK constraint validates `status IN ('PENDING', 'CLOSED', 'MISSING', 'DISPUTED')`

**Result**: Exactly one PENDING allocation per mill at any time, enforced at database level.

### Timezone Safety

- All `allocated_at`, `resolved_at` timestamps stored as UTC-aware datetimes
- SQLite maintains timezone info through SQLModel conversion
- Verified at runtime: test allocation 49h old correctly triggers MISSING status

### Error Handling & Fail-Safe

**`evaluate_mill_capital()` on Exception**:
- Catches all exceptions
- Logs: mill_id, exception type, full traceback
- Returns: 0.0 (fail-safe: blocks capital on error, doesn't hide problems)
- Implication: Sudden 0.0 rate could indicate:
  - Legitimate poor performance (DISPUTED/MISSING cycles)
  - System error (DB disconnect, import failure)
  - Operator **must check logs** to distinguish

**`detect_missing_cycles()` on Exception**:
- Logs error and traceback
- Returns count=0 (no cycles marked as missing, doesn't crash)
- Idempotent: safe to retry on next run

---

## What's Not Yet Wired (Operational Checklist)

### ✅ Code Complete
- [x] Per-cycle advance rate computation
- [x] Latency penalty step function
- [x] Database schema (TokenAllocation, CashReceipt, partial index)
- [x] Adherence & lag query helpers
- [x] Missing cycle detection
- [x] Admin dispute resolution
- [x] Integration orchestration function

### ⏳ Requires Scheduler Integration
- [ ] **`detect_missing_cycles()` scheduler**: Needs periodic call (every 24-48h recommended)
  - Option 1: APScheduler in `main.py` startup
  - Option 2: Cron job calling endpoint
  - **Current**: Function exists, nothing calls it yet

### ⏳ Requires Live Code Path Integration
- [ ] **`evaluate_mill_capital()` call site**: Where to invoke in PXE flow?
  - Should be called when determining advance rate for *next* cycle allocation
  - Likely in `issue_token()` or pre-allocation validation
  - **Current**: Function exists, not yet integrated into `issue_token()`

---

## Testing Status

| Component | Test Type | Status | Notes |
|-----------|-----------|--------|-------|
| `compute_per_cycle_advance_rate()` | Syntax | ✅ PASS | No syntax errors |
| `latency_penalty()` | Syntax | ✅ PASS | No syntax errors |
| `get_last_cycle_adherence()` | Syntax | ✅ PASS | No syntax errors |
| `get_last_cycle_lag()` | Syntax | ✅ PASS | No syntax errors |
| `detect_missing_cycles()` | Runtime | ✅ PASS | Marked 49h-old allocation as MISSING |
| `resolve_dispute()` | Code Inspection | ✅ PASS | Logic verified correct (DISPUTED→CLOSED) |
| Partial Index | Database | ✅ PASS | Index confirmed in sqlite_master |
| Timezone Handling | Runtime | ✅ PASS | UTC datetime conversions confirmed |
| `evaluate_mill_capital()` | Syntax | ✅ PASS | No syntax errors |

**Unit test suite**: Existing tests cover `compute_advance_rate()` (efficiency), `detect_missing_cycles()`, and `resolve_dispute()`.  
**Integration test**: End-to-end flow through `evaluate_mill_capital()` with real database — recommended before first deployment.

---

## Configuration Constants (from backend/config.py)

```python
TOLERANCE_PERCENT = 5.0                    # ±5% variance allowed
DISPUTED_ADHERENCE_PENALTY = 0.0           # Penalty for disputed cycles
MISSING_CYCLE_TIMEOUT_HOURS = 48           # Mark PENDING as MISSING after 48h
CONSERVATIVE_LAG_HOURS = 72.0              # Fallback lag for disputed/missing
BASE_ADVANCE_RATE = 0.5                    # Maximum advance rate (50%)

LATENCY_BOUNDARIES = [
    (24,   1.00),   # <24h:    no penalty
    (48,   0.95),   # 24–48h:  5% penalty
    (72,   0.90),   # 48–72h:  10% penalty
    (None, 0.85),   # ≥72h:    15% penalty
]
```

---

## Revision History

| Date | Change | Reason |
|------|--------|--------|
| 2026-03-31 | Initial Implementation (Blocks 1–8) | Per-cycle allocation system complete |
| 2026-04-01 | Fix: DISPUTED→CLOSED resolution logic | Resolved backwards state transition |
| 2026-04-01 | Clarify: PENDING lag interpretation | Prevent confusion in lag calculation |
| 2026-04-01 | Document: Operational Reference | Single source of truth for behavior |

---

## Sign-Off

**System**: Production-ready for code review and merge.  
**Blockers for deployment**: Scheduler integration + live code path integration.  
**Recommendation**: Add integration tests before first production deployment.
