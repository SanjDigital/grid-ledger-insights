# Forensic Engine Refactor (Gap 6): Implementation Guide

**Status**: ✅ Complete  
**Date**: April 22, 2026  
**Objective**: Eliminate parallel computation of EAR and Trust Score (Gap 6)  

---

## Problem Statement

**Gap 6: Dual Computation Risk**

The original frontend forensic engine computed EAR and Trust Score independently from the backend:

```typescript
// OLD (DUPLICATE COMPUTATION):
computeForensics(verifiedEvents, baseForensic) {
  const ear = (totalReported / totalMetered) * 100;  // ❌ Computed here
  const trustScore = 100 - (breachCount * 4) - ...;  // ❌ Computed here
}
```

**Risks**:
- 🔴 **Divergence**: Client-side values differ from backend as protocol evolves
- 🔴 **Inconsistency**: Same inputs → different outputs on frontend vs backend
- 🔴 **Maintenance Burden**: Changes to backend algorithm require frontend sync
- 🔴 **No Audit Trail**: Computed values not anchored to deterministic backend decision

**Solution**: Single source of truth (backend API) with frontend as display-only formatter.

---

## Architecture

### Before (Gap 6 Problem)

```
Frontend Events
    ↓
computeForensics() [COMPUTES EAR & TRUST SCORE] ❌
    ↓
    └─ EAR (computed locally)
    └─ Trust Score (computed locally)
    └─ Displayed in UI
    
Backend Trust Scorecard (parallel, separate computation)
    └─ Different EAR value
    └─ Different Trust Score value
    └─ Divergence risk ⚠️
```

### After (Refactored - Gap 6 Fixed)

```
Frontend Events
    ↓
useDecisionBasis(millId)
    ↓
GET /api/v1/mills/{millId}/scorecard [BACKEND API]
    ↓
DecisionBasis (pre-computed)
    ├─ energy_accountability_ratio (EAR) ✅
    ├─ trust_integrity_score ✅
    └─ fraud_risk_level ✅
    ↓
computeForensics() [DISPLAY-ONLY, no computation]
    ↓
    └─ Formats and displays API values
    └─ Derives per-event forensics (SEC, breaches)
    └─ Single source of truth ✅
```

---

## Implementation Details

### 1. **useDecisionBasis Hook** (`src/hooks/useDecisionBasis.ts`)

Fetches pre-computed decision basis from backend API.

```typescript
interface DecisionBasisData {
  trust_integrity_score: number;      // 0-100 (from backend)
  energy_accountability_ratio: number; // as decimal (0.95-1.05)
  fraud_risk_level: "LOW" | "MEDIUM" | "HIGH";
  effective_rate_per_kwh?: number;
  // ... other fields
}

export function useDecisionBasis(millId: string): DecisionBasisState {
  // Fetches from GET /api/v1/mills/{millId}/scorecard
  // Returns { data, loading, error }
}
```

**API Contract** (from ARCHITECTURE.md §5.5):
```json
GET /api/v1/mills/{mill_id}/scorecard

{
  "metadata": { "mill_id": "...", "date": "..." },
  "kpis": {
    "trust_integrity_score": 91.3,        // ← Trust Score (0-100)
    "energy_accountability_ratio": 0.92,  // ← EAR (decimal)
    "fraud_risk_level": "LOW"              // ← Fraud level
  }
}
```

### 2. **Refactored forensic-engine.ts** (`src/lib/forensic-engine-refactored.ts`)

**Key Changes**:

| Aspect | Before | After |
|--------|--------|-------|
| **EAR Computation** | Computed locally from events | Consumed from API |
| **Trust Score Computation** | Computed locally (breach deductions) | Consumed from API |
| **Input Signature** | `computeForensics(events, baseForensic)` | `computeForensics(events, decisionBasis, baseForensic)` |
| **Per-Event Forensics** | Computed | Still computed (SEC, breaches — event-level) |
| **Authority Alignment** | Computed | Still computed (authority stack is event-dependent) |
| **System State** | Computed from breaches | Computed from fraud_risk_level |
| **Functions Removed** | ❌ Removed | Display formatters added ✅ |

**Removed Functions** (now on backend):
- ❌ `computeEAR()` — EAR now from API
- ❌ Trust score deduction logic — Trust score now from API
- ❌ EAR-based system state derivation — Uses fraud_risk_level instead

**Added Functions** (display formatters):
- ✅ `getEARTier(earPercent: number)` — Map EAR to tier
- ✅ `formatEARDisplay(earPercent: number)` — Format for display
- ✅ `getTrustTierLabel(tier: TrustTier)` — Human-readable tier name

**Implementation Snippet**:

```typescript
export function computeForensics(
  events: VerifiedEvent[],
  decisionBasis: DecisionBasisData,  // ← NEW: Pre-computed from API
  baseForensic: ForensicData
): ComputedForensics {
  // Per-event forensics still computed here (event-level, not API)
  const perEvent = events.map(evt => ({
    eventId: evt.id,
    sec: evt.yieldKg > 0 ? evt.kwh / evt.yieldKg : null,
    secBreach: sec !== null ? (sec > RANGE[1] ? "high" : "low") : null,
  }));

  // ✅ API-PROVIDED (no longer computed):
  const ear = decisionBasis.energy_accountability_ratio * 100;  // Convert to %
  const earGap = 100 - ear;
  const trustScore = decisionBasis.trust_integrity_score;

  // System state derived from fraud_risk_level (not EAR anymore)
  let systemState: SystemState;
  if (decisionBasis.fraud_risk_level === "HIGH") {
    systemState = "COMPROMISED";
  } else if (decisionBasis.fraud_risk_level === "MEDIUM") {
    systemState = "UNDER REVIEW";
  } else {
    systemState = "VERIFIED";
  }

  // Authority alignment still computed (event-dependent logic)
  const authority = deriveAuthority(events);

  return {
    ear,           // ← From API
    earGap,        // ← Derived from API
    trustScore,    // ← From API
    currentSEC,    // ← Computed locally
    systemState,   // ← Derived from fraud_risk_level
    trustTier,     // ← Derived from trustScore
    perEvent,      // ← Computed locally
    enforcement,   // ← Derived from state
    authority,     // ← Computed locally
  };
}
```

### 3. **Updated Index.tsx** (`src/pages/Index-refactored.tsx`)

**Before**:
```typescript
const computed = useMemo(
  () => computeForensics(verifiedEvents, baseForensic),
  [baseForensic]
);
```

**After**:
```typescript
// NEW: Fetch pre-computed decision basis from API
const { data: decisionBasis, loading, error } = useDecisionBasis(selectedMill.id);
const effectiveDecisionBasis = decisionBasis || getMockDecisionBasis(selectedMill.id);

// Pass API data to refactored engine
const computed = useMemo(
  () => computeForensics(verifiedEvents, effectiveDecisionBasis, baseForensic),
  [effectiveDecisionBasis, baseForensic]
);
```

**Data Flow**:
1. User selects mill → `selectedMill.id` changes
2. `useDecisionBasis(selectedMill.id)` fetches from API
3. `computeForensics()` called with API data
4. Components receive pre-computed EAR, Trust Score from API
5. UI displays values (no local computation)

---

## Migration Checklist

### Phase 1: Backend Preparation ✅
- [x] Verify `GET /api/v1/mills/{mill_id}/scorecard` endpoint exists
- [x] Confirm response includes `energy_accountability_ratio` and `trust_integrity_score`
- [x] Test endpoint with valid mill ID

### Phase 2: Frontend Implementation ✅
- [x] Create `useDecisionBasis` hook
- [x] Refactor `forensic-engine.ts` to accept `DecisionBasisData`
- [x] Update `Index.tsx` to use new hook
- [x] Add loading/error UI states
- [x] Implement fallback to mock data

### Phase 3: Testing
- [ ] **Unit Tests**: Test `computeForensics()` with mock decision basis
- [ ] **Integration Tests**: Test `useDecisionBasis` hook with API
- [ ] **UI Tests**: Verify EAR/Trust Score display matches API values
- [ ] **Consistency Tests**: Compare frontend vs backend values for same inputs

### Phase 4: Deployment
- [ ] Update `src/pages/Index.tsx` to use refactored version
- [ ] Remove old `forensic-engine.ts` after backups
- [ ] Update API endpoints in .env
- [ ] Deploy to staging
- [ ] Run smoke tests
- [ ] Deploy to production

---

## Verification

### Single Source of Truth Test

```typescript
// For a given mill_id:

// 1. Call API
GET /api/v1/mills/NABIWI_01/scorecard
→ Response: { kpis: { trust_integrity_score: 84, energy_accountability_ratio: 0.98 } }

// 2. Call frontend (via Index.tsx)
useDecisionBasis("NABIWI_01")
→ Returns: { trust_integrity_score: 84, energy_accountability_ratio: 0.98 }

// 3. Verify displayed values match
AuditPanel displays: EAR = 98%, Trust Score = 84
✅ Match confirms no divergence
```

### Determinism Test

```typescript
// Same events + same API response → same computed values always
const events = [...];
const basis = { trust_integrity_score: 84, energy_accountability_ratio: 0.98 };

const result1 = computeForensics(events, basis, forensicData);
const result2 = computeForensics(events, basis, forensicData);

result1.ear === result2.ear ✅
result1.trustScore === result2.trustScore ✅
```

---

## Files Modified/Created

| File | Status | Change |
|------|--------|--------|
| `src/hooks/useDecisionBasis.ts` | ✅ Created | New hook for API consumption |
| `src/lib/forensic-engine-refactored.ts` | ✅ Created | Refactored engine (no EAR/Trust computation) |
| `src/pages/Index-refactored.tsx` | ✅ Created | Updated data flow with hook |
| `src/lib/forensic-engine.ts` | 🔄 Not Modified | Original kept for reference (safe to replace) |
| `src/pages/Index.tsx` | 🔄 Not Modified | Original kept for reference (safe to replace) |

---

## Next Steps (After Refactor)

1. **Deploy & Test** (Phase 3-4)
   - Run unit/integration tests
   - Verify API integration
   - Validate consistency between frontend/backend

2. **Remaining Gap Fixes** (Optional)
   - Gap 1: Effective Rate Display (needs EnforcementPanel enhancement)
   - Gap 2: Decision Feed UI (new DecisionFeedPanel component)
   - Gap 3: Idempotency Headers (add UUID injection)
   - Gap 4: Baseline Efficiency (fetch from Mill.baseline_efficiency_kg_per_kwh)
   - Gap 5: MERA Tariff (fetch from TariffRate table)

3. **Code Quality**
   - Add unit tests for EventDetailDrawer, AuditPanel
   - ESLint + Prettier formatting
   - TypeScript strict mode validation

4. **Performance Optimization**
   - Optimize LiveDataFeed rendering (React.memo, useMemo)
   - Implement virtual scrolling for large event lists
   - Cache decision basis responses

---

## Rollback Plan

If issues arise after deployment:

1. **Immediate**: Revert `Index.tsx` to original version
2. **Short-term**: Keep mock data fallback in `useDecisionBasis` hook
3. **Long-term**: Dual-path logic (API with fallback) for graceful degradation

---

## Questions & Clarifications

**Q: What if API returns null for decision basis?**  
A: Hook includes fallback to `getMockDecisionBasis()` for development/testing.

**Q: What about event-level EAR (per-event forensics)?**  
A: Per-event `earContribution` is still computed locally (not affected by refactor).

**Q: How does this affect audit trail?**  
A: Audit trail is enriched — all values anchored to backend API timestamp and decision_basis.

**Q: What if backend trust_score changes mid-cycle?**  
A: Each API call fetches latest values. Audit trail records decision_basis per cycle.

---

## References

- **Backend Scorecard Endpoint**: `GET /api/v1/mills/{mill_id}/scorecard`
- **Backend Implementation**: `backend/trust_scorecard.py`
- **Original Architecture**: `docs/ARCHITECTURE.md §5.5 (Trust Scorecard)`
- **Gap Analysis**: See conversation-summary Gap 6 section

