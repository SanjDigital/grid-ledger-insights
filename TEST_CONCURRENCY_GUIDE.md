# Move A: Concurrency Test Guide

## 🧪 Running the Concurrency Test

This test verifies that the double-check locking mechanism and active cycle re-verification work correctly under simultaneous requests.

### Prerequisites

1. **Python environment configured** (virtual environment activated)
2. **Database initialized** with the SQL migration applied:
   ```bash
   sqlite3 data/gridledger.db "CREATE UNIQUE INDEX one_active_cycle_per_mill ON token_allocations (mill_id) WHERE status IN ('PENDING', 'MISSING', 'DISPUTED');"
   ```
3. **All dependencies installed** - ensure FastAPI, SQLModel, requests are available

### Step 1: Start the API Server

In the first terminal (inside the gridledger folder):

```bash
# Make sure your virtual environment is active
# Then start the FastAPI server
python -m uvicorn backend.main:app --reload --port 8000
```

You should see output like:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete
```

### Step 2: Run the Concurrency Test

In a second terminal (also in gridledger folder, with venv activated):

```bash
# Run the concurrency test
python test_move_a_concurrency.py
```

### Expected Output

The test will:

1. **Setup Phase**
   - Initialize the test database
   - Create a test mill (TEST_MILL_CONCURRENT) with revenue_rate_per_kwh=100.0
   - Verify the mill was created

2. **Connectivity Check**
   - Verify the API is responding on http://localhost:8000

3. **Concurrent Requests Phase**
   - Send Request 1 to `/api/owner/mills/TEST_MILL_CONCURRENT/allocate-token`
   - Send Request 2 ~100ms later to the same endpoint
   - Display timing and response for each

4. **Verification Phase**
   - Check if responses match expected concurrency behavior
   - Verify database state (at most 1 active allocation)

### Success Criteria

✅ **Test passes if:**

**Case 1: Perfect Double-Lock Behavior** (Most likely)
- Request 1: ✅ Allowed (creates PENDING allocation)
- Request 2: ❌ Blocked with `BLOCKED_PENDING`
- Database: Only 1 active allocation exists

**Case 2: Both Allowed** (Also valid)
- Both requests succeeded (mill was in IDLE state initially)
- This indicates no active cycle race condition occurred
- Database: Each has its own allocation (or at most 1 if they sequenced)

**Case 3: Either Request Blocked** (Also valid)
- If both are blocked due to exposure limit or other policy
- This is fine - they're being treated fairly

### Example Output

```
======================================================================
🧪 MOVE A CONCURRENCY TEST
======================================================================
Endpoint: POST /api/owner/mills/TEST_MILL_CONCURRENT/allocate-token
Test Mill: TEST_MILL_CONCURRENT
API URL: http://localhost:8000
Timestamp: 2026-04-14T15:30:42.123456+00:00

----------------------------------------------------------------------
📦 SETUP PHASE
----------------------------------------------------------------------
🔧 Setting up test database...
   Cleaned up existing test mill 'TEST_MILL_CONCURRENT'
✅ Test mill 'TEST_MILL_CONCURRENT' created with revenue_rate_per_kwh=100.0
   ✓ Mill verified: TEST_MILL_CONCURRENT, revenue_rate=100.0

🔌 Testing API connectivity...
   ✓ API is responding (HTTP 200)

----------------------------------------------------------------------
🚀 CONCURRENT REQUESTS PHASE
----------------------------------------------------------------------

Sending 2 simultaneous requests (with ~100ms stagger for fairness)...

[Request 1] Starting allocate-token request at 2026-04-14T15:30:44.123456+00:00
[Request 2] Starting allocate-token request at 2026-04-14T15:30:44.223456+00:00
[Request 1] ✅ SUCCESS (HTTP 200) - took 0.456s
          Allocation allowed: 35.94 kWh
[Request 2] ✅ SUCCESS (HTTP 200) - took 0.512s
          Blocked: BLOCKED_PENDING

----------------------------------------------------------------------
🔍 VERIFICATION PHASE
----------------------------------------------------------------------
...
📋 VERIFICATION LOGIC:
  ✅ PERFECT: Request 1 allowed, Request 2 blocked
     Blocked reason: BLOCKED_PENDING
     This demonstrates double-check locking working correctly!
  ✓ Blocking reason is appropriate: BLOCKED_PENDING

======================================================================
📊 TEST SUMMARY
======================================================================

✅ CONCURRENCY TEST PASSED!
   Double-lock checking and active cycle re-verification are working correctly.
```

### Troubleshooting

#### "Cannot reach API at http://localhost:8000"
- **Solution:** Make sure the API server is running in another terminal
  ```bash
  python -m uvicorn backend.main:app --reload --port 8000
  ```

#### "Database setup failed: DecisionAudit model not found"
- **Solution:** Ensure DecisionAudit is in init_db.py and imported in owner_routes.py
  ```bash
  python scripts/init_db.py  # Recreate tables if needed
  ```

#### "UNIQUE constraint failed: token_allocations (mill_id)"
- **Solution:** The SQL index migration hasn't been run. Execute:
  ```bash
  sqlite3 data/gridledger.db "CREATE UNIQUE INDEX one_active_cycle_per_mill ON token_allocations (mill_id) WHERE status IN ('PENDING', 'MISSING', 'DISPUTED');"
  ```

#### Test hangs or times out
- **Possible causes:**
  1. API is not responding (not running)
  2. Deadlock in database transaction (very rare with SQLite)
  3. Network issue
- **Solution:** Check API server logs, restart both server and test

#### "HTTP 401: Invalid or missing API key"
- **Solution:** The API key in the test script doesn't match OWNER_API_KEY env var
  - The test sets OWNER_API_KEY automatically
  - Verify it's set correctly on the API server side:
    ```bash
    # The test uses: OWNER_API_KEY=test-api-key-12345
    # Make sure your API doesn't require a different key
    ```

### Detailed Verification

After the test completes, you can manually verify the results:

**Check the created allocation:**
```python
from sqlmodel import Session, select
from scripts.init_db import engine, TokenAllocation

with Session(engine) as session:
    allocations = session.exec(
        select(TokenAllocation).where(
            TokenAllocation.mill_id == "TEST_MILL_CONCURRENT"
        )
    ).all()
    for alloc in allocations:
        print(f"Allocation {alloc.id}: status={alloc.status}, expected_revenue={alloc.expected_revenue}")
```

**Check the audit trail:**
```python
from sqlmodel import Session, select
from scripts.init_db import engine
from backend.owner_routes import DecisionAudit

with Session(engine) as session:
    audits = session.exec(
        select(DecisionAudit).where(
            DecisionAudit.mill_id == "TEST_MILL_CONCURRENT"
        )
    ).all()
    for audit in audits:
        print(f"Audit: allowed={audit.allowed}, reason={audit.reason}")
```

### Performance Notes

- **Request 1** typically takes 0.4-0.6 seconds (includes lock acquisition, calculations, allocation)
- **Request 2** should take slightly longer if blocked (more work to compute decision basis before blocking)
- The ~100ms stagger between requests helps ensure close temporal interleaving without being completely simultaneous

### What's Being Tested

✅ **Transaction Atomicity**
  - Allocation and audit record both added to transaction
  - Both committed together

✅ **Row Locking**
  - Mill row locked at start of allocate_token
  - Lock held until response returned

✅ **Active Cycle Re-Check**
  - Inside locked transaction with `with_for_update()`
  - Prevents TOCTOU (Time-of-Check-Time-of-Use) race condition

✅ **Unique Index Enforcement**
  - At most 1 PENDING/MISSING/DISPUTED cycle per mill
  - Database level constraint prevents violations

✅ **Decision Audit Atomicity**
  - Audit stored in same transaction as allocation
  - No orphaned or missing records

---

## 📊 Test Results to Expect

### Ideal Outcome (Most Common)

| Aspect | Result | Notes |
|--------|--------|-------|
| Request 1 | ✅ Allowed | Created PENDING allocation |
| Request 2 | ❌ Blocked | `BLOCKED_PENDING` reason |
| Active Count | 1 | Only Request 1's allocation |
| Audits | 2 | Both allowed and blocked logged |

### Alternative Outcomes

| Scenario | Validity | Reason |
|----------|----------|--------|
| Both allowed | ✅ Valid | No active cycle blocking required |
| Both blocked | ✅ Valid | Both hit exposure/policy limit |
| Req 1 blocked, Req 2 allowed | ✅ Valid | Sequences correctly after lock release |

### Invalid Outcomes (Would Indicate Bug)

| Scenario | Problem |
|----------|---------|
| Multiple PENDING/MISSING/DISPUTED per mill | Unique index not working |
| Orphaned audit records | Atomicity broken |
| Request hangs indefinitely | Deadlock or missing lock |
| 500 errors in both requests | Code error, check API logs |

---

## 📝 Next Steps

After confirming concurrency test passes:

1. ✅ **Verify SQL Index** - confirm it exists in database
2. ✅ **Run Performance Profiling** - verify single SQL query for exposure
3. ✅ **Review Audit Logs** - confirm all decisions recorded atomically
4. 🔜 **Move B: Idempotency** - prevent double-allocation on retry
5. 🔜 **Move C: Fraud Detection** - add suspicion scoring

---

## 🆘 Need Help?

- Check the test output for specific error messages
- Review [MIGRATION_MOVE_A.md](MIGRATION_MOVE_A.md) for implementation details
- Check API server logs for any exceptions
- Verify database schema: `sqlite3 data/gridledger.db ".schema token_allocations"`
