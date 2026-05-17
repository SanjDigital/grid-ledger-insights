# FRONTEND INTEGRATION CHECKLIST – May 7, 2026

## PHASE 1: Environment Setup (15 min)

- [ ] Create `frontend/.env.local`
- [ ] Set `VITE_API_URL=http://localhost:8000`
- [ ] Set `VITE_API_KEY=letmein123`
- [ ] Verify environment file in `frontend/` directory
- [ ] Run `npm install` in frontend directory

## PHASE 2: Install Dependencies (5 min)

```bash
cd frontend
npm install axios  # If not already installed
npm install
```

- [ ] Confirm no dependency errors
- [ ] Verify `node_modules/` created

## PHASE 3: Code Updates (30 min)

### Update 1: Replace `frontend/src/pages/Index.tsx`

**File:** `FRONTEND_INDEX_UPDATED.tsx` (provided)

**Changes:**
- Import `institutional` service from `@/services/institutional`
- Replace mock mills with API fetch (fallback to mock if offline)
- Load enforcement actions from `/api/institutional/enforcement-actions`
- Load audit trail from `/api/institutional/audit-trail/full`
- Submit mandate on mill selection (GL-1 governance requirement)
- Record friction analytics when mandate acknowledged

**How to apply:**
1. Open `frontend/src/pages/Index.tsx`
2. Copy content from `FRONTEND_INDEX_UPDATED.tsx`
3. Replace entire file (or merge sections manually)
4. Save

- [ ] Index.tsx updated with API calls
- [ ] No TypeScript errors (run `npm run type-check`)

### Update 2: Verify `frontend/src/services/institutional.ts` exists

**File:** `institutional.ts` (created in previous session)

**Functions required:**
- `submitMandate(payload)` → POST mandate
- `recordFrictionAnalytics(payload)` → POST friction
- `getEnforcementActions(mill_id?, ...)` → GET enforcement
- `getFullAuditTrail(limit, offset)` → GET audit trail
- `generateSessionId()` → UUID generator
- `generateMandateId()` → UUID generator

- [ ] institutional.ts file exists
- [ ] All 8 functions implemented
- [ ] No TypeScript errors

### Update 3: Verify `frontend/src/hooks/useDecisionBasis.ts` updated

**File:** `useDecisionBasis.ts`

**Changes from previous session:**
- Fetch endpoint: `/api/v1/mills/{millId}/scorecard`
- Returns: `{ trust_integrity_score, energy_accountability_ratio, fraud_risk_level }`
- Fallback: `getMockDecisionBasis()` for offline mode

- [ ] Hook queries live backend
- [ ] Fallback to mock data works
- [ ] No TypeScript errors

### Update 4: Environment Configuration in Components

**File:** `frontend/src/services/institutional.ts`

**Verify API URL:**
```typescript
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY || 'letmein123';
```

- [ ] institutional.ts uses environment variables
- [ ] Fallback keys defined

## PHASE 4: Type Safety (10 min)

```bash
cd frontend
npm run type-check
```

- [ ] No TypeScript errors
- [ ] All types compile successfully
- [ ] Commit `.ts` changes (if using git)

## PHASE 5: Backend Verification (5 min)

**Ensure backend is running:**

```bash
# Terminal 1: Backend
cd gridledger
& ".\venv\Scripts\python.exe" -m uvicorn backend.main:app --workers 1
# Expected: "Uvicorn running on http://127.0.0.1:8000"
```

- [ ] Backend running on localhost:8000
- [ ] No import errors in terminal
- [ ] Institutional models registered

**Test API endpoints:**

```bash
# Terminal 2: Test
cd gridledger
& ".\venv\Scripts\python.exe" test_api_live.py
# Expected: 4/4 tests PASS, 3+ records persisted
```

- [ ] All 4 API tests passing
- [ ] Data persisting in database

## PHASE 6: Frontend Startup (5 min)

```bash
# Terminal 3: Frontend
cd frontend
npm run dev
# Expected: "Local: http://localhost:5173"
```

- [ ] Frontend dev server started
- [ ] No build errors
- [ ] Accessible at http://localhost:5173

## PHASE 7: Dashboard Verification (10 min)

**Open browser:** http://localhost:5173

### Visual Checks:

- [ ] Dashboard loads without errors
- [ ] Mills list populated (either from API or mock)
- [ ] TrustGauge renders with EAR percentage
- [ ] INTERRUPTED (GRID) mills show amber color
- [ ] Enforcement actions table visible
- [ ] Audit trail events displayed

### API Checks:

1. Open browser DevTools (F12)
2. Go to Network tab
3. Click on a mill
4. Observe requests:
   - [ ] POST `/api/institutional/mandate-submission` → 200
   - [ ] POST `/api/institutional/friction-analytics` → 200
   - [ ] GET `/api/institutional/enforcement-actions` → 200
   - [ ] GET `/api/institutional/audit-trail/full` → 200
   - [ ] GET `/api/v1/mills/{id}/scorecard` → 200 (useDecisionBasis)

### Data Verification:

1. In backend terminal, check logs:
   - [ ] See "127.0.0.1:xxxxx - POST /api/institutional/mandate-submission"
   - [ ] See "127.0.0.1:xxxxx - POST /api/institutional/friction-analytics"

2. Verify database:
   ```bash
   # Terminal 2
   cd gridledger
   & ".\venv\Scripts\python.exe" -c "
   import sqlite3
   conn = sqlite3.connect('gridledger.db')
   c = conn.cursor()
   c.execute('SELECT COUNT(*) FROM mandate_submissions')
   print(f'Mandates: {c.fetchone()[0]}')
   c.execute('SELECT COUNT(*) FROM friction_analytics')
   print(f'Friction records: {c.fetchone()[0]}')
   "
   ```
   - [ ] mandate_submissions count increases
   - [ ] friction_analytics count increases

## PHASE 8: GL-1 Governance Verification (5 min)

- [ ] Session ID generated on page load
- [ ] Mandate submitted when mill selected
- [ ] Friction analytics recorded (100% scroll depth, 30+ seconds)
- [ ] Both records visible in audit trail
- [ ] Mandate ID matches between mandate and friction record

## PHASE 9: Frozen Trust & EAR Verification (5 min)

**Verify INTERRUPTED (GRID) handling:**

1. Select NABIWI_02 (INTERRUPTED status)
2. Check dashboard display:
   - [ ] Status badge shows "INTERRUPTED (GRID)" in amber
   - [ ] Energy generation shows 0 MWh
   - [ ] EAR percentage reflects grid outage state
   - [ ] TrustGauge color matches EAR tier

**Verify Tiered EAR:**

1. Check TrustGauge for different mills:
   - [ ] EAR ≥95% → Green (INSTITUTIONAL)
   - [ ] EAR 90-95% → Amber (COMMERCIAL)
   - [ ] EAR 80-90% → Yellow (SUBPRIME)
   - [ ] EAR <80% → Red (HIGH RISK)

## PHASE 10: Error Handling (5 min)

**Test offline mode:**

1. Stop backend: Press CTRL+C in backend terminal
2. Refresh dashboard
3. Verify:
   - [ ] Fallback mock data loads
   - [ ] No red error banner
   - [ ] "API unavailable, showing mock data" message

**Test with wrong API key:**

1. Edit `.env.local`: `VITE_API_KEY=wrong_key`
2. Refresh dashboard
3. Verify:
   - [ ] API calls fail gracefully
   - [ ] Error logged to console
   - [ ] Fallback mock data displays

## PHASE 11: Performance & Logs (5 min)

**Check browser console (F12):**

- [ ] No JavaScript errors
- [ ] No CORS errors
- [ ] Institutional service functions logged (if debug enabled)
- [ ] API calls visible in Network tab

**Check backend logs:**

- [ ] All requests logged
- [ ] No 500 errors
- [ ] Response times < 100ms

## PHASE 12: Commit & Documentation (5 min)

- [ ] Git add: `frontend/src/pages/Index.tsx`
- [ ] Git add: `frontend/.env.local` (or .gitignore if needed)
- [ ] Git commit: "Frontend: Wire dashboard to live institutional API"
- [ ] Document any custom changes in ticket
- [ ] Update DEPLOYMENT_STATUS.md

---

## TROUBLESHOOTING

### Issue: "Cannot find module 'institutional'"

**Solution:**
```bash
# Verify file exists
ls frontend/src/services/institutional.ts

# If missing, create it from FRONTEND_INTEGRATION_STEP0.md example
```

### Issue: API returns 401 Unauthorized

**Solution:**
- Check API key in `.env.local`
- Verify backend expecting `X-API-Key: letmein123`
- Inspect Network tab → Request Headers

### Issue: CORS error

**Solution:**
```python
# Add to backend/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Issue: Frontend loads but shows blank dashboard

**Solution:**
1. Open browser console (F12)
2. Check for JavaScript errors
3. Check Network tab for failed requests
4. Verify `.env.local` exists and `VITE_API_URL` set

---

## COMPLETION SIGN-OFF

When all checks complete, frontend integration is **COMPLETE**:

- ✅ Backend running + API responding
- ✅ Frontend wired to institutional service
- ✅ Dashboard displays live data + GL-1 governance records
- ✅ INTERRUPTED (GRID) + tiered EAR verified
- ✅ Error handling working
- ✅ Mandate + friction analytics recorded

**Next Steps:**
1. Timestamp canonicalisation verification (BLOCKING)
2. Cycle 1 anchor procedure
3. Cycle 2 chain continuity verification
4. Deploy to secondary mill

---

**Integration Completed:** May 7, 2026 at [timestamp]
**Verified By:** [operator name]
**Ticket Reference:** GL-1 Integration Phase 2
