# CANONICAL_TERMINOLOGY_V1_0.md
## GridLedger Institutional Vocabulary — Frozen Definitions

**Effective Date:** May 8, 2026  
**Status:** FROZEN FOR ALL FUTURE ARTIFACTS  
**Governance Authority:** GridLedger IP Ltd — Risk & Verification Committee

---

## CONSTITUTIONAL PRINCIPLE

**Terminology drift is institutional risk.** Every term in this document is canonical and binding. Future artifacts (certificates, reports, standards, code) must use these exact terms with these exact meanings. No synonyms, no rephrasing, no evolution without formal amendment.

**Amendment Protocol:** Any change requires:
1. Formal amendment document (versioned v1.1, v1.2, etc.)
2. Risk committee approval
3. Retroactive review of all issued certificates for consistency
4. Public notice to all certificate holders

**Citation:** All GridLedger documents shall reference: "Terminology per CANONICAL_TERMINOLOGY_V1_0.md"

---

## SECTION 1: QUALIFICATION PATHWAYS

### 1.1 Baseline Path
**Definition:** Minimum entry criterion for portfolio inclusion. Binary qualification (present/absent) based on operational cycle existence.

**Canonical Usage:**
- "Node qualifies for Baseline Path"
- "Baseline qualification confirmed"
- "Does not qualify for Baseline Path"

**Forbidden Variations:** "Basic qualification," "Entry-level status," "Portfolio eligibility"

### 1.2 Glass Box Path
**Definition:** Constitutional proof of operational discipline through consecutive clean cycle run. Enables institutional capital instruments.

**Canonical Usage:**
- "Glass Box Certification"
- "Glass Box qualified"
- "Glass Box Path eligibility"

**Forbidden Variations:** "Box certification," "Clean cycle qualification," "Institutional grade"

### 1.3 Forensic Path
**Definition:** Extended verification for institutional lender confidence; packages deterministic outputs with honest limits.

**Canonical Usage:**
- "Forensic qualification"
- "Forensic Path eligibility"
- "Forensic report"

**Forbidden Variations:** "Detailed verification," "Lender confidence path," "Extended audit"

### 1.4 ESG Path
**Definition:** Environmental, Social, Governance verification for impact-linked financing.

**Canonical Usage:**
- "ESG qualification"
- "ESG Path eligibility"
- "ESG verification"

**Forbidden Variations:** "Sustainability path," "Impact qualification," "Green certification"

---

## SECTION 2: OPERATIONAL METRICS

### 2.1 Adherence
**Definition:** Percentage of expected revenue actually remitted. Formula: `1 - ((expected_revenue - actual_cash) / expected_revenue)`

**Canonical Usage:**
- "Adherence rate: X%"
- "Cycle adherence ≥ 90%"
- "Adherence threshold"

**Forbidden Variations:** "Compliance rate," "Remittance accuracy," "Payment fidelity"

### 2.2 Clean Run
**Definition:** Consecutive sequence of cycles with status='SEALED'/'VERIFIED', gap_breach_detected=0, and adherence ≥ 90%.

**Canonical Usage:**
- "62-cycle clean run"
- "Consecutive clean cycles"
- "Clean run window"

**Forbidden Variations:** "Good cycle sequence," "Compliant period," "Clean streak"

### 2.3 Verified Completion Rate
**Definition:** Portion of initiated cycles that reach terminal status ('SEALED' or 'VERIFIED'). Formula: `(cycles_sealed + cycles_verified) / total_cycles_initiated`

**Canonical Usage:**
- "Verified completion rate: 100%"
- "Completion rate threshold"

**Forbidden Variations:** "Success rate," "Cycle completion percentage," "Terminal status rate"

### 2.4 Variance Coefficient
**Definition:** Volatility of cycle-to-cycle variance. Formula: `STDEV(variance) / AVG(ABS(variance))`

**Canonical Usage:**
- "Variance coefficient ≤ 15%"
- "Coefficient of variance"

**Forbidden Variations:** "Volatility measure," "Variance ratio," "Stability coefficient"

### 2.5 Integrity Score Completeness
**Definition:** Percentage of cycles with recorded integrity_score. Formula: `(cycles_with_integrity_score / total_cycles) × 100`

**Canonical Usage:**
- "Integrity score completeness: X%"
- "Completeness ≥ 80%"

**Forbidden Variations:** "Integrity coverage," "Score completeness percentage," "Verification completeness"

---

## SECTION 3: CYCLE STATUS DEFINITIONS

### 3.1 SEALED
**Definition:** Cycle completed with operator remittance submitted and meter reconciliation performed. Ready for verification.

**Canonical Usage:**
- "Status: SEALED"
- "Sealed cycle"

**Forbidden Variations:** "Completed," "Submitted," "Reconciled"

### 3.2 VERIFIED
**Definition:** Cycle with cryptographic verification that remittance data has not been tampered with post-submission.

**Canonical Usage:**
- "Status: VERIFIED"
- "Verified cycle"

**Forbidden Variations:** "Confirmed," "Authenticated," "Validated"

### 3.3 FAILED
**Definition:** Cycle that did not complete successfully due to operational failure, meter malfunction, or reconciliation error.

**Canonical Usage:**
- "Status: FAILED"
- "Failed cycle"

**Forbidden Variations:** "Error," "Incomplete," "Unsuccessful"

### 3.4 INTERRUPTED
**Definition:** Cycle initiated but terminated before completion due to external factors (power outage, network failure, operator action).

**Canonical Usage:**
- "Status: INTERRUPTED"
- "Interrupted cycle"

**Forbidden Variations:** "Stopped," "Aborted," "Terminated"

### 3.5 DISPUTED
**Definition:** Cycle with remittance discrepancy requiring manual investigation. Operator and verifier disagree on meter readings or amounts.

**Canonical Usage:**
- "Status: DISPUTED"
- "Disputed cycle"

**Forbidden Variations:** "Contested," "Disagreeing," "Under review"

### 3.6 MISSING
**Definition:** Cycle record expected but not present in database. Indicates data loss or ingestion failure.

**Canonical Usage:**
- "Status: MISSING"
- "Missing cycle"

**Forbidden Variations:** "Absent," "Not found," "Lost"

---

## SECTION 4: INSTITUTIONAL CONCEPTS

### 4.1 Constitutional Event
**Definition:** Operational demonstration that establishes institutional confidence. For Glass Box: 62-cycle consecutive clean run.

**Canonical Usage:**
- "Constitutional event"
- "Proof point"

**Forbidden Variations:** "Milestone," "Achievement," "Demonstration"

### 4.2 Capital Decision Counterfactual
**Definition:** Economic value of verification measured by capital instruments it enables, not cost of producing verification.

**Canonical Usage:**
- "Capital decision counterfactual"
- "Counterfactual value"

**Forbidden Variations:** "Economic benefit," "Value proposition," "ROI of verification"

### 4.3 Honest Limits
**Definition:** Explicit boundaries on what verification confirms and does not confirm. Mandatory inclusion in forensic reports.

**Canonical Usage:**
- "Honest limits"
- "What this report DOES confirm"
- "What this report DOES NOT confirm"

**Forbidden Variations:** "Limitations," "Caveats," "Boundaries"

### 4.4 Replay Procedure
**Definition:** Deterministic SQL query that reproduces qualification decision from raw cycle data.

**Canonical Usage:**
- "Replay procedure"
- "Deterministic replay"
- "Replay query"

**Forbidden Variations:** "Verification method," "Audit process," "Reproduction procedure"

### 4.5 Qualification Engine
**Definition:** Automated system that evaluates node qualification against standards without analyst discretion.

**Canonical Usage:**
- "Qualification Engine"
- "`node.evaluate_qualification()`"

**Forbidden Variations:** "Evaluation system," "Qualification tool," "Automated checker"

---

## SECTION 5: GOVERNANCE TERMINOLOGY

### 5.1 Governing Standard
**Definition:** Reference document that defines qualification thresholds and procedures. Currently NODE_QUALIFICATION_STANDARD_V1_0.

**Canonical Usage:**
- "Governing standard"
- "Reference standard"

**Forbidden Variations:** "Guidelines," "Rules," "Framework"

### 5.2 Constitutional Precedent
**Definition:** First institutional artifact that establishes format, terminology, and procedures for all subsequent artifacts.

**Canonical Usage:**
- "Constitutional precedent"
- "Institutional precedent"

**Forbidden Variations:** "Template," "Model," "Example"

### 5.3 Invalidation Event
**Definition:** Formal record when qualification status changes from valid to invalid.

**Canonical Usage:**
- "Invalidation event"
- "Invalidation record"

**Forbidden Variations:** "Revocation," "Cancellation," "Termination"

### 5.4 Amendment Protocol
**Definition:** Formal process for changing frozen standards or terminology.

**Canonical Usage:**
- "Amendment protocol"
- "Amendment process"

**Forbidden Variations:** "Change procedure," "Update process," "Revision protocol"

---

## SECTION 6: IMPLEMENTATION TERMINOLOGY

### 6.1 Node Inventory Query
**Definition:** SQL aggregation that produces quality gate table determining monetization paths.

**Canonical Usage:**
- "Node Inventory Query"
- "Quality gate table"

**Forbidden Variations:** "Node assessment," "Inventory check," "Qualification query"

### 6.2 Cycle Table
**Definition:** Primary database table containing operational cycle records.

**Canonical Usage:**
- "Cycle table"
- "cycle table"

**Forbidden Variations:** "Cycles table," "Operational data," "Cycle records"

### 6.3 Event Log
**Definition:** Database table recording system events and state changes.

**Canonical Usage:**
- "Event log"
- "eventlog table"

**Forbidden Variations:** "Event table," "System log," "Activity log"

### 6.4 Reconciliation Record
**Definition:** Database table containing cycle reconciliation data.

**Canonical Usage:**
- "Reconciliation record"
- "reconciliationrecord table"

**Forbidden Variations:** "Reconciliation table," "Reconcile data," "Settlement record"

---

## SECTION 7: ENFORCEMENT

**This vocabulary is binding on all GridLedger artifacts, communications, and implementations.**

### 7.1 Detection of Drift
- **Automated scanning:** All documents scanned quarterly for forbidden variations
- **Manual review:** Risk committee reviews all new artifacts for terminology compliance
- **Correction protocol:** Non-compliant artifacts must be amended within 30 days

### 7.2 Consequences of Drift
- **Minor drift:** Warning issued; correction required
- **Major drift:** Artifact invalidated; re-issuance required
- **Systemic drift:** Governance review triggered; potential standard amendment

### 7.3 Version Control
- **This document:** v1.0 (frozen May 8, 2026)
- **Future versions:** v1.1, v1.2, etc. with formal amendment records
- **Citation format:** "CANONICAL_TERMINOLOGY_V1_0.md (effective May 8, 2026)"

---

**Document Version:** 1.0  
**Last Updated:** May 8, 2026  
**Next Review:** November 8, 2026 (mandatory 6-month governance review)  
**Amendment Authority:** GridLedger Risk & Verification Committee

