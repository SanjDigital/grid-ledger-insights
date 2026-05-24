# CLEAN vs. DIRTY CYCLES — METHODOLOGY NOTE

**Purpose:** To clarify the institutional distinction between clean and dirty cycles in the GridLedger sealing protocol.

**Audience:** Credit teams, auditors, regulators  
**Version:** 1.0  
**Status:** Institutionally Clean  

---

## Definition

### Clean Cycle

A **clean cycle** is a sealed cycle record where:

1. **Variance is within ±5%:** The actual cash remitted falls between 95% and 105% of the expected revenue based on energy produced and the node's calibrated rate.
2. **No infrastructure interruption flags:** The operator completed the full 24-hour production window without interruptions that would be externally corroborated.
3. **Seal validity verified:** The SHA-256 hash of the canonical input string matches the stored seal hash.
4. **Complete evidence chain:** Energy readings, cash confirmations (Airtel Money), and timestamp alignment are all present.

**Example:**
```
Cycle: NAB-001
Energy: 41.0 kWh
Expected revenue: MWK 41,385
Actual cash: MWK 40,400
Variance: -2.4%
Status: CLEAN ✓
```

### Dirty Cycle

A **dirty cycle** is a sealed cycle record where one or more of the following is true:

1. **Variance exceeds ±5%:** Actual cash diverges from expected by more than the tolerance band.
   - **Over-remittance (>105%):** Operator paid more than expected (cash cushion, advance payment, penalty reversal).
   - **Under-remittance (<95%):** Operator remitted less than expected (revenue shortfall, disputed energy, cash diversion).

2. **Infrastructure interruption unconfirmed:** The operator reported an outage, but it was not corroborated by ESCOM registry data (Tier 1 exclusion) or by concurrent outages at peer nodes (Tier 2 exclusion).

3. **Seal mismatch:** The canonical input string does not hash to the stored seal value, indicating either data corruption or tampering.

4. **Incomplete evidence chain:** Missing energy readings, payment confirmations, or timestamp alignment issues.

**Examples:**
```
Cycle: NAB-051
Energy: 35.2 kWh
Expected revenue: MWK 35,550
Actual cash: MWK 29,800
Variance: -16.1%
Status: DIRTY (under-remittance) ✗

Cycle: NAB-042
Energy: 38.0 kWh
Expected revenue: MWK 38,400
Actual cash: MWK 38,400
Variance: 0.0%
Operator note: "Grid outage 12:00–14:00, 2 hours"
ESCOM confirmation: NOT YET RECEIVED (Tier 1 exclusion pending)
Status: DIRTY (unconfirmed interruption) ✗
```

---

## Statistical Use

### 62-Cycle Clean Window

The `GLASSBOX_62_CLEAN_CYCLES.csv` file represents a consecutive sequence of clean cycles. This window is used by lenders to:

- **Establish baseline performance** — What is the operator's typical variance and cash flow?
- **Calibrate advance rates** — At 96.78% adherence over 10 cycles, the operator can support 60% LTV structures.
- **Verify sealing integrity** — Hash all 10 cycles and confirm the mechanism works.

### Dirty Cycles in Exclusion Tables

When sovereign corroboration (ESCOM, Airtel Money, cluster concurrency) is integrated, dirty cycles will be reclassified:

- **Tier 1 (ESCOM-confirmed outage):** Excluded from adherence calc, operator not penalized.
- **Tier 2 (cluster-concurrency-confirmed outage):** Excluded from adherence calc, operator not penalized.
- **Tier 3 (operator breach):** Included in adherence calc as delinquency, operator subject to covenant breach.

---

## Why This Matters for Credit

### The Tri-Separation

GridLedger separates three dimensions that traditional credit systems conflate:

| Dimension | Definition | Example |
|-----------|-----------|---------|
| **Operator Discipline** | Does the operator remit cash as promised? | 10/10 cycles clean = operator is disciplined |
| **Infrastructure Reliability** | Does the grid or local infrastructure support production? | 12 outages in 31 days = infrastructure is fragile |
| **Verification Integrity** | Are the cycle seals cryptographically sound? | 100% hash match rate = integrity is high |

**Traditional credit systems:** Collapse all three into a single "credit score," which penalizes the operator for grid instability outside their control.

**GridLedger approach:** Separate them, so lenders can:
- Advance to disciplined operators even during infrastructure disruptions
- Apply infrastructure-specific remedies (covenant forbearance) rather than punishing operators
- Maintain verification transparency (hash replay) independent of credit decisions

---

## Operational Classification Example

**Nabiwi Node, March 2026:**

| Dimension | Finding |
|-----------|---------|
| Operator Discipline | **HIGH** — 62-cycle clean run, 93% adherence |
| Infrastructure Reliability | **LOW** — 12 outages in 31 days, IAF 0.38 |
| Verification Integrity | **HIGH** — 100% hash match rate, seal replay successful |

**Lender Decision:**
- ✓ Approve advance (operator is disciplined)
- ⚠ Set infrastructure-specific covenant (e.g., 60% LTV instead of 75%)
- ✓ Confirm seal mechanism before next drawdown (1-minute hash replay per REPLAY_INSTRUCTIONS_V1_0.md)

---

## Data Integrity Boundary

All cycles in the `GLASSBOX_62_CLEAN_CYCLES.csv` file:
- Are sealed and hash-verified
- Show variance within ±5%
- Have complete energy and cash evidence chains
- Are institutional clean for credit committee review

Dirty cycles and exclusion logic will be published separately as sovereign corroboration data is integrated.

---

## Footnote: Methodology Demonstration Status

The Nabiwi Fragility Profile contains exclusion tables that are **methodology demonstrations**, not attested production exclusions. They illustrate how the classification logic will work once ESCOM and Airtel Money records are cross-referenced. The canonical 10-cycle clean window in `GLASSBOX_62_CLEAN_CYCLES.csv` is production data, immediately suitable for credit review.

---

**Version:** 1.0  
**Date:** May 24, 2026  
**Prepared by:** GridLedger IP Ltd  
**For:** David Hargrove, Goldman Sachs  
**Status:** Institutionally Clean
