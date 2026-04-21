# Effective Rate Tracking: Deployment & Calibration Protocol

**Status:** Ready for deployment  
**Ground truth established:** Nabiwi Feb–Mar 2026 (19 cycles, 1,347 MWK/bucket average)  
**Phase:** Observation (no enforcement yet)  
**Date:** April 14, 2026

---

## 📋 Deployment Checklist

- [x] `effective_rate_per_kwh` added to `DecisionBasis` model
- [x] `_compute_effective_rate_per_kwh()` helper function created
- [x] Integration into `_build_decision_basis()` (computed on every read)
- [x] Nabiwi calibration data extracted (19 cycles, 2,026 Feb–Mar)
- [x] Ground truth baseline established (1,347 MWK/bucket, ±0.2% variance)
- [ ] Deploy to staging
- [ ] Begin cycle observation logging
- [ ] Monitor 5–10 cycles per mill before any enforcement

---

## 🎯 Observation Bands (No Enforcement)

### Nabiwi (Calibrated)

| Band | Lower | Upper | Status | Action |
|------|-------|-------|--------|--------|
| **Observation** | 1,340 | 1,360 | Primary window | Log only |
| **Warning** | 1,320 | 1,380 | Wider tolerance | Flag if reached, don't block |
| **Anomaly** | <1,100 or >1,500 | — | Outside phase 1 band | Manual review required |

**Rationale:** 
- Observation band (±0.7%) reflects 2-month historical variance
- Warning band (±2.2%) allows for temporary market moves
- Anomaly band matches Phase 1 conservative range
- Zero enforcement gates – all data flows through to audit trail

---

### New Mills (Generic Phase 1)

| Band | Lower | Upper | Status | Action |
|------|-------|-------|--------|--------|
| **Observation** | — | — | Establishing baseline | Collect 5–10 cycles first |
| **Warning** | 1,100 | 1,500 | Phase 1 range | Monitor for pattern |
| **Anomaly** | <800 or >2,000 | — | Extreme outlier | Immediate review |

**Process:**
1. Deploy to new mill
2. Log first 5 cycles without any band
3. Calculate mill-specific median + std deviation
4. Establish observation band: median ± 2σ
5. Move to monitoring phase after 10 cycles

---

## 📊 Logging & Audit Trail

### What Gets Logged (For Every Cycle)

```json
{
  "cycle_id": "NABIWI_20260415_001",
  "mill_id": "NABIWI_01",
  "timestamp": "2026-04-15T14:30:00Z",
  "allocation": {
    "allocated_kwh": 59.9,
    "allocated_at": "2026-04-15T10:00:00Z"
  },
  "execution": {
    "actual_revenue_received": 81000,
    "receipt_recorded_at": "2026-04-15T18:00:00Z"
  },
  "forensic_metrics": {
    "effective_rate_per_kwh": 1350.00,
    "effective_rate_per_bucket": 1350.00,
    "buckets_processed": 60,
    "variance_from_budgeted_1350": 0.0,
    "variance_percent": 0.0
  },
  "band_status": {
    "mill": "NABIWI_01",
    "band_lower": 1340,
    "band_upper": 1360,
    "in_band": true,
    "band_type": "observation",
    "observation_note": "Stable within Nabiwi calibration range"
  },
  "decision_basis": {
    "capital_at_risk": 0,
    "time_weighted_risk": 0,
    "effective_rate_per_kwh": 1350.00,
    "cycle_state": "IDLE",
    "simulated_allocation_kwh": 59.9,
    "simulated_expected_revenue": 80865.00
  },
  "energy_cash_reconciliation": {
    "energy_source": "ESCOM_token",
    "token_mwk_cost": 16500,
    "token_kwh": 64.8,
    "energy_cost_per_kwh": 254.63,
    "revenue_per_kwh": 1350.00,
    "gross_margin_percent": 80.8
  }
}
```

### Observation Log (Human-Readable)

Every 5 cycles, generate summary:

| Mill | Cycles | Avg Rate | Min | Max | In Band? | Deviation | Notes |
|------|--------|----------|-----|-----|----------|-----------|-------|
| NABIWI_01 | 5–10 | 1,347 | 1,333 | 1,350 | ✅ Yes | -0.2% | Stable |
| MKWINDA_01 | 1–5 | — | — | — | 🔍 TBD | — | Baseline gathering |

---

## 🚨 Scenario Responses (Observation Phase)

### Scenario 1: Cycle within band (e.g., 1,348 MWK/bucket for Nabiwi)

**Decision:** ✅ Approve and log  
**Action:** No operator contact needed. Log to audit trail.  
**Follow-up:** None.

---

### Scenario 2: Cycle in warning band but outside observation (e.g., 1,320 MWK/bucket for Nabiwi)

**Decision:** ✅ Approve and log  
**Flag:** Investigate (do not block)  
**Action:** 
1. Log observation: "Rate below normal band"
2. **Do not send alert to operator yet** (observation phase)
3. Staff reviews next SMS from operator
4. Check for: customer mix shift, competitive pressure, or data error
5. Log review decision

**Example:**
```
Flag: 2026-04-15 – Nabiwi effective rate 1,325 (below 1,340 band)
Operator SMS context: "Ndiye kuti magulitsi angosala amagula maite ache malo achigayo" 
  = Customers are buying individual 5L units instead of 20L buckets (mix shift)
Conclusion: Legitimate market behaviour, not fraud → Update band observation
Status: Continue monitoring
```

---

### Scenario 3: Cycle outside warning band (e.g., <1,100 for Nabiwi)

**Decision:** ✅ Approve and log (still observation phase)  
**Flag:** Immediate manual review  
**Action:**
1. Flag in decision feed as MANUAL_REVIEW_REQUIRED
2. Generate alert for operations team (non-blocking)
3. Operator not contacted automatically
4. Staff investigates within 24 hours
5. Log findings in audit trail

**Possible causes:**
- Data entry error in SMS (typo)
- Bulk discount transaction (legitimate price negotiation)
- Measurement error (meter or reconciliation)
- Genuine fraud or meter tampering (unlikely at this phase given Nabiwi data)

---

### Scenario 4: New mill's first cycle

**Decision:** ✅ Log (no band yet)  
**Action:**
1. Record effective_rate_per_kwh
2. Collect 4 more cycles
3. Calculate median + std dev
4. Establish mill-specific band
5. Begin observation phase when 5 cycles collected

---

## 📈 Transition from Observation to Enforcement (Not Yet)

### Criteria for Tightening Band (After 10 Clean Cycles)

Monitor for 10 consecutive cycles without deviation:

1. If all 10 cycles within observation band → **band is valid**
2. Calculate new tight band: median ± 1σ (instead of ±2σ)
3. Continue observation for 5 more cycles with tight band
4. If all 15 stable → band is "hardened"

### Criteria for Moving to Light Enforcement (Future Phase)

After 20+ clean cycles AND forensic film verification:

1. Effective_rate < lower_band: flag as **LOW_RATE_WARNING** (not blocking)
2. Effective_rate > upper_band: flag as **HIGH_RATE_ALERT** (not blocking)
3. Effective_rate outside Phase 1 band: flag as **MANUAL_REVIEW** (investigate, don't block)

**No automatic rejection ever** – band is for early warning, not gate.

---

## 🧪 Quality Gates (What Still Gates Allocation)

**These remain unchanged** – only observation adds new metrics:

| Gate | Current Rule | Change |
|------|---|---|
| **Active cycle check** | Blocks if PENDING/MISSING/DISPUTED | No change |
| **Exposure limit** | Blocks if exposure > MAX_EXPOSURE_PER_MILL | No change |
| **Idempotency** | Blocks duplicate allocations | No change |
| **Time-weighted risk** | Inflates exposure for old cycles | No change |
| **Effective rate band** | **Observation only (no gate)** | NEW – monitoring, no enforcement |

---

## 📍 Staged Deployment: What to Do Monday (Day 1)

### Pre-Deployment

1. Back up database: `cp data/gridledger.db data/gridledger.backup-effective-rate`
2. Review code changes (already done – zero syntax errors)
3. Verify observation band settings in tool/config (Nabiwi: 1,340–1,360)

### Post-Deployment (After Restart)

1. Make one allocation to Nabiwi with new code
2. Verify `effective_rate_per_kwh` appears in decision_basis JSON response
3. Check audit trail includes effective_rate fields
4. Take screenshot of output for team verification

### Week 1: Observation Window

1. Log allocations for Nabiwi (expected sequence: 1,350, 1,350, 1,350, 1,350, 1,350)
2. If all match band → document "Baseline confirmed"
3. If any deviation → document reason and impact

### Week 2: Second Mill

1. Deploy code to second mill (e.g., Mkwinda)
2. Collect first 5 cycles
3. Calculate mill-specific band
4. Begin observation phase for that mill

---

## 💡 What Happens Now vs. Later

### NOW (Observation Phase – Weeks 1–2)

✅ **Compute effective_rate_per_kwh** for every cycle  
✅ **Log to audit trail**  
✅ **Monitor against band**  
✅ **Flag anomalies for staff review** (non-blocking)  
✅ **Collect 5–10 cycles per mill**  

❌ **Do NOT block allocations** based on band  
❌ **Do NOT send alerts to operators** yet  
❌ **Do NOT assume band applies to other mills**  

### LATER (After 10 Clean Cycles + Forensic Film)

🔜 **Tighten band to ±1σ**  
🔜 **Move from observation to monitoring**  
🔜 **Send yellow flags (not blocking) for outside-band rates**  
🔜 **Consider light enforcement** (flagging, not gating)  
🔜 **Apply per-mill bands** with forensic ground truth  

---

## 🎯 Success Criteria (Next 2 Weeks)

| Criteria | Target | Status |
|----------|--------|--------|
| Effective_rate computed for 100% of cycles | ✅ 100% | Monitor |
| Nabiwi cycles logged | ✅ 5–10 cycles | In progress |
| Nabiwi band confidence | ✅ All in 1,340–1,360 | Expected |
| Second mill band established | ✅ By end week 2 | On track |
| Zero blocking errors from band logic | ✅ 0% | Expected (observation only) |
| Staff review process identified | ✅ Documented | Done |

---

## 📚 Reference Documents

- **Calibration data:** [NABIWI_FEB_MAR_2026_CYCLE_ANALYSIS.md](NABIWI_FEB_MAR_2026_CYCLE_ANALYSIS.md)
- **Cycle calibration details:** [NABIWI_CYCLE_CALIBRATION.md](NABIWI_CYCLE_CALIBRATION.md)
- **Implementation status:** [PHASE_1_IMPLEMENTATION.md](PHASE_1_IMPLEMENTATION.md)

---

## 🚀 Go/No-Go Decision

**Code Status:** ✅ Ready (zero syntax errors, all imports correct)  
**Calibration Data:** ✅ Ready (Nabiwi 19-cycle baseline established)  
**Observation Protocol:** ✅ Ready (bands defined, logging specified)  
**Enforcement Gates:** ✅ Unchanged (only observation added)  

**Recommendation:** Deploy to staging immediately. Begin observation window this week.

---

**Protocol Created:** April 14, 2026  
**Ground Truth Source:** 32-month Nabiwi SMS record + 19-cycle forensic extraction  
**Next Review:** After 5 cycles deployed  
**Status:** READY FOR DEPLOYMENT
