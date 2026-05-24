# CYCLE VERIFICATION REPORT TEMPLATE — PHASE 1

**Classification:** Institutional Clean  
**Version:** 1.0  
**Status:** Template  
**Date:** May 24, 2026  

---

## 1. Header Block

| Field | Value |
|-------|-------|
| **Node ID** | [NABIWI, TEST_MILL_01, etc.] |
| **Node Name** | [Full facility name] |
| **Reporting Period** | [Start date] to [End date] |
| **Report Date** | [ISO 8601 date] |
| **Analyst** | [Name/ID] |
| **Review Authority** | [Lender/Auditor name] |

---

## 2. Cycle Summary

| Metric | Value | Status |
|--------|-------|--------|
| Total cycles submitted | [N] | ✓ Complete |
| Total cycles sealed | [N] | ✓ Complete |
| Total cycles verified (hashes match) | [N] | ✓ Complete |
| Cycles with mismatched hashes | [N] | ✗ If N > 0: ALERT |
| Cycles with missing inputs | [N] | ✗ If N > 0: REJECT |
| Verification completion rate | [%] | ✓ If ≥ 99%: PASS |

---

## 3. Energy & Cash Reconciliation

| Metric | Total | Average per Cycle | Notes |
|--------|-------|-------------------|-------|
| Total energy produced (kWh) | [N] | [N/M] | From meter readings |
| Total expected revenue (MWK) | [N] | [N/M] | @ calibrated rate |
| Total actual cash remitted (MWK) | [N] | [N/M] | From Airtel Money confirmations |
| **Adherence rate** | **[%]** | — | = actual / expected × 100% |
| Variance tolerance band | ±5% | — | Acceptable range |
| Cycles exceeding variance | [N] | — | ✗ If N > 0: Review required |

---

## 4. Seal Integrity Audit

### Hash Verification Results

**Method:** SHA-256 recompute of canonical input string

| Cycle ID | Canonical String | Computed Hash | CSV Hash | Match | Status |
|----------|------------------|---------------|----------|-------|--------|
| [ID] | `{mill_id}\|{start}\|{end}\|...` | `[hash]` | `[hash]` | ✓/✗ | VERIFIED / FAILED |
| … | … | … | … | … | … |

**Summary:**
- Total hashes verified: [N]
- Hash match rate: [%]
- Hash failures: [N]

**Conclusion:** If hash match rate ≥ 99%, cycle sealing mechanism is functionally intact.

---

## 5. Exclusion Audit (Methodology Demonstration)

*This section applies when sovereign corroboration data is integrated (ESCOM registry, Airtel Money receipts, cluster concurrency).*

### Exclusion Classifications

| Tier | Definition | Example | Count | Notes |
|------|-----------|---------|-------|-------|
| **Tier 1** | ESCOM registry mismatch | Power outage unconfirmed by utility | [N] | Requires sovereign confirmation |
| **Tier 2** | Cluster concurrency absent | Single node interrupted, no peer correlation | [N] | Requires ≥3 nodes simultaneous outage |
| **Tier 3** | Operator failure | Operator in breach of SLA | [N] | Deducted from adherence rate |

### Included vs. Excluded Cycles

- **Included in throughput:** [N] cycles (clean-cycle ratio = [%])
- **Excluded (infrastructure):** [N] cycles (Tier 1–2, pending sovereign confirmation)
- **Excluded (operator):** [N] cycles (Tier 3)
- **Disputed:** [N] cycles (awaiting clarification)

---

## 6. Infrastructure Availability Factor (IAF)

$$\text{IAF} = \frac{\text{clean cycles}}{\text{total expected cycles in window}}$$

| Window | Value | Interpretation |
|--------|-------|-----------------|
| Last 7 days | [%] | — |
| Last 30 days | [%] | — |
| Full reporting period | [%] | — |

**Threshold:** IAF ≥ 0.40 permits advance drawdowns. IAF < 0.40 triggers review.

**Result:** IAF = [%]. Status: ✓ PASS / ⚠ REVIEW / ✗ FAIL

---

## 7. Covenant Compliance Checklist

| Covenant | Requirement | Observed | Status |
|----------|-------------|----------|--------|
| Adherence minimum | ≥90% | [%] | ✓/✗ |
| IAF minimum | ≥0.40 | [%] | ✓/✗ |
| Variance tolerance | ±5% | [%] out of spec | ✓/✗ |
| Seal validity rate | ≥99% | [%] | ✓/✗ |
| Cycle submission frequency | Daily | [N] late submissions | ✓/✗ |

**Overall Covenant Status:** ✓ PASS / ⚠ CONDITIONAL / ✗ FAIL

---

## 8. Drawdown Recommendation

| Dimension | Assessment |
|-----------|------------|
| **Energy Production** | [Adequate / Constrained / Interrupted] |
| **Cash Realization** | [Strong / Marginal / Weak] |
| **Verification Integrity** | [High confidence / Moderate confidence / Low confidence] |
| **Infrastructure Stability** | [Stable / Degrading / Critical] |

### Recommendation

**[✓ APPROVE DRAWDOWN / ⚠ CONDITIONAL APPROVAL / ✗ SUSPEND DRAWDOWN]**

**Rationale:** [2–3 sentence summary of key findings]

**Conditions (if applicable):**
- [ ] [Condition 1]
- [ ] [Condition 2]

**Lender Authority:** [Name, Title, Signature]

---

## 9. Audit Trail

| Field | Entry |
|-------|-------|
| Prepared by | [Name, Date] |
| Reviewed by | [Name, Date] |
| Approved by | [Lender authority, Date] |
| Data sources | GLASSBOX_62_CLEAN_CYCLES.csv, Airtel Money statements, ESCOM registry (where available) |
| Verification method | SHA-256 hash replay per REPLAY_INSTRUCTIONS_V1_0.md |
| Confidence level | [High / Moderate / Low] |

---

## 10. Disclaimer

GridLedger IP Ltd provides cycle verification outputs only. All credit decisions remain the sole responsibility of the Lender. This report is not legal, financial, or credit advice. The Lender retains full discretion over drawdown authorization, covenant enforcement, and remedy.

---

**Template Version:** 1.0  
**For use with:** GLASSBOX_62_CLEAN_CYCLES.csv, CASH_RECONCILIATION_62_CYCLES.md, FACILITY_COVENANT_LANGUAGE_V1_0.md  
**Status:** Institutionally Clean
