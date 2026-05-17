# Standardized Forensic Report Format v1.0
## GridLedger Institutional Evidence Product for Lender/DFI Risk Workflows

**Template Version:** 1.0  
**Effective Date:** May 8, 2026  
**Derived From:** T.G. Msonda Precedent (Agricultural Cooperative Verification Protocol, 2023)  
**Governing Authority:** GridLedger Risk & Verification Committee

---

## EXECUTIVE SUMMARY

**[TO BE COMPLETED PER NODE]**

This forensic report packages deterministic operational metrics from verified cashflow data and provides explicit confidence limits. It is designed for consumption by institutional lenders and development finance institutions (DFIs) in formal credit risk assessment workflows.

- **Node:** [MILL_ID]
- **Report Date:** [DATE]
- **Qualification Pathway:** Forensic
- **Data Span:** [START_DATE] to [END_DATE]
- **Cycle Count:** [N] sealed/verified cycles
- **Recommendation:** [QUALIFIED / CONDITIONAL / REFER_TO_RISK_DESK]

---

## SECTION 1: DETERMINISTIC OPERATIONAL PROFILE

### 1.1 Cycle Count & Completion Rate

| Metric | Value | Interpretation |
|--------|-------|-----------------|
| Total sealed cycles | [N] | All cycles must be status='SEALED' or 'VERIFIED' to qualify for forensic review |
| Total cycles reviewed | [N] | Must be ≥30 per NODE_QUALIFICATION_STANDARD_V1_0 Section 2.3 |
| Completion rate (%) | [X]% | Portion of initiated cycles that reached terminal status; <100% suggests operational interruptions |
| Data collection period | [D] days | Minimum 60 days required; longer spans provide confidence in variance modeling |

**Honest limit:** Completion rate is a *historical* measure. Future cycle interruption rates cannot be predicted from past performance. If operator changes, meter is recalibrated, or tariff structure shifts, completion rate may not persist.

---

### 1.2 Cashflow Stability Profile

| Metric | Value | Unit | Interpretation |
|--------|-------|------|-----------------|
| Average remittance per cycle | [X] | MK | `SUM(total_actual_cash) / cycle_count` |
| Standard deviation of remittance | [σ] | MK | Absolute variability; larger σ indicates greater month-to-month swings |
| Coefficient of variation | [CV%] | % | `(σ / mean) × 100`; threshold ≤15% for forensic qualification |
| Minimum cycle remittance | [MIN] | MK | Lowest single-cycle revenue observed; lender stress-test floor |
| Maximum cycle remittance | [MAX] | MK | Highest single-cycle revenue observed; lender upside scenario |
| 25th percentile remittance | [Q1] | MK | Conservative scenario; 75% of cycles exceed this amount |
| Median remittance | [Q2] | MK | 50th percentile; middle of distribution |
| 75th percentile remittance | [Q3] | MK | Optimistic scenario; 75% of cycles fall below this amount |

**Cashflow stability formula:**
```
Variance_coefficient = STDEV(total_actual_cash) / AVG(total_actual_cash)
```

**Lender interpretation guide:**
- **CV ≤ 10%:** Highly stable; lender can model with confidence; supports 90%+ LTV facilities
- **CV 10–15%:** Stable; acceptable for institutional lending; supports 75–85% LTV facilities
- **CV > 15%:** Variable; requires enhanced monitoring; limits to 50–65% LTV facilities

**Honest limit:** Coefficient of variation is calculated from *historical* cycles. Seasonal changes (e.g., dry season affecting agricultural output, tariff changes, operator turnover) can materially alter future remittance distributions. This metric should not be extrapolated beyond 24 months without re-verification.

---

### 1.3 Expected Revenue vs. Actual Remittance (Variance Profile)

| Metric | Value | Unit | Interpretation |
|--------|-------|------|-----------------|
| Average expected revenue per cycle | [E] | MK | `AVG(total_expected_revenue)` = expected amount + expected late fees |
| Average actual remittance per cycle | [A] | MK | `AVG(total_actual_cash)` = what operator actually submitted |
| Average variance (shortfall) | [E−A] | MK | Difference between expected and actual; negative = operator submits more than expected |
| Variance as % of expected | [(E−A)/E]% | % | Standardized variance metric; used in Glass Box adherence calculation |
| Minimum cycle variance | [MIN_V] | MK | Best-case scenario; smallest shortfall or largest overpayment |
| Maximum cycle variance | [MAX_V] | MK | Worst-case scenario; largest shortfall observed |
| Variance coefficient (stdev/mean) | [V_CV%] | % | Volatility of variance; lower = more predictable shortfalls |

**Forensic qualification criterion:**
```
IF variance_coefficient ≤ 15% THEN FORENSIC_QUALIFIED = TRUE
IF variance_coefficient > 15% THEN FORENSIC_QUALIFIED = FALSE
```

**Interpretation for risk desk:**
- Variance ≤ 10%: Operator reliably underpays by predictable amount (e.g., consistent field deductions); lender can model precisely
- Variance 10–20%: Operator payment behavior varies; lender must model range scenarios
- Variance > 20%: Operator payment behavior is erratic; insufficient predictability for institutional lending without additional collateral

**Honest limit:** Variance patterns established in this cycle sample may not persist if:
1. Operator incentive structure changes (e.g., new bonus/penalty system)
2. Market conditions shift (tariff changes, price pressure)
3. Meter calibration drifts or is recalibrated
4. External shocks (weather, supply chain) alter operational capacity

---

### 1.4 Integrity Score Completeness

| Metric | Value | Interpretation |
|--------|-------|-----------------|
| Cycles with integrity_score recorded | [N_INTEGRITY] | Cryptographic verification that cycle data has not been tampered with post-submission |
| Total cycles reviewed | [N_TOTAL] | Denominator for completeness calculation |
| Integrity score completeness (%) | [COMP%] | `(N_INTEGRITY / N_TOTAL) × 100`; must be ≥80% for forensic qualification |
| Cycles pending full audit | [PENDING] | Cycles recorded but awaiting cryptographic anchor verification |

**Forensic qualification criterion:**
```
IF completeness_pct ≥ 80% THEN FORENSIC_QUALIFIED = TRUE (on this dimension)
IF completeness_pct < 80% THEN ESCALATE_TO_RISK_DESK
```

**Interpretation:** Integrity score represents cryptographic proof that a cycle record has not been altered after operator submission. Gaps (cycles without integrity scores) indicate:
- Pending anchor verification (normal; expected to resolve within 14 days)
- Data reconciliation in progress (temporary state)
- Legacy data migrated before anchor procedures were operational (acceptable if ≤20%)

**Honest limit:** Integrity completeness is a *process* metric, not a *performance* metric. It indicates data quality assurance, not operational discipline. A node with 100% integrity scores but high variance remains operationally unpredictable.

---

## SECTION 2: CAPITAL DECISION SCENARIOS

### 2.1 Conservative Scenario (25th Percentile Remittance)

**Assumption:** Operator remits at 25th percentile level consistently

| Instrument | Facility Size | LTV | Tenor | Implied Interest Rate |
|------------|---------------|-----|-------|----------------------|
| Revenue-based credit line | [Q1 × 85%] | 85% | 12-month rolling | Base + 400bp |
| Price floor guarantee | [Q1 × 1.0] | 100% | 12-month | Base + 300bp + premium |
| Working capital facility | [Q1 × 0.5] | 50% | 60-day revolving | Base + 250bp |

**Lender decision rule:** If conservative scenario enables viable instrument structures, recommend approval. Conservative pricing applies.

---

### 2.2 Base Case Scenario (Median Remittance)

**Assumption:** Operator remits at median level consistently

| Instrument | Facility Size | LTV | Tenor | Implied Interest Rate |
|------------|---------------|-----|-------|----------------------|
| Revenue-based credit line | [Q2 × 85%] | 85% | 12-month rolling | Base + 300bp |
| Price floor guarantee | [Q2 × 1.0] | 100% | 12-month | Base + 200bp + premium |
| Working capital facility | [Q2 × 0.6] | 60% | 60-day revolving | Base + 150bp |

**Lender decision rule:** Base case supports institutional-grade facility structures. This is the standard pricing scenario.

---

### 2.3 Optimistic Scenario (75th Percentile Remittance)

**Assumption:** Operator remits at 75th percentile level consistently

| Instrument | Facility Size | LTV | Tenor | Implied Interest Rate |
|------------|---------------|-----|-------|----------------------|
| Revenue-based credit line | [Q3 × 90%] | 90% | 12-month rolling | Base + 200bp |
| Price floor guarantee | [Q3 × 1.05] | 105% | 12-month | Base + 150bp + premium |
| Working capital facility | [Q3 × 0.75] | 75% | 60-day revolving | Base + 100bp |

**Lender decision rule:** If operator consistency supports optimistic scenario, recommend approval with enhanced terms.

---

## SECTION 3: HONEST LIMITS & EXPLICIT CAVEATS

### 3.1 What This Report DOES Confirm

✓ Operator submitted [N] sequential cycle records with ≥[CV]% consistency  
✓ Cycle-to-cycle remittance variance follows distribution [parameters]  
✓ Integrity score completeness is [COMP%]; data assurance level is [HIGH/MEDIUM/LOW]  
✓ No gap-breach events detected in review period  
✓ Completion rate of [X]% indicates operational discipline in cycle closure  

---

### 3.2 What This Report DOES NOT Confirm

✗ Future cashflow performance (historical does not guarantee future)  
✗ Operator creditworthiness (this report evaluates operational discipline, not credit character)  
✗ Absence of prior defaults or payment failures (forensic report is process-focused, not history-focused)  
✗ Market conditions will remain constant (tariffs, pricing, demand may shift)  
✗ Meter calibration is accurate (forensic report assumes meter readings are correct; does not validate meter quality)  
✗ Operator has not committed off-books revenue leakage (forensic report evaluates submitted records; does not audit for shadow cash)  

---

### 3.3 Boundary Conditions & Risk Triggers

| Condition | Status | Action |
|-----------|--------|--------|
| Coefficient of variation exceeds 20% | RISK | Escalate to credit committee; consider enhanced monitoring requirements |
| Integrity completeness < 75% | RISK | Delay instrument issuance; await 14-day anchor reconciliation |
| Operator changes in past 30 days | RISK | Require new baseline period (30+ cycles) before facility issuance |
| Meter maintenance/recalibration in past 60 days | CAUTION | Request pre- vs. post-calibration analysis; assess for systematic drift |
| Tariff increase > 20% in past period | CAUTION | Model new expected revenue baseline; historical variance may not apply |
| External shock event documented (weather, supply disruption) | CAUTION | Segment analysis into pre/post-shock periods; model persistent impact |

---

### 3.4 T.G. Msonda Precedent Compliance

This report follows the **Msonda Institutional Verification Protocol** (2023) in the following dimensions:

1. **Determinism:** All metrics are computed via SQL queries against immutable cycle records. No subjective judgment or manual override.
2. **Honest limits:** Explicit caveats section identifies what the data does and does not confirm.
3. **DFI-ready format:** Package is structured for rapid integration into lender credit workflow systems.
4. **Scenario modeling:** Conservative/base/optimistic scenarios enable lender stress-testing.
5. **Audit trail:** Every metric references the underlying SQL query; auditor can replay verification.

**Msonda citation in risk documentation:** "Forensic qualification confirms operational discipline per GridLedger Forensic Format (derived from Msonda Protocol); does not constitute credit recommendation without additional due diligence."

---

## SECTION 4: FORMAL RECOMMENDATION

### 4.1 Risk Desk Recommendation

**Based on deterministic forensic analysis:**

- **Qualification Status:** [QUALIFIED / CONDITIONAL / REFER_TO_COMMITTEE]

**Rationale:**
```
IF variance_coefficient ≤ 15% AND integrity_completeness ≥ 80% AND completion_rate = 100%
THEN recommendation = FORENSIC_QUALIFIED
```

**Conditional qualifications (if applicable):**
```
IF variance_coefficient ≤ 18% AND integrity_completeness ≥ 75%
THEN recommendation = QUALIFIED_WITH_ENHANCED_MONITORING
```

### 4.2 Lender Engagement Path

- **For DFI submissions:** Attach this report + NODE_QUALIFICATION_STANDARD_V1_0 as institutional evidence of operational discipline
- **For commercial lenders:** Use Section 2 (Capital Decision Scenarios) for facility structuring and pricing
- **For impact investors:** Use Section 3 (Honest Limits) to establish confidence boundaries for ESG-linked instrument design

---

## SECTION 5: TEMPLATE COMPLETION CHECKLIST

**For analyst completing this report:**

- [ ] Query cycle table for [MILL_ID] with date range [START] to [END]
- [ ] Run SQL: Forensic Variance Replay Query (NODE_QUALIFICATION_STANDARD_V1_0 Appendix A)
- [ ] Calculate: variance_coefficient = STDEV / MEAN (must be ≤15% or escalate to CONDITIONAL)
- [ ] Calculate: integrity_completeness_pct = cycles_with_integrity_score / total_cycles (must be ≥80%)
- [ ] Validate: No gap_breach_detected = 1 events in period
- [ ] Complete Section 1 metrics table with actual values
- [ ] Complete Section 2 scenarios using 25th/50th/75th percentile values
- [ ] Review Section 3 honest limits; add node-specific caveats if applicable
- [ ] Get risk desk sign-off on recommendation (Section 4.1)
- [ ] Export to PDF for institutional archive
- [ ] File in gridledger.archive/forensic_reports/[MILL_ID]_[DATE].pdf

---

## APPENDIX A: SQL QUERIES FOR FORENSIC METRICS

All metrics in this report are derived from deterministic SQL queries. Auditor can replicate any metric by running the corresponding query against the cycle table as of report date.

### Query 1: Cashflow Stability Profile
```sql
SELECT 
  mill_id,
  COUNT(*) as cycle_count,
  ROUND(AVG(CAST(total_actual_cash as FLOAT)), 2) as avg_remittance_mk,
  ROUND(STDEV(CAST(total_actual_cash as FLOAT)), 2) as stdev_remittance_mk,
  CASE WHEN AVG(CAST(total_actual_cash as FLOAT)) > 0
    THEN ROUND(100.0 * STDEV(CAST(total_actual_cash as FLOAT)) / AVG(CAST(total_actual_cash as FLOAT)), 2)
    ELSE 0
  END as coefficient_of_variation_pct,
  ROUND(MIN(CAST(total_actual_cash as FLOAT)), 2) as min_remittance_mk,
  ROUND(MAX(CAST(total_actual_cash as FLOAT)), 2) as max_remittance_mk,
  ROUND((
    SELECT CAST(total_actual_cash as FLOAT) 
    FROM cycle 
    WHERE mill_id = c.mill_id AND status IN ('SEALED', 'VERIFIED')
    ORDER BY total_actual_cash
    LIMIT 1 OFFSET (COUNT(*) / 4)
  ), 2) as q1_remittance_mk,
  ROUND((
    SELECT CAST(total_actual_cash as FLOAT) 
    FROM cycle 
    WHERE mill_id = c.mill_id AND status IN ('SEALED', 'VERIFIED')
    ORDER BY total_actual_cash
    LIMIT 1 OFFSET (COUNT(*) / 2)
  ), 2) as median_remittance_mk,
  ROUND((
    SELECT CAST(total_actual_cash as FLOAT) 
    FROM cycle 
    WHERE mill_id = c.mill_id AND status IN ('SEALED', 'VERIFIED')
    ORDER BY total_actual_cash
    LIMIT 1 OFFSET (COUNT(*) * 3 / 4)
  ), 2) as q3_remittance_mk
FROM cycle c
WHERE status IN ('SEALED', 'VERIFIED')
GROUP BY mill_id;
```

### Query 2: Variance Profile
```sql
SELECT 
  mill_id,
  COUNT(*) as cycle_count,
  ROUND(AVG(CAST(total_expected_revenue as FLOAT)), 2) as avg_expected_revenue_mk,
  ROUND(AVG(CAST(total_actual_cash as FLOAT)), 2) as avg_actual_remittance_mk,
  ROUND(AVG(CAST(total_expected_revenue - total_actual_cash as FLOAT)), 2) as avg_variance_mk,
  CASE WHEN AVG(CAST(total_expected_revenue as FLOAT)) > 0
    THEN ROUND(100.0 * AVG(CAST(total_expected_revenue - total_actual_cash as FLOAT)) / AVG(CAST(total_expected_revenue as FLOAT)), 2)
    ELSE 0
  END as avg_variance_pct_of_expected,
  ROUND(MIN(CAST(total_expected_revenue - total_actual_cash as FLOAT)), 2) as min_variance_mk,
  ROUND(MAX(CAST(total_expected_revenue - total_actual_cash as FLOAT)), 2) as max_variance_mk,
  ROUND(STDEV(CAST(total_expected_revenue - total_actual_cash as FLOAT)), 2) as stdev_variance_mk,
  CASE WHEN AVG(ABS(CAST(total_expected_revenue - total_actual_cash as FLOAT))) > 0
    THEN ROUND(100.0 * STDEV(CAST(total_expected_revenue - total_actual_cash as FLOAT)) / AVG(ABS(CAST(total_expected_revenue - total_actual_cash as FLOAT))), 2)
    ELSE 0
  END as variance_coefficient_pct
FROM cycle
WHERE status IN ('SEALED', 'VERIFIED')
GROUP BY mill_id;
```

### Query 3: Integrity Score Completeness
```sql
SELECT 
  mill_id,
  COUNT(*) as total_cycles,
  SUM(CASE WHEN integrity_score IS NOT NULL THEN 1 ELSE 0 END) as cycles_with_integrity_score,
  ROUND(100.0 * SUM(CASE WHEN integrity_score IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as integrity_completeness_pct,
  SUM(CASE WHEN cycle_seal IS NULL THEN 1 ELSE 0 END) as cycles_pending_anchor_verification
FROM cycle
WHERE status IN ('SEALED', 'VERIFIED')
GROUP BY mill_id;
```

---

**Report Template Version:** 1.0  
**Last Updated:** May 8, 2026  
**Compliance Authority:** GridLedger Risk & Verification Committee + T.G. Msonda Protocol Reference  
**For Use By:** Institutional Lenders, DFIs, Capital Markets Participants

