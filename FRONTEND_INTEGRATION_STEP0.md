**FRONTEND INTEGRATION GUIDE – Step 0 Backend Persistence (Live Data)**

**Date:** May 6, 2026  
**Status:** Ready for integration

---

## 📋 Changes Made

### 1. **useDecisionBasis Hook** (`frontend/src/hooks/useDecisionBasis.ts`)
- ✅ Updated to query `/api/owner/mills/{millId}/decision` endpoint
- ✅ Added API URL + API Key from environment variables
- ✅ Fallback to mock data on network errors
- ✅ Properly handles DecisionBasisData shape

### 2. **Institutional Services** (`frontend/src/services/institutional.ts`)
- ✅ Complete API client for GL-1 governance endpoints
- ✅ Functions: submitMandate, recordFrictionAnalytics, submitDiscrepancyReport, etc.
- ✅ Session ID + Mandate ID generation helpers

### 3. **API Verification Script** (`frontend/verify_backend_api.js`)
- ✅ Node.js script to test backend endpoints before frontend integration
- ✅ Tests 3 key endpoints (POST mandate, GET audit trail, GET decision basis)
- ✅ Run with: `node verify_backend_api.js`

---

## 🚀 Integration Steps

### Step 1: Start Backend

```bash
cd c:\Users\USER\Documents\Python Projets\gridledger
python -m uvicorn backend.main:app --reload --workers 1
```

Expected output: `Uvicorn running on http://127.0.0.1:8000`

### Step 2: Verify Backend Endpoints (Optional)

```bash
cd frontend
node verify_backend_api.js
```

Expected output:
```
[TEST] Mandate Submission (POST)
  POST /api/institutional/mandate-submission
  [OK] Status: 200
  Data: {"mandate_id": "test_mandate_...", "status": "ACKNOWLEDGED",...}
```

### Step 3: Configure Frontend Environment

Create or update `.env` in frontend root:

```env
VITE_API_URL=http://localhost:8000
VITE_API_KEY=letmein123
```

For production, use secure token management (e.g., AWS Secrets Manager, HashiCorp Vault).

### Step 4: Test Frontend with Live Data

```bash
cd frontend
npm run dev
```

Navigate to `http://localhost:5173` and observe:

1. **Loading State**: Shows "[OK] Fetching decision basis from API..."
2. **Live Data**: Dashboard displays real EAR, Trust Score from backend
3. **INTERRUPTED (GRID)**: Grid-induced failures appear in amber (not red)
4. **Tiered Trust Gauge**: EAR-based tiers (≥95%, 90–95%, <90%)
5. **Audit Trail**: Mandate submissions, discrepancies, enforcement actions persisted

---

## 🔌 API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/owner/mills/{id}/decision` | GET | Fetch pre-computed decision basis (EAR, Trust Score) |
| `/api/institutional/mandate-submission` | POST | Submit operator mandate acknowledgment |
| `/api/institutional/friction-analytics` | POST | Record friction moment engagement |
| `/api/institutional/discrepancy-reports` | POST | Submit discrepancy report |
| `/api/institutional/audit-trail/mill/{id}` | GET | Retrieve mill's audit trail |

---

## 📊 Data Flow

```
┌─────────────────────────────────────────────────────┐
│  Frontend (React + Vite)                            │
│  ┌────────────────────────────────────────────────┐ │
│  │ Index.tsx (Dashboard)                          │ │
│  │ - Fetches via useDecisionBasis hook            │ │
│  │ - Displays INTERRUPTED (GRID) in amber         │ │
│  │ - Shows tiered EAR-based Trust Gauge           │ │
│  └────────────────────────────────────────────────┘ │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ HTTPS / REST API
                   │
┌──────────────────┴──────────────────────────────────┐
│  Backend (FastAPI + Python)                         │
│  ┌────────────────────────────────────────────────┐ │
│  │ institutional_routes.py                        │ │
│  │ - /api/institutional/* endpoints               │ │
│  │ - Session: get_session() from SQLModel engine  │ │
│  └────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────┐ │
│  │ owner_routes.py                                │ │
│  │ - /api/owner/mills/{id}/decision endpoint      │ │
│  └────────────────────────────────────────────────┘ │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ SQLAlchemy ORM
                   │
┌──────────────────┴──────────────────────────────────┐
│  SQLite Database (gridledger.db)                    │
│  - mandate_submissions (GL-1)                       │
│  - friction_analytics (GL-1)                        │
│  - discrepancy_reports (GL-1)                       │
│  - enforcement_actions (GL-1)                       │
│  - (25 existing tables for cycles, events, etc.)    │
└─────────────────────────────────────────────────────┘
```

---

## ✅ Verification Checklist

- [ ] Backend starts without errors: `python -m uvicorn backend.main:app --reload --workers 1`
- [ ] API verification passes: `node verify_backend_api.js`
- [ ] Frontend `.env` configured with API_URL and API_KEY
- [ ] Frontend loads: `npm run dev` → `http://localhost:5173`
- [ ] Dashboard shows "Fetching decision basis..." while loading
- [ ] EAR and Trust Score display from backend (not mock)
- [ ] INTERRUPTED (GRID) state appears in amber for grid-induced cycles
- [ ] Tiered Trust Gauge updates based on live EAR data
- [ ] Audit trail queryable: `/api/institutional/audit-trail/mill/NABIWI_01`

---

## 🔐 Security Notes

1. **API Key**: Currently `letmein123` (hardcoded in environment)
   - **Production**: Use HashiCorp Vault, AWS Secrets Manager, or similar
   - Never commit `.env` files with real keys

2. **CORS**: If frontend and backend on different origins, configure CORS in `backend/main.py`
   - Add: `app.add_middleware(CORSMiddleware, ...)`

3. **SSL/TLS**: Use HTTPS in production
   - Set `VITE_API_URL=https://api.gridledger.app`

---

## 🧪 Test Scenario: Submit Mandate + Record Friction

```typescript
// In a React component or test:
import { 
  submitMandate, 
  recordFrictionAnalytics, 
  generateSessionId,
  generateMandateId 
} from '@/services/institutional';

async function testMandateFlow() {
  const sessionId = generateSessionId();
  const mandateId = generateMandateId();

  // 1. Record friction analytics
  await recordFrictionAnalytics({
    session_id: sessionId,
    mandate_id: mandateId,
    scroll_depth_pct: 95.0,
    time_on_statement_ms: 45000,
    interaction_count: 3,
    bypass_attempted: false,
  });

  // 2. Submit mandate
  const result = await submitMandate({
    mandate_id: mandateId,
    submitted_by: 'NABIWI_01',
    role: 'operator',
    mandate_version_hash: 'sha256_...',
    acknowledgment_type: 'full_acceptance',
    session_id: sessionId,
  });

  console.log('Mandate submitted:', result);
  // → { mandate_id: "...", status: "ACKNOWLEDGED", timestamp: "2026-05-06T..." }
}
```

---

## 📝 Next Steps (Post-Integration)

1. **Mode-Specific Rendering** – Build Executive/Technical/Audit views
2. **Discrepancy Dashboard** – Display pending reports for review team
3. **GL-1 Institutional Transmission** – Prepare audit trail export for RBM/NBM
4. **Stress Flag Detection** – Implement 3+ interruptions → bridging cycle logic
5. **Live Cycle Deployment** – Execute Cycle 1 & 2 anchor procedures

---

**Status: Ready for Integration. Dashboard will become institution-ready after frontend wiring completes.**
