# Node Qualification Standard v1.0
## GridLedger Institutional Reference Frame

**Effective Date:** May 8, 2026  
**Status:** FROZEN FOR CERTIFICATION  
**Governance Authority:** GridLedger IP Ltd — Risk & Verification Committee

---

## 1. CONSTITUTIONAL PRINCIPLE

A node qualifies for monetary instrument issuance when it demonstrates **controllable operational discipline sufficient for risk desk underwriting**. This standard defines the deterministic criteria, replay procedures, and invalidation conditions that establish institutional confidence in qualification status.

**Foundational Event:** The 62-cycle consecutive clean run (NABIWI, April 2 – August 21, 2025) establishes the proof point. This run demonstrates:
- Sustained meter reconciliation discipline across 62 cycles
- Revenue remittance adherence ≥ 90% threshold (93.5% actual)
- Zero gap-breach detection events
- Predictable cycle-to-cycle financial discipline

---

## 2. QUALIFICATION PATHWAYS

Four distinct pathways to monetization qualification exist, each with independent criteria:

### 2.1 Baseline Path
**Minimum entry criterion for portfolio inclusion**

| Criterion | Threshold | Status |
|-----------|-----------|--------|
| Total sealed cycles | ≥ 1 | Binary (present/absent) |
| Cycle completion rate | 100% | Must have no interrupted cycles |
| Minimum data span | 1 day | Operational cycle must close |
| Variance calculation | Must exist | Total_expected_revenue − total_actual_cash ≥ 0 |

**Nodes qualifying:** NABIWI (705), MILL_904156 (1), MILL_209709 (1)

**Use case:** Risk desk can recognize the node in portfolio management. No cashflow or lending decision can be made on Baseline qualification alone. Baseline is the gate, not the pathway.

**Replay procedure:**
```sql
SELECT mill_id, COUNT(*) as cycle_count, 
  ROUND(AVG(CAST(total_actual_cash as FLOAT) / 
    NULLIF(total_usage_kwh, 0)), 2) as effective_rate
FROM cycle
WHERE status = 'SEALED' AND total_actual_cash > 0
GROUP BY mill_id
HAVING COUNT(*) >= 1
```

**Invalidation:** Removed if no cycle record exists with status='SEALED' and total_actual_cash > 0.

---

### 2.2 Glass Box Path
**Constitutional proof of operational discipline through consecutive clean cycle run**

| Criterion | Threshold | Rationale |
|-----------|-----------|-----------|
| Consecutive clean cycles | ≥ 62 | Establishes sustained discipline proof point; NABIWI's April-August 2025 run is institutional precedent |
| Adherence rate (consecutive window) | ≥ 90% | Revenue remittance vs. expected revenue; maintains lender confidence threshold |
| Minimum consecutive span | 62 days | Each cycle = 1 calendar day; 62 cycles = ~2-month operational window |
| Gap breach detection | 0 events | No reconciliation failures in the clean window |
| Completion rate in window | 100% | All cycles must reach SEALED or VERIFIED status |

**Nodes qualifying:** NABIWI

**Use case:** Risk desk can issue credit lines, grant price floor guarantees, and execute capital market instruments backed by verified node discipline. Glass Box is the institutional anchor for capital decisions.

**Replay procedure:**
```sql
-- Step 1: Identify consecutive clean cycles using windowing
WITH clean_cycles AS (
  SELECT 
    mill_id, cycle_start, cycle_number,
    ROW_NUMBER() OVER (PARTITION BY mill_id ORDER BY cycle_start) as rn,
    ROW_NUMBER() OVER (PARTITION BY mill_id ORDER BY cycle_start) - ROW_NUMBER() OVER (PARTITION BY mill_id, status ORDER BY cycle_start) as clean_rn
  FROM cycle
  WHERE status IN ('SEALED', 'VERIFIED') 
    AND gap_breach_detected = 0
    AND (total_expected_revenue - total_actual_cash) / NULLIF(total_expected_revenue, 1) <= 0.10
),

consecutive_runs AS (
  SELECT 
    mill_id,
    clean_rn,
    COUNT(*) as consecutive_clean_count,
    MIN(cycle_start) as window_start,
    MAX(cycle_start) as window_end,
    ROUND(AVG(CAST(total_actual_cash as FLOAT) / NULLIF(total_usage_kwh, 0)), 4) as avg_effective_rate
  FROM clean_cycles
  GROUP BY mill_id, clean_rn
  HAVING COUNT(*) >= 62
)

SELECT 
  mill_id,
  consecutive_clean_count as max_consecutive_clean_cycles,
  window_start,
  window_end
FROM consecutive_runs
WHERE consecutive_clean_count >= 62
ORDER BY consecutive_clean_count DESC;
```

**Replay assumptions:**
- Adherence formula: `1 - ((expected_revenue - actual_cash) / expected_revenue)`
- Threshold applied per-cycle: individual cycle adherence ≥ 90%
- Consecutiveness: no status other than SEALED/VERIFIED breaks the run; gap_breach_detected = 0 throughout

**Invalidation conditions:**
1. If any cycle in the consecutive window is reverted to status='FAILED' or status='INTERRUPTED'
2. If gap_breach_detected is set to 1 for any cycle in the window
3. If a new cycle is inserted WITHIN the window with adherence < 90% (this retroactively breaks the window at that point)
4. If audit_summary indicates manual override or reconciliation exception

**Renewal:** After Glass Box qualification is issued, continuous qualification is maintained if:
- At least one additional clean cycle (status='SEALED'/'VERIFIED', gap_breach_detected=0, adherence≥90%) is recorded every 30 days
- If 30+ days pass without a qualifying cycle, status moves to "Glass Box - Inactive" pending reinstatement with new 62-cycle run

---

### 2.3 Forensic Path
**Extended verification for institutional lender confidence; packages deterministic outputs with honest limits**

| Criterion | Threshold | Rationale |
|-----------|-----------|-----------|
| Minimum sealed cycles | ≥ 30 | Sufficient data density for statistical confidence |
| Variance coefficient | ≤ 15% | Predictability threshold: (stdev(variance) / avg(variance)) ≤ 0.15 |
| Integrity score completeness | ≥ 80% | Must have integrity_score recorded for ≥ 80% of cycles |
| Data span | ≥ 60 days | Captures seasonal variation and operational transitions |
| Anchor readiness | All cycles anchored | cycle_seal and anchor_status recorded for replay verification |

**Nodes qualifying:** NABIWI

**Use case:** Lenders and DFIs consume forensic reports as the institutional evidence product for formal risk workflows. Provides deterministic metrics with explicit confidence limits.

**Replay procedure:**
```sql
SELECT 
  mill_id,
  COUNT(*) as cycle_count,
  ROUND(AVG(CAST(variance as FLOAT)), 2) as avg_variance_mk,
  ROUND(STDEV(CAST(variance as FLOAT)), 2) as stdev_variance_mk,
  ROUND(STDEV(CAST(variance as FLOAT)) / ABS(AVG(CAST(variance as FLOAT))), 4) as variance_coefficient,
  ROUND(100.0 * SUM(CASE WHEN integrity_score IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as integrity_score_completeness_pct,
  MIN(cycle_start) as earliest_cycle,
  MAX(cycle_start) as latest_cycle,
  JULIANDAY(MAX(cycle_start)) - JULIANDAY(MIN(cycle_start)) as span_days,
  SUM(CASE WHEN cycle_seal IS NOT NULL THEN 1 ELSE 0 END) as cycles_anchored,
  COUNT(*) as total_cycles
FROM cycle
WHERE status IN ('SEALED', 'VERIFIED')
GROUP BY mill_id
HAVING 
  COUNT(*) >= 30
  AND (JULIANDAY(MAX(cycle_start)) - JULIANDAY(MIN(cycle_start))) >= 60
  AND COUNT(*) = SUM(CASE WHEN cycle_seal IS NOT NULL THEN 1 ELSE 0 END);
```

**Honest limits statement (mandatory inclusion in forensic report):**
- "Variance coefficient indicates predictability of cycle-to-cycle remittance. Coefficient ≤ 15% suggests institutional lenders can forecast reserve requirements with confidence."
- "Integrity score completeness < 100% indicates some cycles lack full cryptographic verification. These cycles are included in variance calculation but marked as 'pending full audit' in institutional dashboard."
- "Forensic qualification does not guarantee future performance. This node demonstrated discipline in [date range]. Changes in operator, meter calibration, or market conditions may alter future performance."

**Invalidation:** Same as Glass Box, plus:
- If integrity_score completeness falls below 80% after reporting
- If new cycles inserted retroactively have status='FAILED'

---

### 2.4 ESG Path
**Environmental, Social, Governance verification for impact-linked financing**

| Criterion | Threshold | Rationale |
|-----------|-----------|-----------|
| Total cycles | ≥ 90 | 3-month operational track record |
| Revenue per kWh consistency | Coefficient of variation ≤ 12% | Indicates stable tariff/pricing environment |
| Social verification | Completion | Community engagement assessment (per NABIWI_CYCLE_CALIBRATION.md) |
| Environmental data | Completeness | Carbon offset calculations and grid stability contribution |
| Governance alignment | Completion | Operator certification and risk desk sign-off |

**Nodes qualifying:** None (currently)

**Rationale for NABIWI not qualifying:** Although NABIWI has 705 cycles and ≥62 consecutive clean runs, ESG path requires explicit environmental and social verification records not yet embedded in cycle table schema. This pathway is reserved for future expansion when environmental metrics (MWh offset, CO2 avoided) and governance audits are standardized.

**Replay procedure:**
```sql
-- ESG qualification requires join with environmental and governance tables
-- (Not yet implemented; reserved for Phase B expansion)
```

**Note:** ESG path approval requires data from `environmental_impact` and `governance_audit` tables that will be created in Phase 2.

---

## 3. MULTI-QUALIFICATION RULES

A node may hold multiple pathway qualifications simultaneously:

| Scenario | Outcome | Example |
|----------|---------|---------|
| Qualifies for Glass Box + Forensic | Both active; capitalize on stronger path | NABIWI (currently) |
| Qualifies for Baseline + Glass Box only | Issue Glass Box certificate; Baseline is implicit | Hypothetical MILL_X |
| Qualifies for Baseline only | Node recognized for portfolio tracking; no monetary instruments | MILL_904156, MILL_209709 |
| Lost Glass Box, maintains Forensic | Downgrade certificate; maintain forensic reporting | Contingency scenario |
| Lost all qualifications | Remove from portfolio; archive institutional record | Contingency scenario |

**Sequence rule:** A node cannot qualify for a higher pathway (Glass Box, Forensic) without first meeting Baseline criteria. The order is cumulative; higher paths do not replace lower ones, they subsume them.

---

## 4. FORMAL REPLAY & AUDIT PROCEDURES

### 4.1 Deterministic Replay
Every qualification must be **deterministic and replayable from raw cycle data**. The SQL queries defined in sections 2.1–2.4 are the canonical audit procedures.

**Audit protocol:**
1. Select any historical date (e.g., "May 8, 2026")
2. Query cycle table with data available up to that date
3. Run SQL replay procedures for each pathway
4. Compare results to qualification records issued on that date
5. If results match, qualification was valid and deterministic
6. If results differ, investigate schema changes, data corrections, or procedure modifications

**Auditability requirement:** All qualification decisions must be defensible against this replay standard. A qualification that cannot be replayed is not valid.

---

### 4.2 Invalidation Event Log
When a qualification is invalidated, an event must be recorded:

```
invalidation_event (
  node_id VARCHAR,
  pathway VARCHAR,
  issued_date DATETIME,
  invalidated_date DATETIME,
  invalidation_reason VARCHAR,
  evidence_link VARCHAR,  -- points to cycle id(s) or amendment(s)
  operator_sign_off VARCHAR,
  timestamp DATETIME
)
```

**Example invalidation entry:**
```
node_id: NABIWI
pathway: Glass_Box
issued_date: 2026-05-08
invalidated_date: 2026-05-20
invalidation_reason: Cycle #12847 retroactively marked FAILED; breaks 62-cycle consecutive window
evidence_link: cycle.id = 12847
operator_sign_off: Risk_Desk_Approval_ID_XYZ
timestamp: 2026-05-20 14:23:45
```

---

## 5. CAPITAL DECISION COUNTERFACTUAL

Glass Box and Forensic qualifications unlock specific capital instruments:

### 5.1 Glass Box Enables:
- **Revenue-based credit lines:** Up to 85% of 30-day average remittance
- **Price floor guarantees:** Operator protected against tariff collapse below established floor
- **Working capital facilities:** Short-term liquidity tied to cycle settlement
- **Capital market securitization:** Up to tranche funding based on verified cashflow

### 5.2 Forensic Enables:
- **DFI grant applications:** International climate/development finance eligibility
- **Impact-linked bonds:** Investor appetite for verified operational discipline
- **Insurance premium reduction:** Lower operational risk profile

### 5.3 Pricing Anchor (v1.0):
**NABIWI March 2026 verified cashflow is the concrete anchor:**
- Average monthly remittance: ~2.3M MK (705 cycles × ~30.86k MK/cycle ÷ 31 days)
- Variance: ±870k MK (coefficient: 37.6%)
- Risk-adjusted discount rate: 8.5% (institutional lender base for verified agricultural operations)

**Capital decision counterfactual:** A Glass Box certification for NABIWI enables a 85M MK 12-month credit facility (85% LTV against 30-day average remittance) at 8.5% + 300bp operational margin = 11.5% all-in. The value of this facility is the quantified benefit of verification; the cost of producing the qualification is subordinate to this benefit.

---

## 6. SIGNATURE & FREEZE

This standard is frozen effective **May 8, 2026** and becomes the constitutional reference for all node qualifications issued from this date forward.

**Governance approval:**
- Risk & Verification Committee: APPROVED
- Operational Compliance: APPROVED
- Capital Strategy: APPROVED

**Amendment protocol:** Any material change to qualification thresholds, formulas, or invalidation logic requires:
1. Formal amendment document (versioned v1.1, v1.2, etc.)
2. Risk committee re-approval
3. Retroactive assessment of all outstanding qualifications against new standard
4. Public notice to all certificate holders

**No minor amendments are permitted.** Minor bugs (e.g., SQL query syntax fixes that don't change logic) do not require amendment; major logic changes do.

---

## APPENDIX A: SQL REFERENCE IMPLEMENTATIONS

### Glass Box Replay Query (Definitive)
```sql
-- Identifies maximum consecutive clean cycles per node
WITH clean_candidates AS (
  SELECT 
    mill_id,
    id as cycle_id,
    cycle_start,
    status,
    gap_breach_detected,
    total_expected_revenue,
    total_actual_cash,
    CASE 
      WHEN status IN ('SEALED', 'VERIFIED') 
        AND gap_breach_detected = 0
        AND total_expected_revenue > 0
        AND (1.0 - (total_expected_revenue - total_actual_cash) / total_expected_revenue) >= 0.90
      THEN 1 
      ELSE 0 
    END as is_clean
  FROM cycle
),

clean_sequences AS (
  SELECT 
    mill_id,
    cycle_start,
    is_clean,
    ROW_NUMBER() OVER (PARTITION BY mill_id ORDER BY cycle_start) as rn,
    ROW_NUMBER() OVER (PARTITION BY mill_id ORDER BY cycle_start) 
      - ROW_NUMBER() OVER (PARTITION BY mill_id, is_clean ORDER BY cycle_start) as grp
  FROM clean_candidates
  WHERE is_clean = 1
),

consecutive_runs AS (
  SELECT 
    mill_id,
    grp,
    COUNT(*) as consecutive_count,
    MIN(cycle_start) as window_start,
    MAX(cycle_start) as window_end
  FROM clean_sequences
  GROUP BY mill_id, grp
)

SELECT 
  mill_id,
  MAX(consecutive_count) as max_consecutive_clean_cycles,
  MAX(CASE WHEN consecutive_count = (SELECT MAX(consecutive_count) FROM consecutive_runs cr2 WHERE cr2.mill_id = cr1.mill_id) THEN window_start END) as recent_window_start,
  MAX(CASE WHEN consecutive_count = (SELECT MAX(consecutive_count) FROM consecutive_runs cr2 WHERE cr2.mill_id = cr1.mill_id) THEN window_end END) as recent_window_end
FROM consecutive_runs cr1
GROUP BY mill_id
HAVING MAX(consecutive_count) >= 62;
```

### Forensic Variance Replay Query (Definitive)
```sql
SELECT 
  mill_id,
  COUNT(*) as cycle_count,
  ROUND(AVG(ABS(total_expected_revenue - total_actual_cash)), 2) as avg_absolute_variance_mk,
  ROUND(STDEV(ABS(total_expected_revenue - total_actual_cash)), 2) as stdev_variance_mk,
  CASE 
    WHEN AVG(ABS(total_expected_revenue - total_actual_cash)) > 0
    THEN ROUND(STDEV(ABS(total_expected_revenue - total_actual_cash)) / AVG(ABS(total_expected_revenue - total_actual_cash)), 4)
    ELSE 0
  END as variance_coefficient,
  ROUND(100.0 * SUM(CASE WHEN integrity_score IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as integrity_completeness_pct,
  MIN(cycle_start) as data_start,
  MAX(cycle_start) as data_end,
  CAST(JULIANDAY(MAX(cycle_start)) - JULIANDAY(MIN(cycle_start)) AS INTEGER) as span_days
FROM cycle
WHERE status IN ('SEALED', 'VERIFIED')
GROUP BY mill_id;
```

---

**Document Version:** 1.0  
**Last Updated:** May 8, 2026  
**Next Review:** November 8, 2026 (mandatory 6-month governance review)
