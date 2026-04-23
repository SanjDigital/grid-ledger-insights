# GridLedger Frontend Build Plan – Phase 1
**Status**: Architecture Review Complete  
**Date**: April 22, 2026  
**Target**: Six-gap closure + Supabase integration + decision-feed operationalization

---

## Executive Summary

The backend is **production-ready** (v3.0, all three features implemented and tested). The frontend is **greenfield** (no existing React components).

This plan prioritizes the six gaps from the Claude memo in order of **business impact** and **blocking dependencies**:

1. **Supabase schema & data setup** — blocking everything else
2. **Data hooks** (`useEvents`, `useMills`, `useAuditLog`, `useDecisionFeed`) — replaces mocks
3. **Decision feed UI** — the owner's operational heartbeat
4. **Effective rate display** — closes the primary new forensic signal visibility gap
5. **Idempotency headers** — prevents duplicate allocations
6. **Baseline & tariff fetching** — removes hardcoded constants
7. **EAR refactor** — eliminates dual computation

**Total Effort**: ~25–28 hours (excluding auth, testing, deployment).

---

## Part A: Understanding the Data Model

### Backend Reality Check

The backend has these structures:

**Mill** (per-operator location)
- `id`: "NABIWI_NRID"
- `revenue_rate_per_kwh`: 1350.0 (operator agreement)
- `baseline_efficiency_kg_per_kwh`: 22.66 (Nabiwi verified)
- `observation_band_low`: 1340 (per-mill, Phase 1)
- `observation_band_high`: 1360 (per-mill, Phase 1)

**TokenAllocation** (per-cycle gate)
- `id`: allocation_id
- `mill_id`: "NABIWI_01"
- `allocated_kwh`: 59.9
- `expected_revenue`: 80865.00
- `status`: "PENDING" | "CLOSED" | "MISSING" | "DISPUTED"
- `created_at`: ISO timestamp

**CashReceipt** (operator remittance)
- `id`: receipt_id
- `allocation_id`: links to TokenAllocation
- `amount_mwk`: 80955.00
- `effective_rate_per_kwh`: 80955 / 59.9 = 1350.3
- `created_at`: ISO timestamp

**DecisionBasis** (audit trail, immutable)
- `mill_id`: "NABIWI_01"
- `cycle_state`: "IDLE" | "PENDING" | "MISSING"
- `trust_score`: 0–100
- `adherence`: 0–100 (percent)
- `capital_at_risk`: decimal
- `time_weighted_risk`: decimal (capital_at_risk × (1 + 0.1 × overdue_days), capped 2.0×)
- `effective_rate_per_kwh`: 1350.3 (from last cycle's receipt)
- `decision_timestamp`: ISO

**TariffRate** (MERA cost tracking)
- `mill_id`: "NABIWI_NRID"
- `rate_mk_per_kwh`: 284.15 (MERA ET7, Jan 19 2026)
- `effective_date`: ISO
- `set_by`: "MERA_ADMIN"

**ReconciliationRecord** (forensic anchor)
- `mill_id`: "NABIWI_01"
- `window_start`: ISO
- `window_end`: ISO
- `reported_kwh`: from production events
- `metered_kwh`: from ESCOM meter
- `energy_accountability_ratio`: reported / metered (clipped [0,1])
- `verified_throughput`: metered × EAR

**AuditLog** (immutable event trail)
- `id`: serial
- `mill_id`: "NABIWI_01"
- `event_type`: "ALLOCATION" | "RECEIPT" | "RECONCILIATION" | "BREACH" | etc.
- `event_data`: JSON
- `timestamp`: ISO

### Decision Feed Semantics

The `GET /api/owner/decision-feed` endpoint returns:

```json
[
  {
    "mill_id": "NABIWI_01",
    "issue": "PENDING_NEAR_TIMEOUT",
    "urgency": "HIGH",
    "capital_at_risk_mwk": 80865.00,
    "time_weighted_risk_mwk": 121297.50,
    "remaining_hours": 4.5,
    "priority": 42.7,
    "action": "Review pending allocation; operator should submit receipt"
  },
  {
    "mill_id": "MKWINDA_02",
    "issue": "CONDITIONAL_REVIEW",
    "urgency": "MEDIUM",
    "capital_at_risk_mwk": 45000.00,
    "time_weighted_risk_mwk": 45000.00,
    "remaining_hours": 168.0,
    "priority": 8.3,
    "action": "Trust score in CONDITIONAL range; manual review scheduled"
  }
]
```

Sorting is by `priority` (hybrid log-linear). Urgency determines badge color + icon.

---

## Part B: Supabase Schema (Step 0)

### Database Tables

**1. mills**
```sql
CREATE TABLE mills (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  location TEXT,
  operator_contact TEXT,
  revenue_rate_per_kwh DECIMAL(10, 2) NOT NULL,
  baseline_efficiency_kg_per_kwh DECIMAL(10, 4),
  observation_band_low DECIMAL(10, 2),
  observation_band_high DECIMAL(10, 2),
  observation_status TEXT DEFAULT 'OBSERVING', -- OBSERVING | ENFORCING
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**2. token_allocations**
```sql
CREATE TABLE token_allocations (
  id BIGSERIAL PRIMARY KEY,
  mill_id TEXT NOT NULL REFERENCES mills(id),
  allocated_kwh DECIMAL(10, 2) NOT NULL,
  expected_revenue DECIMAL(12, 2) NOT NULL,
  status TEXT DEFAULT 'PENDING', -- PENDING | CLOSED | MISSING | DISPUTED
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(mill_id) WHERE status='PENDING'
);
```

**3. cash_receipts**
```sql
CREATE TABLE cash_receipts (
  id BIGSERIAL PRIMARY KEY,
  allocation_id BIGINT NOT NULL REFERENCES token_allocations(id),
  amount_mwk DECIMAL(12, 2) NOT NULL,
  effective_rate_per_kwh DECIMAL(10, 4),
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**4. decision_basis** (immutable audit trail)
```sql
CREATE TABLE decision_basis (
  id BIGSERIAL PRIMARY KEY,
  mill_id TEXT NOT NULL REFERENCES mills(id),
  cycle_state TEXT NOT NULL, -- IDLE | PENDING | MISSING
  trust_score INTEGER,
  adherence DECIMAL(5, 2),
  capital_at_risk DECIMAL(12, 2),
  time_weighted_risk DECIMAL(12, 2),
  effective_rate_per_kwh DECIMAL(10, 4),
  decision_timestamp TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_decision_basis_mill_timestamp ON decision_basis(mill_id, decision_timestamp DESC);
```

**5. tariff_rates**
```sql
CREATE TABLE tariff_rates (
  id BIGSERIAL PRIMARY KEY,
  mill_id TEXT NOT NULL REFERENCES mills(id),
  rate_mk_per_kwh DECIMAL(10, 2) NOT NULL,
  effective_date TIMESTAMP NOT NULL,
  set_by TEXT,
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tariff_rates_mill_effective ON tariff_rates(mill_id, effective_date DESC);
```

**6. reconciliation_records**
```sql
CREATE TABLE reconciliation_records (
  id BIGSERIAL PRIMARY KEY,
  mill_id TEXT NOT NULL REFERENCES mills(id),
  window_start TIMESTAMP NOT NULL,
  window_end TIMESTAMP NOT NULL,
  reported_kwh DECIMAL(10, 2),
  metered_kwh DECIMAL(10, 2),
  energy_accountability_ratio DECIMAL(4, 3),
  verified_throughput DECIMAL(10, 2),
  variance_percent DECIMAL(6, 2),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_reconciliation_records_mill_window ON reconciliation_records(mill_id, window_end DESC);
```

**7. audit_log** (immutable)
```sql
CREATE TABLE audit_log (
  id BIGSERIAL PRIMARY KEY,
  mill_id TEXT NOT NULL REFERENCES mills(id),
  event_type TEXT NOT NULL,
  event_data JSONB,
  timestamp TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_log_mill_timestamp ON audit_log(mill_id, timestamp DESC);
```

### Seed Data (Nabiwi Q1 2026)

```sql
-- Insert mill record
INSERT INTO mills (id, name, location, revenue_rate_per_kwh, baseline_efficiency_kg_per_kwh, observation_band_low, observation_band_high, observation_status)
VALUES ('NABIWI_NRID', 'Nabiwi Solar', 'Lilongwe District', 1350.00, 22.66, 1340.00, 1360.00, 'OBSERVING');

-- Insert recent allocations (sample)
INSERT INTO token_allocations (mill_id, allocated_kwh, expected_revenue, status, created_at)
VALUES 
  ('NABIWI_NRID', 59.9, 80865.00, 'CLOSED', NOW() - INTERVAL '2 days'),
  ('NABIWI_NRID', 59.9, 80865.00, 'PENDING', NOW() - INTERVAL '4 hours');

-- Insert cash receipts (sample)
INSERT INTO cash_receipts (allocation_id, amount_mwk, effective_rate_per_kwh, created_at)
VALUES (1, 80955.00, 1350.3, NOW() - INTERVAL '2 days');

-- Insert tariff rate (MERA ET7, Jan 19 2026)
INSERT INTO tariff_rates (mill_id, rate_mk_per_kwh, effective_date, set_by, notes)
VALUES ('NABIWI_NRID', 284.15, '2026-01-19T00:00:00Z', 'MERA_ADMIN', 'ET7 schedule effective 2026-01-19 (+12% adjustment)');

-- Insert decision basis (sample)
INSERT INTO decision_basis (mill_id, cycle_state, trust_score, adherence, capital_at_risk, time_weighted_risk, effective_rate_per_kwh, decision_timestamp)
VALUES ('NABIWI_NRID', 'IDLE', 95, 100.1, 80865.00, 80865.00, 1350.3, NOW());
```

### API Response Validation

After schema creation, verify these endpoints return expected format:

```bash
# Test 1: Get mill metadata
curl http://localhost:8000/api/owner/mills/NABIWI_NRID
# Should return: mill record with baseline_efficiency_kg_per_kwh: 22.66

# Test 2: Get decision feed
curl http://localhost:8000/api/owner/decision-feed
# Should return: array of mills sorted by time_weighted_risk

# Test 3: Get mill decision
curl http://localhost:8000/api/owner/mills/NABIWI_NRID/decision
# Should return: decision_basis with effective_rate_per_kwh

# Test 4: Get tariff rates
curl http://localhost:8000/api/owner/mills/NABIWI_NRID/tariff-rate
# Should return: current MERA rate (284.15)
```

**Effort**: 2–3 hours (schema creation, seed data, API validation)

---

## Part C: Frontend Data Hooks (Step 1)

### File Structure

```
src/
  lib/
    supabaseClient.ts          ← Supabase client setup
  hooks/
    useEvents.ts               ← Fetch decision_basis history
    useMills.ts                ← Fetch mill list + metadata
    useAuditLog.ts             ← Fetch audit trail
    useDecisionFeed.ts         ← Fetch urgency-sorted mills
    useCurrentTariff.ts        ← Fetch MERA tariff (lazy load)
  pages/
    Index.tsx                  ← Main layout (unchanged)
```

### Hook Implementations

**src/lib/supabaseClient.ts**
```typescript
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.REACT_APP_SUPABASE_URL;
const supabaseKey = process.env.REACT_APP_SUPABASE_ANON_KEY;

export const supabase = createClient(supabaseUrl, supabaseKey);
```

**src/hooks/useMills.ts**
```typescript
import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabaseClient';

interface Mill {
  id: string;
  name: string;
  revenue_rate_per_kwh: number;
  baseline_efficiency_kg_per_kwh: number;
  observation_band_low: number;
  observation_band_high: number;
}

export function useMills() {
  const [mills, setMills] = useState<Mill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchMills = async () => {
      const { data, error } = await supabase
        .from('mills')
        .select('*')
        .order('created_at', { ascending: true });

      if (error) {
        setError(error as Error);
      } else {
        setMills(data || []);
      }
      setLoading(false);
    };

    fetchMills();
  }, []);

  return { mills, loading, error };
}
```

**src/hooks/useDecisionFeed.ts**
```typescript
import { useEffect, useState } from 'react';

interface DecisionFeedItem {
  mill_id: string;
  issue: string;
  urgency: 'HIGH' | 'MEDIUM' | 'LOW';
  capital_at_risk_mwk: number;
  time_weighted_risk_mwk: number;
  remaining_hours: number;
  priority: number;
  action: string;
}

export function useDecisionFeed() {
  const [items, setItems] = useState<DecisionFeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchFeed = async () => {
      try {
        const response = await fetch('/api/owner/decision-feed', {
          headers: { 'X-API-Key': process.env.REACT_APP_OWNER_API_KEY },
        });
        const data = await response.json();
        setItems(data);
      } catch (err) {
        setError(err as Error);
      }
      setLoading(false);
    };

    fetchFeed();
  }, []);

  return { items, loading, error };
}
```

**Effort**: 4–5 hours (including error handling, React patterns)

---

## Part D: Gap-Specific UI Components (Steps 2–6)

### Gap 2: Decision Feed Component (Step 2)

**File**: `src/components/DecisionFeedPanel.tsx`

```typescript
import { useDecisionFeed } from '../hooks/useDecisionFeed';

export function DecisionFeedPanel() {
  const { items, loading, error } = useDecisionFeed();

  if (loading) return <div>Loading decision feed...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div className="decision-feed">
      <h2>Decision Feed – Urgent Actions</h2>
      <ul>
        {items.map((item) => (
          <li key={item.mill_id} className={`urgency-${item.urgency.toLowerCase()}`}>
            <div className="urgency-badge">{item.urgency}</div>
            <div className="mill-info">
              <span className="mill-id">{item.mill_id}</span>
              <span className="issue">{item.issue}</span>
            </div>
            <div className="metrics">
              <span>Capital at Risk: {item.capital_at_risk_mwk} MWK</span>
              <span>Remaining Hours: {item.remaining_hours}</span>
            </div>
            <div className="action">{item.action}</div>
            <button className="action-button">Review</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

**Effort**: 6 hours (including styling, responsive layout, button handlers)

### Gap 1: Effective Rate Display (Step 3)

**File**: `src/components/EnforcementPanel.tsx` (update existing)

```typescript
interface EnforcementPanelProps {
  millId: string;
  currentRate?: number;
  observationBandLow?: number;
  observationBandHigh?: number;
}

export function EnforcementPanel({ millId, currentRate, observationBandLow, observationBandHigh }: EnforcementPanelProps) {
  const inBand = currentRate && observationBandLow && observationBandHigh
    ? currentRate >= observationBandLow && currentRate <= observationBandHigh
    : null;

  return (
    <div className="enforcement-panel">
      <h3>Operational Status</h3>
      {currentRate && (
        <div className="rate-metric">
          <span className="label">Effective Rate (kWh)</span>
          <span className={`value ${inBand ? 'in-band' : 'anomaly'}`}>
            {currentRate} MWK/kWh
          </span>
          {observationBandLow && (
            <span className="band">
              Band: {observationBandLow}–{observationBandHigh} MWK/kWh
            </span>
          )}
          <span className={`badge ${inBand ? 'observing' : 'flagged'}`}>
            {inBand ? 'OBSERVING' : 'ANOMALY'}
          </span>
        </div>
      )}
    </div>
  );
}
```

**Effort**: 4 hours (integration with existing mill data)

### Gap 3: Idempotency Headers (Step 4a)

**File**: `src/components/AllocateTokenButton.tsx` (update existing)

```typescript
import { v4 as uuidv4 } from 'uuid';

export function AllocateTokenButton({ millId }) {
  const [idempotencyKey, setIdempotencyKey] = useState<string | null>(null);

  const handleAllocate = async () => {
    const key = idempotencyKey || uuidv4();
    setIdempotencyKey(key); // Store for retries

    try {
      const response = await fetch(`/api/owner/mills/${millId}/allocate-token`, {
        method: 'POST',
        headers: {
          'X-API-Key': process.env.REACT_APP_OWNER_API_KEY,
          'Idempotency-Key': key, // ← INJECT HERE
        },
      });
      const result = await response.json();
      console.log('Allocation successful:', result);
    } catch (error) {
      console.error('Allocation failed:', error);
      // Retry with same key (stored in state)
    }
  };

  return <button onClick={handleAllocate}>Allocate Token</button>;
}
```

**Effort**: 1 hour

### Gap 4: Baseline Efficiency (Step 4b)

**File**: Update `YieldEfficiencyChart.tsx`

```typescript
interface YieldEfficiencyChartProps {
  millId: string;
  mills: Array<{ id: string; baseline_efficiency_kg_per_kwh: number }>;
}

export function YieldEfficiencyChart({ millId, mills }: YieldEfficiencyChartProps) {
  const mill = mills.find((m) => m.id === millId);
  const baseline = mill?.baseline_efficiency_kg_per_kwh || 25; // Fallback to 25 if missing

  // Use baseline in chart rendering
  return <div>Baseline: {baseline} kg/kWh</div>;
}
```

**Effort**: 2 hours

### Gap 5: MERA Tariff (Step 4c)

**File**: Add `src/hooks/useCurrentTariff.ts`

```typescript
export function useCurrentTariff(millId: string) {
  const [tariff, setTariff] = useState<number | null>(null);

  useEffect(() => {
    const fetchTariff = async () => {
      try {
        const response = await fetch(`/api/owner/mills/${millId}/tariff-rate`, {
          headers: { 'X-API-Key': process.env.REACT_APP_OWNER_API_KEY },
        });
        const data = await response.json();
        setTariff(data.rate_mk_per_kwh); // 284.15
      } catch (error) {
        console.error('Failed to fetch tariff:', error);
      }
    };

    fetchTariff();
  }, [millId]);

  return tariff;
}
```

**File**: Update `CostSummary.tsx`

```typescript
export function CostSummary({ millId }) {
  const tariff = useCurrentTariff(millId);

  return (
    <div>
      <span>ESCOM Energy Cost: {tariff} MK/kWh</span>
    </div>
  );
}
```

**Effort**: 2 hours

### Gap 6: EAR Refactor (Step 5)

**File**: Refactor `src/lib/forensic-engine.ts`

```typescript
// BEFORE: Compute EAR client-side
export function computeEAR(reportedKwh: number, meteredKwh: number): number {
  return Math.min(1, reportedKwh / meteredKwh);
}

// AFTER: Consume from API, format for display
export function formatEARDisplay(ear: number): string {
  return `${(ear * 100).toFixed(1)}%`;
}

export function getEARTier(ear: number): 'TIER_1' | 'TIER_2' | 'TIER_3' {
  if (ear >= 0.95) return 'TIER_1';
  if (ear >= 0.90) return 'TIER_2';
  return 'TIER_3';
}
```

**File**: `src/components/TrustScorecard.tsx`

```typescript
import { useDecisionBasis } from '../hooks/useDecisionBasis';

export function TrustScorecard({ millId }) {
  const { decisionBasis, loading } = useDecisionBasis(millId);

  if (loading) return <div>Loading scorecard...</div>;

  return (
    <div>
      <span>Trust Score: {decisionBasis.trust_score}</span>
      <span>EAR: {formatEARDisplay(decisionBasis.ear)}</span>
      <span>EAR Tier: {getEARTier(decisionBasis.ear)}</span>
    </div>
  );
}
```

**Effort**: 3 hours

---

## Part E: Test & Validation

### Unit Tests

- `useMills.test.ts`: Mock Supabase, verify hook fetches correctly
- `useDecisionFeed.test.ts`: Mock API response, verify sorting by priority
- `AllocateTokenButton.test.ts`: Verify Idempotency-Key injection
- `EnforcementPanel.test.ts`: Verify rate display logic (in-band vs anomaly)

**Effort**: 4–5 hours

### E2E Tests

- Flow 1: Load decision feed, click on mill, view effective rate
- Flow 2: Allocate token (with idempotency), retry allocation, verify same ID
- Flow 3: Record receipt, verify effective rate updates

**Effort**: 3–4 hours

---

## Part F: Deployment & Documentation

### Environment Variables

```env
# .env
REACT_APP_SUPABASE_URL=https://[PROJECT].supabase.co
REACT_APP_SUPABASE_ANON_KEY=eyJhbGc...
REACT_APP_OWNER_API_KEY=owner-secret
REACT_APP_API_BASE=http://localhost:8000
```

### Deployment Checklist

- [ ] Supabase project created + schema deployed
- [ ] Seed data loaded (Nabiwi Q1 2026)
- [ ] Backend API verified responding with correct format
- [ ] Frontend hooks tested in isolation
- [ ] Components integrated and styled
- [ ] E2E tests passing
- [ ] Environmental variables configured
- [ ] Deployed to staging
- [ ] Owner acceptance testing

---

## Part G: Timeline & Resource Allocation

| Step | Component | Hours | Owner | Start | End |
|------|-----------|-------|-------|-------|-----|
| 0 | Supabase schema & seed | 3 | You | Day 1 | Day 1 PM |
| 1 | Data hooks | 5 | Dev | Day 2 | Day 2 PM |
| 2 | Decision feed UI | 6 | Dev | Day 2 | Day 3 |
| 3 | Effective rate display | 4 | Dev | Day 3 | Day 3 PM |
| 4a | Idempotency injection | 1 | Dev | Day 3 PM | Day 3 PM |
| 4b | Baseline efficiency | 2 | Dev | Day 4 | Day 4 AM |
| 4c | MERA tariff fetching | 2 | Dev | Day 4 AM | Day 4 PM |
| 5 | EAR refactor | 3 | Dev | Day 4 | Day 5 AM |
| Tests | Unit + E2E | 8 | QA | Day 5 | Day 6 |
| Docs | README + guide | 2 | You | Day 6 | Day 6 PM |

**Total**: ~36–40 hours (including testing & docs)  
**Critical Path**: Supabase (3h) → Hooks (5h) → UI components (19h) → Tests (8h)  
**Parallel**: Can start styling while hooks are being written

---

## Decision Points (Business)

### Q1: Supabase Backup Strategy
What happens if Supabase goes down during active trading? Fallback to REST API only? Implement local cache?

### Q2: Auth Timeline
Is Supabase Auth (magic link) required for launch, or can we mock sessions for Phase 1?

### Q3: EAR Computation on Frontend
Once Supabase is live, should frontend permanently stop computing EAR/Trust Score, or retain as redundant check?

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Supabase schema doesn't match backend | Medium | High | Create schema from backend models, validate API responses early |
| API response formats undocumented | Medium | Medium | Reference §11 of ARCHITECTURE.md; test each endpoint |
| Idempotency-Key collision | Low | Critical | Use crypto.randomUUID() (entropy sufficient) |
| Auth not ready on Day 1 | Medium | Low | Mock session for Phase 1, defer Supabase Auth to Phase 2 |
| Time-weighted risk calculation drift | Low | Medium | Verify formula in backend docs; test with known values |

---

## Acceptance Criteria

✅ **Decision feed displays** urgency-sorted mills without errors  
✅ **Effective rate field** displayed with observation band  
✅ **Idempotency-Key** header injected on every allocate-token call  
✅ **Baseline efficiency** fetched from Mill record, not hardcoded  
✅ **MERA tariff** fetched from TariffRate table, reflects Jan 2026 rate  
✅ **EAR computation** moved to display formatter (no parallel server computation)  
✅ **All tests passing** (unit + E2E)  
✅ **Owner can navigate decision-feed → mill detail → effective rate** without errors

---

## Next Steps

1. **Day 1**: Review this plan with team; confirm Supabase access + schema
2. **Day 1 PM**: Deploy schema; seed Nabiwi data; validate API responses
3. **Day 2**: Begin hooks + component development in parallel
4. **Day 6**: Deploy to staging; owner acceptance testing

**Ready to proceed?**
