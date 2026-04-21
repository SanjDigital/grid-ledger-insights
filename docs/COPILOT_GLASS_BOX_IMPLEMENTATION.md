# IMPLEMENTATION PROMPT: Glass Box Certification — Phase 1

## Context

GridLedger is a physics-first capital enforcement system for informal industrial
operators (maize mills) in Malawi. It allocates energy tokens (59.9 kWh/cycle),
tracks cash remittance against expected revenue, and gates the next token on
compliance. All enforcement data lives in `token_allocations` and `cash_receipts`.

We are now adding **Glass Box Certification** — a deterministic certification mark
earned by operators who sustain verified compliance across a minimum number of cycles.
It is not assigned manually. It is computed automatically from existing enforcement data.

### Operator Identity — CRITICAL

**Operator IDs in this system use the Malawi National Registration Identity (NRID) number.**

The NRID is the primary identifier for every operator. It is the value stored in
`mill_id` / `meter_number` fields throughout the codebase. All queries, API endpoints,
logs, and certification records must reference operators by their NRID.

- Format: Malawi NRID (alphanumeric national ID string)
- Example usage: `get_certification_status("MWI-NRID-XXXXXXXX", session)`
- Do NOT generate or assume sequential integer IDs for operators
- Do NOT use email, name, or any other field as the operator identifier
- The NRID is what the Glass Box certificate will display as the certified entity

This ensures every certification is unambiguously tied to a legally registered
individual, creating a direct link between the physical enforcement system and
Malawi's national identity infrastructure.

---

## Files to Modify

| File | Change |
|---|---|
| `scripts/init_db.py` | Add `glass_box_certified` field to `Mill` model |
| `backend/revenue_engine.py` | Add `get_certification_status()` function |
| `backend/main.py` | Add `GET /api/v1/mills/{mill_id}/certification` endpoint |

---

## Step 1 — `scripts/init_db.py`

Locate the `Mill` SQLModel class. Add one field:

```python
glass_box_certified: bool = Field(default=False)
```

Place it after the existing fields, before any relationships.
Do not change any other fields or table structure.

---

## Step 2 — `backend/revenue_engine.py`

Add the following at the end of the file.

### Imports needed (add only if not already present)
```python
from datetime import datetime, timezone, timedelta
from sqlmodel import Session, select
from scripts.init_db import TokenAllocation, CashReceipt, Mill
from backend.config import CONSERVATIVE_LAG_HOURS
import logging

logger = logging.getLogger(__name__)
```

### Constants (add to `backend/config.py` if not present)
```python
GLASS_BOX_MIN_CYCLES       = 10      # Minimum consecutive clean cycles
GLASS_BOX_MIN_ADHERENCE    = 0.90    # Minimum cash/expected ratio
GLASS_BOX_MAX_DISPUTED     = 0       # Maximum open DISPUTED cycles
GLASS_BOX_MAX_MISSING      = 0       # Maximum MISSING cycles in window
GLASS_BOX_MAX_LAG_HOURS    = 48.0    # Maximum average remittance latency
```

### Function to add to `revenue_engine.py`

```python
def get_certification_status(mill_id: str, session: Session) -> dict:
    """
    Compute Glass Box Certification status for a mill.

    Certification is earned — not assigned. All data is generated automatically
    by the enforcement engine. No manual audit required.

    Criteria (all must pass):
    1. Minimum 10 consecutive CLOSED cycles (no MISSING/DISPUTED interruptions)
    2. Average adherence (cash / expected) >= 90% across those cycles
    3. Zero currently open DISPUTED cycles
    4. Zero MISSING cycles in the last 10 allocations
    5. Average remittance latency < 48 hours

    Returns:
        dict with keys:
            - certified: bool
            - criteria: dict of individual criterion results
            - reason: str | None  (first failing criterion, or None if certified)
            - evaluated_at: str (ISO datetime)
    """
    from backend.config import (
        GLASS_BOX_MIN_CYCLES, GLASS_BOX_MIN_ADHERENCE,
        GLASS_BOX_MAX_DISPUTED, GLASS_BOX_MAX_MISSING,
        GLASS_BOX_MAX_LAG_HOURS, CONSERVATIVE_LAG_HOURS
    )

    criteria = {}
    reason = None

    # ── Fetch last 10 allocations (any status) ───────────────────────────────
    last_10 = session.exec(
        select(TokenAllocation)
        .where(TokenAllocation.mill_id == mill_id)
        .order_by(TokenAllocation.allocated_at.desc())
    ).fetchmany(10)

    # ── Criterion 1: Minimum consecutive CLOSED cycles ───────────────────────
    closed = [a for a in last_10 if a.status == "CLOSED"]
    consecutive_clean = 0
    for alloc in sorted(last_10, key=lambda a: a.allocated_at, reverse=True):
        if alloc.status == "CLOSED":
            consecutive_clean += 1
        else:
            break  # sequence broken

    criteria["consecutive_clean_cycles"] = {
        "value": consecutive_clean,
        "threshold": GLASS_BOX_MIN_CYCLES,
        "pass": consecutive_clean >= GLASS_BOX_MIN_CYCLES
    }
    if not criteria["consecutive_clean_cycles"]["pass"] and not reason:
        reason = f"Insufficient consecutive clean cycles: {consecutive_clean} / {GLASS_BOX_MIN_CYCLES} required"

    # ── Criterion 2: Average adherence >= 90% ────────────────────────────────
    adherence_scores = []
    for alloc in closed:
        receipt = session.exec(
            select(CashReceipt)
            .where(CashReceipt.allocation_id == alloc.id)
        ).first()
        if receipt and receipt.verified:
            adherence_scores.append(
                min(1.0, receipt.amount / alloc.expected_revenue)
            )

    avg_adherence = sum(adherence_scores) / len(adherence_scores) if adherence_scores else 0.0
    criteria["average_adherence"] = {
        "value": round(avg_adherence, 4),
        "threshold": GLASS_BOX_MIN_ADHERENCE,
        "pass": avg_adherence >= GLASS_BOX_MIN_ADHERENCE
    }
    if not criteria["average_adherence"]["pass"] and not reason:
        reason = f"Average adherence too low: {avg_adherence:.1%} / {GLASS_BOX_MIN_ADHERENCE:.0%} required"

    # ── Criterion 3: Zero open DISPUTED cycles ───────────────────────────────
    open_disputed = session.exec(
        select(TokenAllocation)
        .where(
            TokenAllocation.mill_id == mill_id,
            TokenAllocation.status == "DISPUTED"
        )
    ).all()

    criteria["open_disputed"] = {
        "value": len(open_disputed),
        "threshold": GLASS_BOX_MAX_DISPUTED,
        "pass": len(open_disputed) <= GLASS_BOX_MAX_DISPUTED
    }
    if not criteria["open_disputed"]["pass"] and not reason:
        reason = f"Open DISPUTED cycles: {len(open_disputed)}"

    # ── Criterion 4: Zero MISSING in last 10 ────────────────────────────────
    missing_count = len([a for a in last_10 if a.status == "MISSING"])
    criteria["missing_in_window"] = {
        "value": missing_count,
        "threshold": GLASS_BOX_MAX_MISSING,
        "pass": missing_count <= GLASS_BOX_MAX_MISSING
    }
    if not criteria["missing_in_window"]["pass"] and not reason:
        reason = f"MISSING cycles in last 10: {missing_count}"

    # ── Criterion 5: Average remittance latency < 48h ────────────────────────
    lag_values = []
    for alloc in closed:
        receipt = session.exec(
            select(CashReceipt)
            .where(CashReceipt.allocation_id == alloc.id)
        ).first()
        if receipt:
            delta = receipt.received_at - alloc.allocated_at
            lag_values.append(delta.total_seconds() / 3600.0)
        else:
            lag_values.append(CONSERVATIVE_LAG_HOURS)

    avg_lag = sum(lag_values) / len(lag_values) if lag_values else 0.0
    criteria["average_lag_hours"] = {
        "value": round(avg_lag, 2),
        "threshold": GLASS_BOX_MAX_LAG_HOURS,
        "pass": avg_lag < GLASS_BOX_MAX_LAG_HOURS
    }
    if not criteria["average_lag_hours"]["pass"] and not reason:
        reason = f"Average remittance lag too high: {avg_lag:.1f}h / {GLASS_BOX_MAX_LAG_HOURS}h threshold"

    # ── Final result ─────────────────────────────────────────────────────────
    certified = all(c["pass"] for c in criteria.values())

    # Update mill record if status changed
    mill = session.exec(select(Mill).where(Mill.meter_number == mill_id)).first()
    if mill and mill.glass_box_certified != certified:
        mill.glass_box_certified = certified
        session.add(mill)
        session.commit()
        status_str = "GRANTED" if certified else "REVOKED"
        logger.info(f"Glass Box Certification {status_str} for mill {mill_id}")

    return {
        "mill_id": mill_id,
        "certified": certified,
        "criteria": criteria,
        "reason": reason,
        "evaluated_at": datetime.now(timezone.utc).isoformat()
    }
```

---

## Step 3 — `backend/main.py`

Add the following import at the top of main.py (if not present):
```python
from backend.revenue_engine import get_certification_status
```

Add this endpoint. Place it near the other mill-related endpoints:

```python
@app.get("/api/v1/mills/{mill_id}/certification")
def get_mill_certification(mill_id: str, session: Session = Depends(get_session)):
    """
    Returns Glass Box Certification status for a mill.
    Certification is computed live from enforcement data — not cached.
    Automatically updates mill.glass_box_certified on each call.
    """
    try:
        result = get_certification_status(mill_id, session)
        return result
    except Exception as e:
        logger.error(f"Certification check failed for {mill_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Step 4 — Verification

After implementing, run these checks in order:

### 4a. Syntax validation
```bash
python -m py_compile scripts/init_db.py
python -m py_compile backend/revenue_engine.py
python -m py_compile backend/main.py
```

### 4b. Database migration
```bash
python scripts/init_db.py
```
Confirm `glass_box_certified` column appears in the `mill` table:
```bash
python -c "
import sqlite3
db = sqlite3.connect('data/gridledger.db')
cols = [r[1] for r in db.execute('PRAGMA table_info(mill)').fetchall()]
print('glass_box_certified' in cols)
"
```
Expected output: `True`

### 4c. Live check against NABIWI
```bash
python -c "
from scripts.init_db import engine
from sqlmodel import Session
from backend.revenue_engine import get_certification_status
import json

with Session(engine) as session:
    result = get_certification_status('NABIWI', session)
    print(json.dumps(result, indent=2))
"
```

Review the output:
- `certified: true` → issue the first Glass Box mark
- `certified: false` → read `reason` field and `criteria` dict to see which threshold(s) are not yet met

---

## Acceptance Criteria

- [ ] `glass_box_certified` field present in `mill` table after `init_db.py` runs
- [ ] `get_certification_status('NABIWI', session)` returns valid JSON with all 5 criteria
- [ ] `certified` field reflects actual compliance state — not hardcoded
- [ ] Mill record updates automatically when certification status changes
- [ ] Endpoint responds at `GET /api/v1/mills/NABIWI/certification`
- [ ] All syntax validation passes

---

## Notes for Copilot

- Do NOT use `datetime.utcnow()` — use `datetime.now(timezone.utc)` throughout
- Import paths follow `scripts.init_db` pattern (not `backend.init_db`)
- The `Mill` primary key field in this codebase is `meter_number`, not `id`
  — confirm by checking the existing `Mill` model before writing queries
- **Operator IDs are Malawi NRID numbers** — never auto-generate or substitute
  another field. The NRID is the legal identity anchor for every certification.
- Do not add new database tables — all data already exists in `token_allocations`
  and `cash_receipts`
- `get_certification_status()` must be idempotent — safe to call multiple times
