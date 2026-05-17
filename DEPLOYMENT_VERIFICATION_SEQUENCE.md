# Deployment Verification Sequence — Nabiwi Live Anchor
**Date**: May 5, 2026  
**Status**: Pre-Deployment Verification Checklist  
**Authority**: FL00R G3N3RAL + Engineering  

---

## CRITICAL PRE-DEPLOYMENT GAP: Timestamp Canonicalisation

**Why This Matters**: All five pre-flight tests pass with hardcoded UTC timestamps. Production will receive datetimes from `receipt.received_at` — a database datetime object. If serialisation is not exactly `YYYY-MM-DDTHH:MM:SSZ` (20 characters, UTC, Z suffix, no microseconds), the seal computed by the anchor verification script will **not match** the seal in the GitHub CSV.

The chain will appear **broken to any auditor** who tries to verify Cycle 1.

This is the one failure mode that silent anchor failures **cannot catch** — the seal commits to GitHub successfully, but it's the wrong seal.

### Pre-Deployment Verification (Required Before Touching Production)

Run this **exactly once** against the production database before the first live cycle:

```python
# PRODUCTION DB VERIFICATION - Run before Cycle 1
from backend.cycle_manager import reconcile_cycle
from scripts.init_db import get_session
from sqlmodel import select
from backend.models import CashReceipt

print("=" * 80)
print("TIMESTAMP CANONICALISATION VERIFICATION")
print("=" * 80)

with get_session() as session:
    receipt = session.exec(
        select(CashReceipt).order_by(CashReceipt.received_at.desc())
    ).first()
    
    if receipt:
        print(f"\n✓ Found receipt in production DB")
        print(f"  Raw received_at type: {type(receipt.received_at)}")
        print(f"  Raw received_at value: {receipt.received_at}")
        
        # Attempt canonical format
        try:
            canonical = receipt.received_at.strftime("%Y-%m-%dT%H:%M:%SZ")
            print(f"\n✓ Canonical format: {canonical}")
            print(f"  Length: {len(canonical)} chars (expected: 20)")
            
            # Verify format
            if len(canonical) == 20 and canonical[-1] == 'Z':
                print(f"\n✅ PASS: Timestamp canonicalisation correct")
                print(f"   Ready for production deployment")
            else:
                print(f"\n❌ FAIL: Format incorrect")
                print(f"   Expected: YYYY-MM-DDTHH:MM:SSZ (20 chars)")
                print(f"   Got: {canonical} ({len(canonical)} chars)")
                raise ValueError("Canonicalisation format mismatch")
        
        except Exception as e:
            print(f"\n❌ FAIL: Serialisation error: {e}")
            print(f"   Fix the timestamp serialisation before deploying")
            raise
    else:
        print(f"\n⚠ WARNING: No receipts in database")
        print(f"  Run test with actual data or live receipt")

print("\n" + "=" * 80)
```

**Expected Output**:
```
✓ Found receipt in production DB
  Raw received_at type: <class 'datetime.datetime'>
  Raw received_at value: 2026-05-05 10:32:45
  
✓ Canonical format: 2026-05-05T10:32:45Z
  Length: 20 chars (expected: 20)

✅ PASS: Timestamp canonicalisation correct
   Ready for production deployment
```

**If Output Does Not Match**:
- Do not proceed to Cycle 1
- Diagnose the serialisation in `backend/cycle_manager.py`
- Fix the timestamp conversion path
- Re-run verification
- Only proceed when verification passes

---

## PRE-DEPLOYMENT CHECKLIST

Complete **all checks** before first live cycle. Do not skip any item.

### Infrastructure & Configuration

- [ ] **GitHub Token**: Confirm `GITHUB_TOKEN` set in production environment
  ```bash
  export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
  # Test:
  curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user | grep login
  # Expected: GitHub username appears
  ```

- [ ] **GitHub Repository**: Confirm private repo accessible
  ```bash
  curl -H "Authorization: token $GITHUB_TOKEN" \
    https://api.github.com/repos/gridledger/gridledger-cycle-seals
  # Expected: 200 OK response with repo metadata
  ```

- [ ] **Timestamp Canonicalisation**: Run verification script above
  ```
  Expected: ✅ PASS message
  ```

- [ ] **Single-Worker Mode**: Confirm `--workers 1` in production start command
  ```bash
  # Verify startup command uses:
  uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1
  # NOT: --workers 4 or default (which defaults to CPU count)
  ```

### Database Schema

- [ ] **Migration Status**: Confirm cycle table has new columns
  ```bash
  sqlite3 gridledger.db "SELECT name FROM pragma_table_info('cycle') 
    WHERE name IN ('cycle_number','previous_seal','cycle_seal',
                   'anchor_status','anchor_retries')"
  # Expected: 5 rows returned
  #   cycle_number
  #   previous_seal
  #   cycle_seal
  #   anchor_status
  #   anchor_retries
  ```

### Runtime Verification

- [ ] **Anchor Daemon**: Confirm anchor worker thread starts on backend launch
  ```bash
  # Watch backend logs for:
  # "Anchor worker thread started"
  # Expected on every backend startup
  ```

---

## DEPLOYMENT SEQUENCE — NABIWI LIVE

### CYCLE 1 — FIRST LIVE ANCHOR

**Prerequisite**: All checks above passing ✅

1. **Issue Token**
   - [ ] Token allocation to Nabiwi node via standard flow
   - [ ] Confirm allocation recorded in `TokenPurchase` table

2. **Operator Production & Remittance**
   - [ ] Operator produces energy (standard capacity constrained by token)
   - [ ] Cash remitted via Airtel Money
   - [ ] Receipt received and recorded

3. **Record Cash Receipt**
   - [ ] POST to `/api/owner/mills/NABIWI_01/record-cash-receipt`
   - [ ] Confirm HTTP 200 response
   - [ ] Verify receipt appears in database

4. **Trigger Reconciliation**
   - [ ] Backend calls `reconcile_cycle()` automatically (or manually if needed)
   - [ ] Confirm completion without errors in logs
   - [ ] Check decision feed for reconciliation status

5. **Verify Cycle Record**
   ```bash
   sqlite3 gridledger.db "SELECT cycle_number, cycle_seal, anchor_status, anchor_retries 
     FROM cycle WHERE mill_id='NABIWI_01' ORDER BY cycle_number DESC LIMIT 1"
   ```
   - [ ] `cycle_seal` is 64-character hexadecimal string
   - [ ] `anchor_status` = `ANCHORED`
   - [ ] `anchor_retries` = 0 (or 1-2 if transient retry occurred)

6. **Verify GitHub Seal Committed**
   ```bash
   curl https://raw.githubusercontent.com/gridledger/gridledger-cycle-seals/main/seal_log.csv | tail -1
   ```
   - [ ] Row present in seal log
   - [ ] Format: `cycle_number, mill_id_hash, previous_seal, cycle_seal, timestamp`
   - [ ] Seal matches database record

7. **Independently Verify Cycle 1 Seal** (Critical)
   ```python
   import json
   import hashlib
   
   # Populate from DB record
   cycle_data = {
       "cycle_number": 1,
       "mill_id": "NABIWI_01",
       "token_id": "...",
       "revenue_rate_per_kwh": ...,
       "total_usage_kwh": ...,
       "total_actual_cash": ...,
       "expected_revenue": ...,
       "variance": ...,
       "settled_at": "2026-05-05T10:32:45Z",  # Must be this exact format
       "previous_seal": "genesis_seal_nabiwi",
   }
   
   seal = hashlib.sha256(
       json.dumps(cycle_data, sort_keys=True).encode()
   ).hexdigest()
   
   github_seal = "[paste from seal_log.csv]"
   
   if seal == github_seal:
       print("✅ Cycle 1 seal independently verified")
   else:
       print(f"❌ SEAL MISMATCH")
       print(f"  Computed: {seal}")
       print(f"  GitHub:   {github_seal}")
       raise AssertionError("Seal verification failed")
   ```
   - [ ] Script produces `✅ Cycle 1 seal independently verified`
   - [ ] If mismatch: **STOP. Do not proceed. Diagnose serialisation.**

### CYCLE 2 — CHAIN CONTINUITY VERIFICATION

**Prerequisite**: Cycle 1 seal verified and committed ✅

1. **Issue Second Token**
   - [ ] Standard allocation flow

2. **Complete Production & Remittance**
   - [ ] Operator produces energy
   - [ ] Cash remitted via Airtel Money

3. **Record Receipt & Reconcile**
   - [ ] Receipt recorded
   - [ ] Reconciliation completes

4. **Verify Cycle 2 Chain Incorporation** (Critical)
   ```bash
   sqlite3 gridledger.db "SELECT previous_seal FROM cycle 
     WHERE mill_id='NABIWI_01' ORDER BY cycle_number DESC LIMIT 1"
   # Expected: 64-char hex matching Cycle 1 seal
   ```
   - [ ] `previous_seal` = Cycle 1's `cycle_seal` (exactly)

5. **Independently Verify Chain** (Critical)
   ```python
   import json
   import hashlib
   
   # Cycle 2 data with Cycle 1 seal as previous_seal
   cycle2_data = {
       "cycle_number": 2,
       "mill_id": "NABIWI_01",
       "previous_seal": "[Cycle 1 seal from step 4]",
       # ... other fields
   }
   
   seal2 = hashlib.sha256(
       json.dumps(cycle2_data, sort_keys=True).encode()
   ).hexdigest()
   
   github_seal2 = "[paste from seal_log.csv row 2]"
   
   if seal2 == github_seal2:
       print("✅ Chain continuity verified — tamper-evident link established")
   else:
       print(f"❌ CHAIN VERIFICATION FAILED")
       raise AssertionError("Chain continuity broken")
   ```
   - [ ] Script produces `✅ Chain continuity verified`
   - [ ] If mismatch: **STOP. Do not authorize secondary mill.**

6. **Verify Decision Feed** (No Anchor Alerts)
   ```bash
   curl -H 'X-API-Key: owner-secret' http://localhost:8000/api/owner/decision-feed
   ```
   - [ ] No `SEAL_ANCHOR_FAILED` alerts
   - [ ] No `SEAL_ANCHOR_PENDING` alerts
   - [ ] Both cycles show `ANCHORED` status

### POST-CYCLE 2 — OPERATIONAL REPORTING

- [ ] Record Cycle 1 seal hash (64-char hex)
- [ ] Record Cycle 1 GitHub commit URL
- [ ] Record Cycle 2 seal hash (64-char hex)
- [ ] Record Cycle 2 GitHub commit URL
- [ ] Screenshot `seal_log.csv` with both rows visible
- [ ] Measure timestamp delta (cycle close to GitHub commit)
  - Expected: < 60 seconds under normal GitHub connectivity
  - Note any delays (GitHub API latency, network issues)

---

## FIRST ANCHOR REPORT FORMAT

**Do not report status. Report evidence.**

This report must be delivered to FL00R G3N3RAL before authorising secondary mill deployment:

```
NABIWI LIVE ANCHOR — FIRST REPORT
Date: 2026-05-05
Reported by: [Your Name / Team]

CYCLE 1
───────
Seal (64-char hex):   [paste exact value]
GitHub Commit URL:    [github.com/gridledger/gridledger-cycle-seals/commit/...]
Timestamp (settled_at): [exact format from DB, e.g., 2026-05-05T10:32:45Z]
Chain Link: Genesis → Cycle 1 (anchored)

CYCLE 2
───────
Seal (64-char hex):   [paste exact value]
GitHub Commit URL:    [github.com/gridledger/gridledger-cycle-seals/commit/...]
Timestamp (settled_at): [exact format from DB]
Chain Link: Cycle 1 → Cycle 2 (verified)

CHAIN VERIFICATION
──────────────────
Independent Recomputation Script:
  Cycle 1: PASS / FAIL
  Cycle 2: PASS / FAIL
  Chain Continuity: YES / NO

If YES:
  ✅ Tamper-evident chain established
  ✅ 32-month forensic record has successor
  ✅ Ready for secondary mill deployment

If NO:
  ❌ STOP
  Diagnosis: [what serialisation issue was found]
  Fix Applied: [what was changed in serialisation path]
  Next Action: Redeploy and rerun Cycle 1

SYSTEM STATUS
─────────────
anchor_status (Cycle 1): ANCHORED
anchor_status (Cycle 2): ANCHORED
anchor_retries (Cycle 1): [0/1/2]
anchor_retries (Cycle 2): [0/1/2]

Anchor Latency (cycle close → GitHub commit):
  Cycle 1: [X seconds]
  Cycle 2: [Y seconds]
  Expected: < 60 seconds

Decision Feed Alerts: NONE (no SEAL_ANCHOR failures)

AUTHORIZATION
──────────────
This report authorises:
[ ] Proceed to secondary mill deployment
[ ] Update RBM brief from "externally anchored" to "live-anchored with verified chain"
```

---

## IF CHAIN VERIFICATION FAILS

**Stop immediately. Do not proceed.**

Diagnostic steps:
1. Compare computed seal vs. GitHub seal character-by-character
2. Check timestamp format in cycle data vs. database
3. Verify `previous_seal` is included in Cycle 2 computation
4. Check JSON serialisation order (must use `sort_keys=True`)
5. Verify all numeric fields are in correct types (not string representations)

**Common Issues**:
- Timestamp has microseconds: `2026-05-05T10:32:45.123456Z` (❌ strip them)
- Timestamp uses offset instead of Z: `2026-05-05T10:32:45+00:00` (❌ use Z)
- Timestamp is naive (no timezone): `2026-05-05T10:32:45` (❌ add `Z`)
- JSON fields are stringified: `"total_usage_kwh": "59.9"` (❌ use numeric)
- Field order is not sorted: `json.dumps(data)` (❌ use `sort_keys=True`)

After fix, redeploy backend and restart Cycle 1.

---

## SEAL MISMATCH RESPONSE PROTOCOL

**Triggered when**: Independent seal recomputation does not match GitHub CSV

**Action**: Stop immediately. Do not proceed to Cycle 2. Do not issue further tokens. Do not report the cycle as verified.

### Diagnostic Sequence (In Order)

#### Step 1 — Isolate the Timestamp

```python
print("TIMESTAMP ISOLATION")
print(f"settled_at from cycle_data: {cycle_data['settled_at']}")
print(f"settled_at from GitHub CSV:  [paste from seal_log.csv]")
```

- If they differ: **the serialisation path is the failure point**
  
**Fix**: Enforce `strftime("%Y-%m-%dT%H:%M:%SZ")` at the point of `cycle_data` dict construction, not at storage:

```python
# WRONG: serialise at storage time
cycle.settled_at = receipt.received_at  # loses format control

# CORRECT: serialise immediately when building cycle_data
cycle_data = {
    "settled_at": receipt.received_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    ...
}
```

---

#### Step 2 — Isolate the Mill ID

```python
print("MILL ID ISOLATION")
print(f"mill_id in cycle_data: {cycle_data['mill_id']}")
print(f"mill_id_hash in GitHub: [paste from seal_log.csv]")
```

**Note**: The seal uses **raw `mill_id`** for computation. The CSV uses **SHA256(mill_id)** for the public record. This is correct and expected.

**Verify**: Your recomputation script uses raw `mill_id`, not the hash.

```python
# In recomputation script
cycle_data = {
    "mill_id": "NABIWI_01",  # CORRECT: raw mill_id
    ...
}
# NOT:
cycle_data = {
    "mill_id_hash": "abc123...",  # WRONG: uses the hash
    ...
}
```

If your script used the hash: **script error, not seal error.**

**Fix**: Update recomputation script to use raw `mill_id`.

---

#### Step 3 — Isolate JSON Serialisation

```python
import json

serialised = json.dumps(cycle_data, sort_keys=True)
print(f"Serialised (no encoding): {serialised}")
print(f"Bytes: {serialised.encode('utf-8')}")
print(f"Length: {len(serialised.encode('utf-8'))}")

# Verify no hidden characters
for i, byte in enumerate(serialised.encode('utf-8')):
    if byte not in range(32, 127) and byte not in [9, 10, 13]:  # printable + whitespace
        print(f"⚠ Non-printable byte at position {i}: {byte}")
```

**Verify**:
- No whitespace outside quoted strings
- No trailing characters
- No BOM (Byte Order Mark)
- Encoding is UTF-8

**Fix**:
```python
# WRONG
seal_bytes = json.dumps(cycle_data, sort_keys=True)
seal_hash = hashlib.sha256(seal_bytes).hexdigest()

# CORRECT
seal_json = json.dumps(cycle_data, sort_keys=True)
seal_bytes = seal_json.encode('utf-8')  # explicit UTF-8
seal_hash = hashlib.sha256(seal_bytes).hexdigest()
```

---

#### Step 4 — Isolate the Field Set

```python
import json

# Check field-by-field against specification
spec_fields = [
    'cycle_number', 'mill_id', 'token_id', 'revenue_rate_per_kwh',
    'total_usage_kwh', 'total_actual_cash', 'expected_revenue',
    'variance', 'settled_at', 'previous_seal'
]

actual_fields = sorted(cycle_data.keys())
spec_fields = sorted(spec_fields)

print("FIELD SET ISOLATION")
print(f"Expected fields: {spec_fields}")
print(f"Actual fields:   {actual_fields}")

if actual_fields != spec_fields:
    missing = set(spec_fields) - set(actual_fields)
    extra = set(actual_fields) - set(spec_fields)
    if missing:
        print(f"❌ MISSING: {missing}")
    if extra:
        print(f"❌ EXTRA: {extra}")
```

**Why This Matters**: Any extra field or missing field produces a completely different seal.

**Fix**: Align field set exactly with specification in [TRUST_ANCHOR_DEPLOYMENT.md](TRUST_ANCHOR_DEPLOYMENT.md).

---

#### Step 5 — If All Four Steps Pass and Mismatch Persists

If timestamp, mill_id, serialisation, and field set are all correct:

```python
# Double-check the GitHub CSV has not been altered
# Pull the raw CSV from GitHub
curl https://raw.githubusercontent.com/gridledger/gridledger-cycle-seals/main/seal_log.csv > seal_log_backup.csv

# Manually verify the Cycle 1 row
# If the CSV is correct, the recomputation should match

# If recomputation STILL does not match
print("❌ MISMATCH PERSISTS AFTER ALL DIAGNOSTICS PASS")
print("Possible causes:")
print("  - GitHub CSV was corrupted or altered during commit")
print("  - Backend serialisation uses a different code path than recomputation script")
print("  - Floating-point precision issue in numeric fields")
print("\nACTION: Delete the CSV entry, recommit the correct seal, re-run verification")
```

**Action**: 
1. Delete the GitHub CSV entry
2. Recommit with correct seal
3. Re-run independent verification
4. If mismatch **still persists**: Escalate to engineering + FL00R G3N3RAL

---

### Why Stopping at Cycle 1 Mismatch Is Non-Negotiable

If a mismatch on Cycle 1 is not diagnosed and fixed **before Cycle 2**:
- Cycle 2's `previous_seal` input is **wrong**
- Every subsequent seal in the chain is **wrong**
- The chain cannot be retroactively corrected without breaking its tamper-evident property
- The entire chain becomes unpresentable to an auditor

**Cost of stopping at Cycle 1 mismatch**: One delayed cycle  
**Cost of proceeding**: A corrupt chain that destroys the system's credibility

Stop. Diagnose. Fix. Verify. Then proceed.

---

## SECONDARY MILL DEPLOYMENT GATE CRITERIA

**All five gates must show YES before secondary mill deployment is authorised.**

A single NO halts deployment and triggers the relevant response protocol.

```
Gate 1: Cycle 1 seal independently verified
        Verified: YES / NO
        If NO → Trigger: SEAL MISMATCH RESPONSE PROTOCOL
        
Gate 2: Cycle 2 chain continuity independently verified
        Verified: YES / NO
        If NO → Trigger: SEAL MISMATCH RESPONSE PROTOCOL
        
Gate 3: Both cycles show anchor_status = ANCHORED in database
        Status:  YES (both ANCHORED) / NO (any PENDING/FAILED/FAILED_PERMANENT)
        If NO → Trigger: Decision Feed Alert Response
                         (monitor anchor retries, check for GitHub API issues)
        
Gate 4: Anchor latency < 120 seconds on both cycles
        Cycle 1 latency: [X seconds]
        Cycle 2 latency: [Y seconds]
        Requirement: Both < 120 seconds
        If NO → Trigger: Network/GitHub Performance Investigation
                         (acceptable for pilot if < 180s, note for Phase 2 optimization)
        
Gate 5: Decision feed shows zero anchor alerts
        Alerts: SEAL_ANCHOR_FAILED [count]
                SEAL_ANCHOR_PENDING [count]
                SEAL_ANCHOR_PERMANENT_FAILED [count]
        Requirement: All counts = 0
        If NO → Trigger: Decision Feed Alert Response
```

**When All Five Gates Return YES**:

Report to FL00R G3N3RAL with the evidence package specified in **First Anchor Report Format** above.

Authorise secondary mill deployment.

Update RBM brief from "externally anchored" to "live-anchored with verified chain continuity from [date]".

---

## SIGN-OFF

**This checklist must be completed and verified by**:
- [ ] Engineering lead (timestamp verification + seal diagnostic steps)
- [ ] Operations lead (infrastructure deployment + monitoring)
- [ ] Finance approval (capital gate + secondary mill authorisation)

**Before**: Any secondary mill deployment  
**Before**: Any claim of "live-anchored system"

---

**There is no ambiguity remaining in this deployment.**

The chain begins at timestamp verification (pre-deployment).
The chain is confirmed at Gate 5 (post-Cycle 2).
Between those two moments, every step has a documented pass condition and a documented failure response.

The 32-month forensic record's successor begins when all five gates return YES.
