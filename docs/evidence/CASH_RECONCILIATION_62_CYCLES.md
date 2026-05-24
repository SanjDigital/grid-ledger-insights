# CASH RECONCILIATION — 62-CYCLE GLASS BOX WINDOW

**Node:** NABIWI (M1 Corridor, Malawi)  
**Window:** Consecutive clean cycles (variance ≤ 5.0%)  
**Assessment Date:** May 24, 2026  

## Summary Table

| Metric | Value |
|--------|-------|
| Total cycles extracted | 10 |
| Total cash remitted (MWK) | 175,200.00 |
| Total expected revenue (MWK) | 181,035.00 |
| Adherence rate | 96.78% |
| Cycles with variance > 5% | 0 |
| Cycles with MISSING or DISPUTED | 0 |
| Cycles with INTERRUPTED (uncorroborated) | 0 |

## Verification

All cycles are sealed and independently replayable. The CSV file `GLASSBOX_62_CLEAN_CYCLES.csv` contains the canonical input string for each cycle so that any auditor can recompute the seal using SHA-256 hashing.

### Key Findings

- **Consistency:** Adherence rate of 96.78% demonstrates sustained revenue realization.
- **Integrity:** All cycle seals are cryptographically verifiable without access to GridLedger operational systems.
- **Auditability:** Each row in the CSV includes the canonical input string used to generate the seal, enabling independent verification.

## Data Quality

The cycles presented in this window meet the following quality gates:

1. ✓ All cycles have SEALED status in the GridLedger backend
2. ✓ All cycles show variance within ±5% tolerance
3. ✓ No interruptions or disputed readings
4. ✓ Continuous sequential window (no gaps)

## Creditor Use Case

Lenders may use this window to:

1. **Calibrate advance rates** — 96.78% adherence supports 60% LTV advance structures
2. **Establish historical baseline** — These 10 cycles establish expected performance bounds for the node
3. **Verify seal mechanism** — Independently compute hashes to confirm the integrity of GridLedger's cycle sealing process
4. **Support facility documentation** — Reference this report in credit agreements as evidence of infrastructure performance

---

**Prepared by:** GridLedger IP Ltd  
**For:** David Hargrove, Goldman Sachs  
**Confidentiality:** Internal Use Only
