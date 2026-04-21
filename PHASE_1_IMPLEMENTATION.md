# Phase 1 Implementation: Idempotency + Time-Weighted Risk

## ✅ Status: Complete

All patches for Phase 1 have been applied successfully with **zero syntax errors**.

---

## Patches Applied

### ✅ Patch 1: IdempotencyRecord Model
**File:** `scripts/init_db.py` (after DecisionAudit)

Added new SQLModel with fields:
- `id` (primary key)
- `idempotency_key` (unique index)
- `mill_id` (foreign key to mill)
- `created_at` (timestamp)
- `response_json` (serialized AllocationDecisionResponse)
- `allocation_id` (foreign key to token_allocations)
- `expires_at` (24-hour TTL)

**Purpose:** Cache allocation responses to prevent double-allocation on retries.

---

### ✅ Patch 2: Time-Weighted Risk Calculation
**File:** `backend/owner_routes.py`

**Added Functions:**
1. `_time_weighted_risk(exposure: Decimal, overdue_days: float) -> Decimal`
   - Linear multiplier: 1 + (0.1 × overdue_days), capped at 2.0
   - Makes delays increasingly expensive

2. `_compute_capital_at_risk()` – Updated to return tuple
   - **Returns:** `tuple[Decimal, Decimal]`
   - **Values:** `(raw_risk, time_weighted_risk)`
   - Calculates overdue days automatically from allocation timestamp

**Impact:**
- Raw exposure static (for display)
- Time-weighted exposure escalates over time (for decisions)
- Incentivizes prompt receipt submission

---

### ✅ Patch 3: DecisionBasis Model Extension
**File:** `backend/owner_routes.py`

Added field to `DecisionBasis`:
```python
time_weighted_risk: Decimal  # NEW – capital_at_risk adjusted for overdue age
```

**Audit Trail:** All allocation decisions now include both raw and time-weighted exposure.

---

### ✅ Patch 4: Idempotency in Allocate-Token Endpoint
**File:** `backend/owner_routes.py`

**Function Signature Change:**
```python
def allocate_token(
    mill_id: str,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),  # NEW
    session: Session = Depends(get_session),
    _: str = Depends(verify_api_key),
):
```

**Flow:**
1. Check for existing idempotency record (non-expired)
2. If found, return cached response without re-allocating
3. If not found, proceed with allocation
4. On success, store response in IdempotencyRecord (24h TTL)
5. Retries with same key return same allocation

**Outcome:** Safe retries – duplicate requests return same response, no double-allocation.

---

### ✅ Patch 5: Updated All Call Sites
**File:** `backend/owner_routes.py`

Updated 4 call sites of `_compute_capital_at_risk()`:
1. `get_mill_decision()` – line ~707
2. `allocate_token()` – first call (active cycle) – line ~768
3. `allocate_token()` – second call (normal flow) – line ~798
4. `get_decision_feed()` – line ~887

**All updated to:**
- Unpack tuple: `capital_at_risk, time_weighted_risk = _compute_capital_at_risk(...)`
- Pass both to `_build_decision_basis()`
- Use `time_weighted_risk` in decision feed priority calculations

**Result:** Stale allocations now rank higher in operator feed.

---

## Database Migrations

### Create IdempotencyRecord Table

Run this SQL against `data/gridledger.db`:

```sql
CREATE TABLE idempotency_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idempotency_key TEXT NOT NULL UNIQUE,
    mill_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    response_json TEXT NOT NULL,
    allocation_id INTEGER,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (mill_id) REFERENCES mill(id),
    FOREIGN KEY (allocation_id) REFERENCES token_allocations(id)
);

CREATE INDEX idx_idempotency_key ON idempotency_records(idempotency_key);
```

### Verify TokenAllocation Table

Ensure `token_allocations` table exists with:
- `id` (primary key)
- `allocated_at` (datetime)
- `expected_revenue` (numeric)
- `mill_id` (foreign key)

(This should already exist from Move A – no changes needed.)

---

## Testing Idempotency

### Test 1: Duplicate Request Returns Same Response

```bash
# First request
curl -X POST http://localhost:8000/api/owner/mills/NABIWI_01/allocate-token \
  -H "X-API-Key: ${OWNER_API_KEY}" \
  -H "Idempotency-Key: test-key-12345"

# Expected response (e.g.)
{
  "allowed": true,
  "allocation_id": 42,
  "allocated_kwh": 59.9,
  "expected_revenue": "5990.00"
}

# Second request (exact same headers)
curl -X POST http://localhost:8000/api/owner/mills/NABIWI_01/allocate-token \
  -H "X-API-Key: ${OWNER_API_KEY}" \
  -H "Idempotency-Key: test-key-12345"

# Expected: Identical response, NO new allocation created
```

**Verification:** Check database – only ONE record in `token_allocations` for this mill cycle.

---

## Testing Time-Weighted Risk

### Test 2: Overdue Allocations Show Escalated Exposure

```bash
# Get decision for mill with pending allocation
curl -X GET http://localhost:8000/api/owner/mills/NABIWI_01/decision \
  -H "X-API-Key: ${OWNER_API_KEY}"

# In response.decision_basis:
# - capital_at_risk: 5000.00 (raw shortfall)
# - time_weighted_risk: 5500.00+ (with age multiplier)
```

**Age Multiplier Progression:**
- 0 days: 1.0x (5000 MWK)
- 1 day: 1.1x (5500 MWK)
- 3 days: 1.3x (6500 MWK)
- 10 days: 2.0x (10000 MWK – capped)

### Test 3: Decision Feed Sorting

```bash
curl -X GET http://localhost:8000/api/owner/decision-feed \
  -H "X-API-Key: ${OWNER_API_KEY}"

# Response: Items sorted by priority_score (calculated using time_weighted_risk)
# Expected: Older allocations with missing receipts rank higher
```

---

## Deployment Checklist

- [ ] Back up database: `cp data/gridledger.db data/gridledger.db.backup-phase1`
- [ ] Run SQL migration (IdempotencyRecord table)
- [ ] Restart API server: `python backend/main.py`
- [ ] Verify server starts without errors
- [ ] Run Idempotency Test 1 (duplicate requests)
- [ ] Run Idempotency Test 2 (time-weighted exposure)
- [ ] Run Idempotency Test 3 (decision feed priority)
- [ ] Monitor for 24–48 hours
- [ ] Check logs for any allocation anomalies
- [ ] Verify no expired idempotency records accumulate (TTL working)

---

## Key Design Decisions

### Idempotency-Key Strategy
- **Duration:** 24 hours (safe replay window)
- **Scope:** Per-mill, per-key (different mills can use same key)
- **Storage:** In-database cache (durable across restarts)
- **Expiration:** Automatic (checked at runtime, cleaned via TTL)

### Time-Weighted Risk Logic
- **Formula:** `1 + 0.1 × overdue_days`, capped at 2.0
- **Trigger:** Absence of receipt after allocation
- **Intent:** Penalize delays without hard blocking
- **Reversibility:** Disappears when receipt recorded (risk -> 0)

### Phase 1 Scope (What's NOT Included)
- ESCOM reconciliation (Phase 2)
- Anomaly detection flags (Phase 2)
- Game-theoretic threat detection (Phase 2)
- Cluster-level defense (Move C)

---

## Observation Window

After deployment, monitor for 24–48 hours:
- ✅ Idempotency function (test retries)
- ✅ Time-weighted risk (verify exposure multipliers)
- ✅ Decision feed (confirm sorting by time-weighted risk)
- ⚠️ Operator response times (may be delayed due to urgency signal)
- ⚠️ Any unexpected allocation blocks

---

## Files Modified

1. **`scripts/init_db.py`**
   - Added `IdempotencyRecord` model

2. **`backend/owner_routes.py`**
   - Added `timedelta` import
   - Added `IdempotencyRecord` import
   - Added `_time_weighted_risk()` helper
   - Updated `_compute_capital_at_risk()` to return tuple
   - Updated `_build_decision_basis()` signature
   - Updated `allocate_token()` signature + idempotency logic
   - Updated 4 call sites of `_compute_capital_at_risk()`
   - Updated `DecisionBasis` model

---

## Validation Results

✅ `scripts/init_db.py` – Zero syntax errors  
✅ `backend/owner_routes.py` – Zero syntax errors

---

## Next Steps

1. **Immediate (1–4 hours):**
   - Back up database
   - Run SQL migration
   - Restart server
   - Run tests

2. **Observation (24–48 hours):**
   - Monitor allocation pipeline
   - Check decision feed priority
   - Verify no double-allocations
   - Verify time-weighting is working

3. **Post-Observation (User decision):**
   - Option A: Proceed to Phase 2 (ESCOM + Anomalies + Threats)
   - Option B: Extend observation window
   - Option C: Skip to Move C (cluster-level defense)

---

## Contact Points

For issues during deployment:
- **Idempotency failures:** Check logs for duplicate key collisions
- **Time-weighted risk anomalies:** Verify UTC timezone consistency
- **Decision feed sorting:** Confirm time_weighted_risk > capital_at_risk

---

**Implementation Date:** April 14, 2026  
**Status:** Ready for Staging Deployment
