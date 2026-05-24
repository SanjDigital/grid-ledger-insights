# DATA ROOM MANIFEST — GOLDMAN SACHS CREDIT REVIEW PACKAGE

**Recipient:** David Hargrove, Goldman Sachs  
**Date Prepared:** May 24, 2026  
**Classification:** Institutional Clean  
**Status:** Ready for transmission  

---

## Contents

This package contains five core deliverables plus supplementary methodology notes for credit analysis of the Nabiwi node under the Grid-Verified Cycle Facility (GVCF) framework.

### Primary Deliverables

#### 1. **GLASSBOX_62_CLEAN_CYCLES.csv**
- **Type:** Data (CSV, 10 rows)
- **Purpose:** Extraction of consecutive clean cycles for hash replay verification
- **Key Metrics:**
  - 10 consecutive clean cycles (variance ≤ 5%)
  - Total cash remitted: MWK 175,200.00
  - Total expected revenue: MWK 181,035.00
  - Adherence rate: 96.78%
- **Use Case:** Credit team can independently verify all cycle seals using REPLAY_INSTRUCTIONS_V1_0.md
- **Format:** Standard CSV with columns: cycle_id, cycle_start, cycle_end, total_usage_kwh, total_actual_cash, expected_revenue, variance_pct, canonical_input_string, seal_hash

#### 2. **CASH_RECONCILIATION_62_CYCLES.md**
- **Type:** Report (Markdown)
- **Purpose:** Reconcile the 10-cycle window totals and demonstrate cash flow consistency
- **Key Content:**
  - Financial summary table
  - Verification methodology
  - Data quality gates
  - Creditor use cases
- **Status:** Institutionally clean; ready for underwriting committee

#### 3. **CYCLE_VERIFICATION_REPORT_TEMPLATE_V1_0.md**
- **Type:** Template (Markdown)
- **Purpose:** Standardized format for ongoing cycle verification reports
- **Sections:**
  - Header block (node identification, reporting period)
  - Cycle summary (counts, completion rates)
  - Energy & cash reconciliation
  - Seal integrity audit (hash verification)
  - Exclusion audit (methodology demonstration)
  - Infrastructure Availability Factor (IAF)
  - Covenant compliance checklist
  - Drawdown recommendation
  - Audit trail
- **Use Case:** Can be completed by any auditor for any production cycle window

#### 4. **NABIWI_FRAGILITY_PROFILE_V1_0.pdf**
- **Type:** Report (PDF)
- **Purpose:** Node-level infrastructure assessment over 31-day observation window
- **Key Metrics:**
  - Gross energy availability (metered)
  - Verified production throughput
  - Infrastructure Fragility Delta (tri-separation of operator discipline, infrastructure reliability, verification integrity)
  - Grid Stability Index: 38
  - Outage frequency: 12 events (methodology demonstration)
  - Verified throughput continuity: 93%
- **Methodology:** Illustrates exclusion classification logic pending sovereign corroboration (ESCOM, Airtel Money)
- **Status:** Methodology demonstration; full production exclusion tables pending integration of external data sources

#### 5. **FACILITY_COVENANT_LANGUAGE_V1_0.md**
- **Type:** Template (Markdown)
- **Purpose:** Example drawdown conditions for a regulated lender's credit agreement
- **Key Clauses:**
  - Adherence Threshold (≥90% trailing 10-cycle)
  - Infrastructure Availability Gate (IAF ≥0.40)
  - Seal Validity (SHA-256 verification)
  - Revenue Shortfall Event (tolerance band 5%)
  - Cross-cycle Compounding boundary (60% LTV per cycle)
- **Constitutional Boundary:** GridLedger is not a counterparty; lender retains all credit decisions
- **Verification:** Independent hash replay requires no access to GridLedger systems

---

## Supplementary Documents

#### A. **REPLAY_INSTRUCTIONS_V1_0.md**
- **Purpose:** Step-by-step guide for independent verification of cycle seals
- **Prerequisites:** Python 3.9+, SHA-256 capability
- **Time to verify one cycle:** < 2 minutes
- **Key Script:** Simple Python hash replay demonstrates cryptographic integrity
- **Outcome:** Match or mismatch determines seal validity

#### B. **CLEAN_vs_DIRTY_CYCLES_METHODOLOGY_NOTE.md**
- **Purpose:** Clarify institutional definitions of clean vs. dirty cycles
- **Content:**
  - Definition of clean cycle (variance ±5%, no unconfirmed interruptions, seal valid)
  - Definition of dirty cycle (variance >5%, unconfirmed interruptions, seal mismatch, incomplete evidence)
  - Statistical use case (62-cycle clean windows for baseline calibration)
  - Why this matters for credit (tri-separation of operator discipline, infrastructure reliability, verification integrity)
  - Operational classification example (Nabiwi: HIGH operator discipline, LOW infrastructure reliability, HIGH verification integrity)
- **Status:** Institutional methodology

---

## Verification Checklist

- [x] CSV file contains canonical input strings for all rows
- [x] Cash reconciliation figures reconcile to CSV totals
- [x] Hash replay instructions are complete and tested
- [x] Facility covenant language is institutionally clean
- [x] Fragility Profile PDF is included
- [x] All files are versioned and dated
- [x] No external dependencies (all verification can be performed offline)
- [x] All files frozen (ready for archival)

---

## File Manifest & Versioning

| Filename | Version | Date | Status | Size |
|----------|---------|------|--------|------|
| GLASSBOX_62_CLEAN_CYCLES.csv | 1.0 | 2026-05-24 | Frozen | [auto] |
| CASH_RECONCILIATION_62_CYCLES.md | 1.0 | 2026-05-24 | Frozen | [auto] |
| CYCLE_VERIFICATION_REPORT_TEMPLATE_V1_0.md | 1.0 | 2026-05-24 | Frozen | [auto] |
| NABIWI_FRAGILITY_PROFILE_V1_0.pdf | 1.0 | 2026-05-24 | Frozen | [auto] |
| FACILITY_COVENANT_LANGUAGE_V1_0.md | 1.0 | 2026-05-24 | Frozen | [auto] |
| REPLAY_INSTRUCTIONS_V1_0.md | 1.0 | 2026-05-24 | Frozen | [auto] |
| CLEAN_vs_DIRTY_CYCLES_METHODOLOGY_NOTE.md | 1.0 | 2026-05-24 | Frozen | [auto] |

---

## Transmission Protocol

### Before Sending

1. Verify all files exist: `docs/evidence/` directory
2. Run spot check on CSV: `python verify_glassbox.py` (see REPLAY_INSTRUCTIONS_V1_0.md)
3. Confirm all markdown files render correctly in recipient's viewer
4. Preserve file timestamps and hashes

### Compression & Transport

- Recommend: ZIP archive, password-protected (credential to be shared via separate secure channel)
- Include this manifest as `README.md` in the archive
- Send via [secure delivery mechanism specified separately]

### Recipient Instructions

1. Extract archive
2. Open `README.md` (this manifest) first
3. Review CASH_RECONCILIATION_62_CYCLES.md for financial summary
4. Open GLASSBOX_62_CLEAN_CYCLES.csv in spreadsheet application
5. Follow REPLAY_INSTRUCTIONS_V1_0.md to verify 2–3 cycle hashes independently
6. Review CYCLE_VERIFICATION_REPORT_TEMPLATE_V1_0.md to understand ongoing verification process
7. Consult FACILITY_COVENANT_LANGUAGE_V1_0.md for credit agreement drafting
8. Reference NABIWI_FRAGILITY_PROFILE_V1_0.pdf for infrastructure assessment
9. Use CLEAN_vs_DIRTY_CYCLES_METHODOLOGY_NOTE.md for definitions and tri-separation logic

---

## Technical Support

**If verification fails:**
- Confirm CSV file was not modified during transmission (size and modification date should match manifest)
- Ensure Python 3.9+ with hashlib installed
- Manually re-copy canonical_input_string from CSV to eliminate transcription errors
- Contact GridLedger IP Ltd for log files

**If questions arise:**
- Refer to FACILITY_COVENANT_LANGUAGE_V1_0.md for drawdown mechanics
- Refer to CLEAN_vs_DIRTY_CYCLES_METHODOLOGY_NOTE.md for cycle definitions
- Refer to REPLAY_INSTRUCTIONS_V1_0.md for hash verification troubleshooting

---

## Confidentiality

This package contains commercially sensitive operational and financial data. Restrict distribution to:
- Goldman Sachs credit committee
- External auditors (if authorized by borrower)
- Regulators (if legally required)

Do not share with borrower (Nabiwi operator) without explicit consent from GridLedger IP Ltd.

---

## Governance

- **Prepared by:** GridLedger IP Ltd, May 24, 2026
- **Reviewed by:** [Internal governance review — date pending]
- **Approved for transmission:** [Date pending internal authorization]
- **Recipient:** David Hargrove, Goldman Sachs
- **Expiration:** No expiration; frozen for indefinite archival use

---

**Next Steps:** Commit to Trust Anchor, prepare secure transmission, and coordinate delivery date with David Hargrove.
