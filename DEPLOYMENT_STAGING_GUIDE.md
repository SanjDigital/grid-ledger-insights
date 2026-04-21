# Deployment & Observation: Staging Setup Guide

**Status:** Code complete, ready for deployment  
**Target Environment:** Staging (or live with single mill)  
**First Observed Node:** Nabiwi (NABIWI_01)  
**Observation Window:** 5–10 cycles (estimated 1–2 weeks)  
**Date:** April 14, 2026

---

## ✅ Pre-Deployment Checklist

### Code Verification
- [x] `scripts/init_db.py` – IdempotencyRecord model added, zero syntax errors
- [x] `backend/owner_routes.py` – All 5 patches applied, zero syntax errors
- [x] Imports verified (timedelta, IdempotencyRecord)
- [x] Model changes validated (DecisionBasis has time_weighted_risk + effective_rate_per_kwh)
- [x] Function signatures updated (_compute_capital_at_risk returns tuple)
- [x] All callers updated (4 sites unpacking tuple correctly)
- [x] Helper functions added (_time_weighted_risk, _compute_effective_rate_per_kwh)

### Database Preparation
- [x] Migration SQL prepared (IdempotencyRecord table creation)
- [x] Schema changes minimal (no breaking changes)
- [x] Backward compatibility maintained (effective_rate is Optional, defaults to None)

### Configuration
- [x] SYSTEM_ALLOCATION_ENABLED environment variable defined
- [x] Nabiwi observation band documented (1,340–1,360)
- [x] Phase 1 default band documented (1,100–1,500)
- [x] No enforcement logic added (observation only)

### Documentation
- [x] PHASE_1_IMPLEMENTATION.md (idempotency + time-weighted risk)
- [x] NABIWI_CYCLE_CALIBRATION.md (ground truth baseline)
- [x] NABIWI_FEB_MAR_2026_CYCLE_ANALYSIS.md (19-cycle forensic extraction)
- [x] EFFECTIVE_RATE_OBSERVATION_PROTOCOL.md (monitoring & band rules)

---

## 🚀 Deployment Steps (Staging)

### Step 1: Environment Setup (Hour 1)

```bash
# Navigate to project
cd c:\Users\USER\Documents\Python\ Projets\gridledger

# Activate venv
.\venv\Scripts\Activate.ps1

# Set environment variables
$env:SYSTEM_ALLOCATION_ENABLED = "true"
$env:OWNER_API_KEY = "your-staging-key-here"  # Update as needed

# Verify venv
python --version
```

### Step 2: Database Migration (Hour 1)

```bash
# Back up current database
copy data\gridledger.db data\gridledger.db.backup-pre-observation

# Run migration (using SQLite CLI or Python)
# Option A: Using sqlite3 directly
sqlite3 data\gridledger.db < scripts\p1_migration.sql

# Option B: Using Python
python -c "
from scripts.init_db import create_db_and_tables
create_db_and_tables()  # WARNING: This drops all tables – use only for fresh setup
"

# For staging (preserving existing data), run migration manually:
# sqlite3 data\gridledger.db
# > CREATE TABLE idempotency_records (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     idempotency_key TEXT NOT NULL UNIQUE,
#     mill_id TEXT NOT NULL,
#     ...
#   );
```

**SQL Migration:**
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

### Step 3: Start API Server (Hour 1)

```bash
# Start development server
python backend/main.py

# Expected output:
# ✅ GridLedger Database Initialized.
# INFO:     Uvicorn running on http://127.0.0.1:8000
# INFO:     Application startup complete
```

### Step 4: Verify Deployment (Hour 1)

```bash
# Test 1: Health check
curl -X GET http://localhost:8000/docs

# Expected: Swagger UI loads (200)

# Test 2: Decision endpoint (read-only, no side effects)
curl -X GET http://localhost:8000/api/owner/mills/NABIWI_01/decision \
  -H "X-API-Key: your-staging-key" \
  -H "Content-Type: application/json"

# Expected response includes:
# {
#   "allowed": true/false,
#   "decision_basis": {
#     "effective_rate_per_kwh": 1350.00,  # NEW FIELD
#     ...
#   }
# }

# Test 3: Idempotency test (creates allocation, stores in cache)
curl -X POST http://localhost:8000/api/owner/mills/NABIWI_01/allocate-token \
  -H "X-API-Key: your-staging-key" \
  -H "Idempotency-Key: test-key-001" \
  -H "Content-Type: application/json"

# Expected: 200 OK, allocation_id returned

# Test 4: Duplicate request (should return cached response)
curl -X POST http://localhost:8000/api/owner/mills/NABIWI_01/allocate-token \
  -H "X-API-Key: your-staging-key" \
  -H "Idempotency-Key: test-key-001" \
  -H "Content-Type: application/json"

# Expected: Same allocation_id, no new allocation created
```

### Step 5: Enable Logging (Hour 1–2)

```bash
# Ensure logging captures effective_rate_per_kwh
# In backend/owner_routes.py, verify _store_decision_audit includes:
#   decision_basis.model_dump_json() captures effective_rate_per_kwh

# Check audit table
sqlite3 data\gridledger.db "SELECT allocation_id, decision_basis_json FROM decision_audit LIMIT 1;" | jq .

# Should show effective_rate_per_kwh in decision_basis_json
```

---

## 📊 Observation Window: First 5–10 Cycles

### What to Monitor

| Metric | Expected | Captured By |
|--------|----------|---|
| **Effective rate per cycle** | 1,340–1,360 for Nabiwi | decision_basis.effective_rate_per_kwh |
| **Band status** | All in_band: true | audit trail |
| **Variance from budgeted** | ±0.7% | (effective_rate - 1350) / 1350 |
| **Idempotency hits** | Each retry returns cached | idempotency_records table row count |
| **Time-weighted risk** | Increases over cycle age | decision_basis.time_weighted_risk |
| **No blocking errors** | 0 allocation failures | error logs |

### Cycle Observation Log Template

**For each allocation cycle, record:**

```json
{
  "cycle_number": 1,
  "date": "2026-04-15",
  "mill_id": "NABIWI_01",
  "allocation": {
    "allocated_kwh": 59.9,
    "expected_revenue": 80855.00
  },
  "execution": {
    "actual_revenue": 81000,
    "actual_kwh": 64.8,
    "time_to_receipt": "4 hours"
  },
  "forensic_metrics": {
    "effective_rate_per_kwh": 1350.00,
    "variance_from_budgeted": 0.0,
    "band_status": "in_band",
    "time_weighted_risk_multiplier": 1.0
  },
  "idempotency": {
    "used_idempotency_key": "nabiwi-2026-04-15-001",
    "cache_hit": false,
    "notes": "First cycle, no cache hit expected"
  },
  "operator_notes": "Full 60 buckets, tokens exhausted mid-day",
  "flags": []
}
```

### Data Export (After Each Week)

```sql
-- Export audit trail with effective_rate metrics
SELECT 
  a.id,
  a.mill_id,
  a.timestamp,
  a.allowed,
  json_extract(a.decision_basis_json, '$.effective_rate_per_kwh') as effective_rate,
  json_extract(a.decision_basis_json, '$.capital_at_risk') as capital_at_risk,
  json_extract(a.decision_basis_json, '$.time_weighted_risk') as time_weighted_risk,
  a.allocation_id
FROM decision_audit a
WHERE a.mill_id = 'NABIWI_01'
ORDER BY a.timestamp DESC
LIMIT 10;
```

---

## 🔍 Observation Dashboard (Manual Weekly)

### Week 1 Template

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| **Nabiwi cycles observed** | 5–10 | — | 🔄 In progress |
| **Avg effective rate** | 1,347 | — | 🔄 In progress |
| **Min effective rate** | >1,300 | — | 🔄 In progress |
| **Max effective rate** | <1,400 | — | 🔄 In progress |
| **All cycles in band** | 100% | — | 🔄 In progress |
| **Out-of-band flags** | 0 | — | 🔄 In progress |
| **Idempotency tests passed** | 100% | — | 🔄 In progress |
| **Time-weighted risk computed** | 100% | — | 🔄 In progress |
| **Audit trail complete** | 100% | — | 🔄 In progress |
| **API errors** | 0 | — | 🔄 In progress |

### Week 2 Template (After Second Mill)

| Metric | Nabiwi | Mkwinda (or other) | Status |
|--------|--------|---|---|
| **Cycles observed** | 10+ | 5–10 | 🔄 In progress |
| **Band established** | ✅ 1,340–1,360 | 🔄 Establishing | 🔄 |
| **Avg effective rate** | 1,347 | — | 🔄 |
| **Variance** | ±0.2% | — | 🔄 |
| **Fraud risk** | LOW | — | 🔄 |

---

## ⚠️ Troubleshooting (If Deployed)

### Issue: Syntax Errors on Startup

```
File "backend/owner_routes.py", line XXX: SyntaxError: invalid syntax
```

**Solution:**
1. Check imports at top of file (timedelta, IdempotencyRecord)
2. Verify DecisionBasis model has all fields
3. Run: `python -m py_compile backend/owner_routes.py` to verify

### Issue: Database Migration Fails

```
sqlite3.OperationalError: table idempotency_records already exists
```

**Solution:**
- If first deployment: run migration as shown above
- If re-deploying: migration is idempotent (check if table exists first)

### Issue: Effective Rate Shows None/Null

```json
{
  "effective_rate_per_kwh": null
}
```

**Cause:** Cycle has no receipt recorded yet (or receipt.amount = 0)

**Expected**: Normal for PENDING cycles. Once receipt is recorded, effective_rate_per_kwh will populate.

### Issue: Idempotency Key Always Passes (Cache Not Working)

**Check:**
1. Verify IdempotencyRecord table has data: `SELECT COUNT(*) FROM idempotency_records;`
2. Verify expires_at is in future: `SELECT idempotency_key, expires_at, datetime('now') FROM idempotency_records;`
3. Verify idempotency_key matches (case-sensitive): Check X-Idempotency-Key header spelling

---

## 📋 Post-Deployment Checklist (Day 1)

- [ ] Server starts without errors
- [ ] `/docs` endpoint loads (Swagger UI)
- [ ] Decision endpoint returns decision_basis with effective_rate_per_kwh
- [ ] First allocation succeeds and logs to audit trail
- [ ] Idempotency test works (duplicate key returns same allocation_id)
- [ ] Database contains idempotency_records entries
- [ ] Time-weighted risk is computed for pending cycles
- [ ] No blocking errors from band logic (observation only)
- [ ] Audit trail JSON is valid and parseable

---

## 📊 Success Criteria (First Week)

### If True → Proceed to Week 2
- [ ] 5–10 Nabiwi cycles observed
- [ ] All cycles have effective_rate_per_kwh logged
- [ ] All cycles within observation band (1,340–1,360)
- [ ] Zero blocking errors from new code
- [ ] Audit trail is complete and searchable
- [ ] Idempotency cache working (verified by duplicate test)
- [ ] Time-weighted risk multiplier computed correctly

### If False → Debug and Fix
- [ ] Any cycles outside band → investigate (check cycle data)
- [ ] Any cycles with null effective_rate → expected (normal behavior)
- [ ] Any blocking errors → revert and check code syntax
- [ ] Idempotency cache not working → verify table/expires_at logic

---

## 📈 What Happens After 5–10 Cycles

### Data Review Meeting

**Agenda:**
1. Review effective_rate_per_kwh data
2. Confirm band holds (1,340–1,360 for Nabiwi)
3. Discuss any anomalies
4. Plan second mill deployment
5. Decide if band should be tightened

**Expected Outcome:**
- Nabiwi band confidence: HIGH (identical to Feb–Mar 2026 data)
- Next mill baseline: ESTABLISHING (need 5–10 cycles)
- Enforcement timeline: DEFER (wait for 2 mills calibrated + forensic film)

---

## 🎯 15-Day Roadmap

| Day | Milestone | Action |
|-----|-----------|--------|
| **Day 1** | Deploy to staging | Start server, run tests, first 2 cycles |
| **Day 2–3** | First 5 cycles | Monitor, confirm band holds |
| **Day 4** | Nabiwi baseline confirmed | Document ✅ |
| **Day 5–7** | Deploy second mill | Set up Mkwinda, run first 3 cycles |
| **Day 8–10** | Second mill baseline | Collect 5–10 cycles, establish mill-specific band |
| **Day 11–14** | Forensic film prep | Schedule field visit to Nabiwi (1–2 cycles) |
| **Day 15** | Data review + decision | Tighten band? Add enforcement? Plan Move B (ESCOM)? |

---

## 🚀 Go/No-Go Decision

**Code Status:** ✅ READY (zero syntax errors)  
**Calibration:** ✅ READY (Nabiwi 19-cycle baseline)  
**Protocol:** ✅ READY (observation framework documented)  
**Database Migration:** ✅ READY (SQL prepared)  
**Testing:** ✅ READY (curl commands specified)  

**Recommendation:** **GO FOR DEPLOYMENT**

You can deploy to staging today and begin observation phase. No blockers.

---

**Deployment Guide Created:** April 14, 2026  
**First Observation Node:** NABIWI_01  
**Observation Duration:** 1–2 weeks  
**Next Checkpoint:** After 5 cycles, report band status
