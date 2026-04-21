# 🚀 Quick-Start: Deployment Checklist

**Target:** Go live with Phase 1 + forensic metrics observation  
**Duration:** 2 hours (deploy + verify)  
**First Node:** NABIWI_01

---

## ✅ Pre-Flight (15 min)

- [ ] Activate venv: `.\venv\Scripts\Activate.ps1`
- [ ] Set `$env:SYSTEM_ALLOCATION_ENABLED = "true"`
- [ ] Back up database: `copy data\gridledger.db data\gridledger.db.backup-phase1`
- [ ] Review code changes: verify zero syntax errors (already confirmed April 14)

---

## ✅ Deploy (30 min)

### Step 1: Database Migration

```bash
# Run SQL migration
sqlite3 data\gridledger.db

# Paste in sqlite prompt:
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

# Exit: .quit
```

### Step 2: Start Server

```bash
python backend/main.py
```

**Expected output:**
```
✅ GridLedger Database Initialized.
INFO: Uvicorn running on http://127.0.0.1:8000
```

---

## ✅ Verify (30 min)

### Test 1: API Health
```bash
curl http://localhost:8000/docs
# Expected: 200, Swagger UI loads
```

### Test 2: Decision Endpoint (New Metric)
```bash
curl -X GET http://localhost:8000/api/owner/mills/NABIWI_01/decision \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" | jq .decision_basis.effective_rate_per_kwh
# Expected: 1350.00 (or null if no receipt recorded)
```

### Test 3: Idempotency (New Feature)
```bash
# First request
curl -X POST http://localhost:8000/api/owner/mills/NABIWI_01/allocate-token \
  -H "X-API-Key: your-key" \
  -H "Idempotency-Key: test-001"

# Get allocation_id from response (e.g., 42)

# Second request (duplicate)
curl -X POST http://localhost:8000/api/owner/mills/NABIWI_01/allocate-token \
  -H "X-API-Key: your-key" \
  -H "Idempotency-Key: test-001"

# Expected: Same allocation_id (42), no new allocation
```

### Test 4: Audit Trail (Verify Logging)
```bash
sqlite3 data\gridledger.db "SELECT * FROM decision_audit ORDER BY id DESC LIMIT 1;" | jq .
# Expected: decision_basis_json includes effective_rate_per_kwh
```

### Test 5: Time-Weighted Risk (New Feature)
```bash
# Get decision for mill with pending allocation
curl -X GET http://localhost:8000/api/owner/mills/NABIWI_01/decision \
  -H "X-API-Key: your-key" | jq .decision_basis | grep -E "capital_at_risk|time_weighted_risk"
# Expected: time_weighted_risk ≥ capital_at_risk
```

---

## 📊 First 5 Cycles: Data to Collect

For each allocation cycle:

```bash
# Export after cycle completes
sqlite3 data\gridledger.db << EOF
SELECT 
  allocation_id,
  datetime(timestamp, 'localtime') as time,
  json_extract(decision_basis_json, '$.effective_rate_per_kwh') as rate,
  json_extract(decision_basis_json, '$.capital_at_risk') as risk,
  json_extract(decision_basis_json, '$.time_weighted_risk') as weighted_risk
FROM decision_audit 
WHERE mill_id = 'NABIWI_01' 
ORDER BY timestamp DESC 
LIMIT 1;
EOF
```

**Expected values (Nabiwi):**
- effective_rate_per_kwh: ~1,350 (±0.7%)
- capital_at_risk: 0–5,000 (depends on cycle state)
- time_weighted_risk: ≥ capital_at_risk (increases with age)

---

## 🚨 If Something Goes Wrong

| Issue | Fix |
|-------|-----|
| **Syntax error on startup** | Check imports: `timedelta`, `IdempotencyRecord` |
| **Migration fails** | Table exists? Check: `sqlite3 data\gridledger.db ".tables"` |
| **Effective rate is null** | Normal if no receipt yet. Will populate once receipt recorded. |
| **Idempotency key still allocates twice** | Check: expires_at is in future; key matches exactly (case-sensitive) |
| **API won't start** | Check Python syntax: `python -m py_compile backend/owner_routes.py` |

---

## ✅ Success Criteria

After 5 cycles:

- [x] effective_rate_per_kwh logged for every cycle
- [x] All Nabiwi cycles within 1,340–1,360 band
- [x] Idempotency cache working (duplicate key returns same ID)
- [x] Time-weighted risk computed (≥ capital_at_risk)
- [x] Zero blocking errors
- [x] Audit trail complete and searchable

**Result:** Report "✅ Phase 1 observation phase active"

---

## 📋 Observation Log (Simple)

**Week 1 Template:**

| Date | Cycle | Effective Rate | In Band? | Notes |
|------|-------|---|---|---|
| Apr 15 | 1 | 1,350 | ✅ | Full day |
| Apr 15 | 2 | 1,350 | ✅ | Tokens exhausted |
| Apr 16 | 3 | 1,348 | ✅ | Minor variance (normal) |
| Apr 16 | 4 | 1,350 | ✅ | Full day |
| Apr 17 | 5 | 1,350 | ✅ | Full day |

**Expected outcome:** All ✅ = band is confirmed.

---

## 🚀 Next Steps After 5 Cycles

1. **Export data:** Run SQL query above, save to CSV
2. **Report:** "Nabiwi band confirmed: 1,347 avg, all cycles 1,340–1,360"
3. **Deploy second mill:** Repeat process with Mkwinda
4. **Plan forensic film:** Schedule 1-cycle field observation (after 10 cycles)

---

## 📞 Reference Docs (If Needed)

- **Detailed deployment:** [DEPLOYMENT_STAGING_GUIDE.md](DEPLOYMENT_STAGING_GUIDE.md)
- **Band definition:** [EFFECTIVE_RATE_OBSERVATION_PROTOCOL.md](EFFECTIVE_RATE_OBSERVATION_PROTOCOL.md)
- **Calibration data:** [NABIWI_FEB_MAR_2026_CYCLE_ANALYSIS.md](NABIWI_FEB_MAR_2026_CYCLE_ANALYSIS.md)
- **Executive summary:** [PHASE_1_EXECUTIVE_STATUS.md](PHASE_1_EXECUTIVE_STATUS.md)

---

**Status:** ✅ READY TO DEPLOY  
**Estimated Deploy Time:** 2 hours  
**Next Checkpoint:** After 5 cycles (April 21, 2026 estimated)

**Go live. Observe. Report back.**
