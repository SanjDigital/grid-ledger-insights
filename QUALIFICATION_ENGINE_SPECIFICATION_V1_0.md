# QUALIFICATION_ENGINE_SPECIFICATION_V1_0.md
## GridLedger Qualification Engine — Automated Node Evaluation

**Effective Date:** May 8, 2026  
**Status:** FROZEN FOR IMPLEMENTATION  
**Governing Authority:** GridLedger IP Ltd — Risk & Verification Committee

---

## CONSTITUTIONAL PRINCIPLE

**Qualification must be deterministic and replayable.** The Qualification Engine automates `node.evaluate_qualification()` to produce eligibility states, reasons, and replay references without analyst discretion. This transitions from Phase A (manual classification) to Phase B (automated institutional consumption).

**Core Function:** `node.evaluate_qualification(node_id, as_of_date) → QualificationResult`

**Governance:** Engine behavior is frozen in this specification. Code implementation must match specification exactly.

---

## SECTION 1: ENGINE INTERFACE

### 1.1 Function Signature
```python
def evaluate_qualification(node_id: str, as_of_date: datetime) → QualificationResult:
    """
    Evaluate node qualification against NODE_QUALIFICATION_STANDARD_V1_0
    
    Args:
        node_id: Mill identifier (e.g., 'NABIWI')
        as_of_date: Evaluation date (data available up to this date)
    
    Returns:
        QualificationResult object with eligibility states and evidence
    """
```

### 1.2 QualificationResult Structure
```python
@dataclass
class QualificationResult:
    node_id: str
    evaluation_timestamp: datetime
    as_of_date: datetime
    
    # Eligibility states (True/False)
    baseline_eligible: bool
    glass_box_eligible: bool
    forensic_eligible: bool
    esg_eligible: bool  # Reserved for Phase B
    
    # Evidence for each pathway
    baseline_evidence: PathwayEvidence
    glass_box_evidence: PathwayEvidence
    forensic_evidence: PathwayEvidence
    esg_evidence: PathwayEvidence
    
    # Replay references
    replay_queries: Dict[str, str]  # pathway → SQL query hash
    data_snapshot_hash: str  # SHA-256 of cycle table state
```

### 1.3 PathwayEvidence Structure
```python
@dataclass
class PathwayEvidence:
    eligible: bool
    reason: str  # Human-readable explanation
    metrics: Dict[str, Any]  # Calculated values
    threshold_checks: Dict[str, bool]  # threshold → pass/fail
    disqualifying_factors: List[str]  # If ineligible, why
    replay_query: str  # SQL to reproduce this evaluation
```

---

## SECTION 2: BASELINE PATHWAY EVALUATION

### 2.1 Eligibility Criteria
**From NODE_QUALIFICATION_STANDARD_V1_0 Section 2.1**

| Criterion | Threshold | Evaluation Logic |
|-----------|-----------|------------------|
| Total sealed cycles | ≥ 1 | `COUNT(*) >= 1 WHERE status IN ('SEALED', 'VERIFIED')` |
| Cycle completion rate | 100% | `COUNT(*) = COUNT(*) WHERE status NOT IN ('INTERRUPTED')` |
| Minimum data span | 1 day | `MAX(cycle_end) - MIN(cycle_start) >= 1` |
| Variance calculation | Must exist | `COUNT(variance IS NOT NULL) = COUNT(*)` |

### 2.2 Evaluation Algorithm
```python
def evaluate_baseline(node_id, as_of_date):
    # Query cycle table up to as_of_date
    cycles = query_cycles(node_id, as_of_date)
    
    if len(cycles) == 0:
        return PathwayEvidence(
            eligible=False,
            reason="No cycle records found",
            metrics={},
            threshold_checks={},
            disqualifying_factors=["No operational data"],
            replay_query=BASELINE_REPLAY_QUERY
        )
    
    # Check thresholds
    total_cycles = len(cycles)
    sealed_cycles = len([c for c in cycles if c.status in ['SEALED', 'VERIFIED']])
    interrupted_cycles = len([c for c in cycles if c.status == 'INTERRUPTED'])
    completion_rate = (total_cycles - interrupted_cycles) / total_cycles if total_cycles > 0 else 0
    
    # Data span
    if cycles:
        start_dates = [c.cycle_start for c in cycles]
        end_dates = [c.cycle_end for c in cycles]
        data_span_days = (max(end_dates) - min(start_dates)).days
    else:
        data_span_days = 0
    
    # Variance existence
    variance_exists = all(c.variance is not None for c in cycles)
    
    # Threshold checks
    threshold_checks = {
        'total_sealed_cycles >= 1': sealed_cycles >= 1,
        'completion_rate == 100%': completion_rate == 1.0,
        'data_span >= 1 day': data_span_days >= 1,
        'variance_calculated': variance_exists
    }
    
    eligible = all(threshold_checks.values())
    
    metrics = {
        'total_cycles': total_cycles,
        'sealed_cycles': sealed_cycles,
        'completion_rate_pct': completion_rate * 100,
        'data_span_days': data_span_days,
        'variance_exists': variance_exists
    }
    
    disqualifying_factors = [
        f"{k}: FAILED" for k, v in threshold_checks.items() if not v
    ]
    
    return PathwayEvidence(
        eligible=eligible,
        reason="Meets all Baseline criteria" if eligible else f"Failed {len(disqualifying_factors)} criteria",
        metrics=metrics,
        threshold_checks=threshold_checks,
        disqualifying_factors=disqualifying_factors,
        replay_query=BASELINE_REPLAY_QUERY
    )
```

### 2.3 Replay Query
```sql
-- BASELINE_REPLAY_QUERY
SELECT 
  mill_id,
  COUNT(*) as total_cycles,
  SUM(CASE WHEN status IN ('SEALED', 'VERIFIED') THEN 1 ELSE 0 END) as sealed_cycles,
  ROUND(100.0 * (COUNT(*) - SUM(CASE WHEN status = 'INTERRUPTED' THEN 1 ELSE 0 END)) / COUNT(*), 1) as completion_rate_pct,
  CAST(JULIANDAY(MAX(cycle_end)) - JULIANDAY(MIN(cycle_start)) AS INTEGER) as data_span_days,
  SUM(CASE WHEN variance IS NOT NULL THEN 1 ELSE 0 END) = COUNT(*) as variance_exists
FROM cycle
WHERE mill_id = ?
  AND cycle_start <= ?
GROUP BY mill_id;
```

---

## SECTION 3: GLASS BOX PATHWAY EVALUATION

### 3.1 Eligibility Criteria
**From NODE_QUALIFICATION_STANDARD_V1_0 Section 2.2**

| Criterion | Threshold | Evaluation Logic |
|-----------|-----------|------------------|
| Consecutive clean cycles | ≥ 62 | Window with ≥62 consecutive cycles meeting all criteria |
| Adherence rate (window) | ≥ 90% | Average adherence in qualifying window |
| Gap breach detection | 0 events | No gap_breach_detected = 1 in window |
| Completion rate in window | 100% | All cycles SEALED/VERIFIED |

### 3.2 Evaluation Algorithm
```python
def evaluate_glass_box(node_id, as_of_date):
    # Find maximum consecutive clean run
    max_run = find_max_consecutive_clean_run(node_id, as_of_date)
    
    if max_run['consecutive_count'] < 62:
        return PathwayEvidence(
            eligible=False,
            reason=f"Maximum consecutive clean cycles: {max_run['consecutive_count']} (requires ≥62)",
            metrics=max_run,
            threshold_checks={'consecutive_clean_cycles >= 62': False},
            disqualifying_factors=["Insufficient consecutive clean cycles"],
            replay_query=GLASS_BOX_REPLAY_QUERY
        )
    
    # Check window criteria
    window_cycles = get_cycles_in_window(node_id, max_run['window_start'], max_run['window_end'])
    
    adherence_rates = []
    gap_breaches = 0
    completion_rate = 0
    
    for cycle in window_cycles:
        if cycle.expected_revenue and cycle.expected_revenue > 0:
            adherence = 1.0 - (cycle.expected_revenue - cycle.total_actual_cash) / cycle.expected_revenue
            adherence_rates.append(adherence)
        
        if cycle.gap_breach_detected:
            gap_breaches += 1
        
        if cycle.status in ['SEALED', 'VERIFIED']:
            completion_rate += 1
    
    avg_adherence = sum(adherence_rates) / len(adherence_rates) if adherence_rates else 0
    completion_rate_pct = (completion_rate / len(window_cycles)) * 100 if window_cycles else 0
    
    threshold_checks = {
        'consecutive_clean_cycles >= 62': max_run['consecutive_count'] >= 62,
        'avg_adherence >= 90%': avg_adherence >= 0.90,
        'gap_breaches == 0': gap_breaches == 0,
        'completion_rate == 100%': completion_rate_pct == 100.0
    }
    
    eligible = all(threshold_checks.values())
    
    metrics = {
        'max_consecutive_clean_cycles': max_run['consecutive_count'],
        'window_start': max_run['window_start'],
        'window_end': max_run['window_end'],
        'avg_adherence_pct': avg_adherence * 100,
        'gap_breaches': gap_breaches,
        'completion_rate_pct': completion_rate_pct
    }
    
    disqualifying_factors = [
        f"{k}: FAILED" for k, v in threshold_checks.items() if not v
    ]
    
    return PathwayEvidence(
        eligible=eligible,
        reason="Qualifies for Glass Box certification" if eligible else f"Failed {len(disqualifying_factors)} criteria",
        metrics=metrics,
        threshold_checks=threshold_checks,
        disqualifying_factors=disqualifying_factors,
        replay_query=GLASS_BOX_REPLAY_QUERY
    )
```

### 3.3 Replay Query
```sql
-- GLASS_BOX_REPLAY_QUERY (from NODE_QUALIFICATION_STANDARD_V1_0 Appendix A)
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
  WHERE mill_id = ?
    AND cycle_start <= ?
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
WHERE mill_id = ?
GROUP BY mill_id;
```

---

## SECTION 4: FORENSIC PATHWAY EVALUATION

### 4.1 Eligibility Criteria
**From NODE_QUALIFICATION_STANDARD_V1_0 Section 2.3**

| Criterion | Threshold | Evaluation Logic |
|-----------|-----------|------------------|
| Minimum sealed cycles | ≥ 30 | `COUNT(*) >= 30 WHERE status IN ('SEALED', 'VERIFIED')` |
| Variance coefficient | ≤ 15% | `STDEV(variance) / AVG(ABS(variance)) <= 0.15` |
| Integrity score completeness | ≥ 80% | `(cycles_with_integrity_score / total_cycles) >= 0.80` |
| Data span | ≥ 60 days | `MAX(cycle_end) - MIN(cycle_start) >= 60` |
| Anchor readiness | All cycles anchored | `COUNT(cycle_seal IS NOT NULL) = COUNT(*)` |

### 4.2 Evaluation Algorithm
```python
def evaluate_forensic(node_id, as_of_date):
    cycles = query_cycles(node_id, as_of_date)
    sealed_cycles = [c for c in cycles if c.status in ['SEALED', 'VERIFIED']]
    
    if len(sealed_cycles) < 30:
        return PathwayEvidence(
            eligible=False,
            reason=f"Only {len(sealed_cycles)} sealed cycles (requires ≥30)",
            metrics={'sealed_cycles': len(sealed_cycles)},
            threshold_checks={'sealed_cycles >= 30': False},
            disqualifying_factors=["Insufficient sealed cycles"],
            replay_query=FORENSIC_REPLAY_QUERY
        )
    
    # Data span
    if sealed_cycles:
        data_span_days = (max(c.cycle_end for c in sealed_cycles) - min(c.cycle_start for c in sealed_cycles)).days
    else:
        data_span_days = 0
    
    # Variance coefficient
    variances = [abs(c.variance) for c in sealed_cycles if c.variance is not None]
    if variances:
        avg_variance = sum(variances) / len(variances)
        stdev_variance = (sum((v - avg_variance) ** 2 for v in variances) / len(variances)) ** 0.5
        variance_coefficient = stdev_variance / avg_variance if avg_variance > 0 else 0
    else:
        variance_coefficient = 0
    
    # Integrity completeness
    integrity_scores = [c for c in sealed_cycles if c.integrity_score is not None]
    integrity_completeness = len(integrity_scores) / len(sealed_cycles) if sealed_cycles else 0
    
    # Anchor readiness
    anchored_cycles = [c for c in sealed_cycles if c.cycle_seal is not None]
    anchor_readiness = len(anchored_cycles) == len(sealed_cycles)
    
    threshold_checks = {
        'sealed_cycles >= 30': len(sealed_cycles) >= 30,
        'data_span >= 60 days': data_span_days >= 60,
        'variance_coefficient <= 15%': variance_coefficient <= 0.15,
        'integrity_completeness >= 80%': integrity_completeness >= 0.80,
        'anchor_readiness == 100%': anchor_readiness
    }
    
    eligible = all(threshold_checks.values())
    
    metrics = {
        'sealed_cycles': len(sealed_cycles),
        'data_span_days': data_span_days,
        'variance_coefficient_pct': variance_coefficient * 100,
        'integrity_completeness_pct': integrity_completeness * 100,
        'anchor_readiness_pct': (len(anchored_cycles) / len(sealed_cycles) * 100) if sealed_cycles else 0
    }
    
    disqualifying_factors = [
        f"{k}: FAILED" for k, v in threshold_checks.items() if not v
    ]
    
    return PathwayEvidence(
        eligible=eligible,
        reason="Qualifies for Forensic reporting" if eligible else f"Failed {len(disqualifying_factors)} criteria",
        metrics=metrics,
        threshold_checks=threshold_checks,
        disqualifying_factors=disqualifying_factors,
        replay_query=FORENSIC_REPLAY_QUERY
    )
```

### 4.3 Replay Query
```sql
-- FORENSIC_REPLAY_QUERY (from NODE_QUALIFICATION_STANDARD_V1_0 Appendix A)
SELECT 
  mill_id,
  COUNT(*) as cycle_count,
  ROUND(STDEV(ABS(total_expected_revenue - total_actual_cash)), 2) as stdev_abs_variance,
  ROUND(AVG(ABS(total_expected_revenue - total_actual_cash)), 2) as avg_abs_variance,
  CASE WHEN AVG(ABS(total_expected_revenue - total_actual_cash)) > 0
    THEN ROUND(100.0 * STDEV(ABS(total_expected_revenue - total_actual_cash)) / AVG(ABS(total_expected_revenue - total_actual_cash)), 2)
    ELSE 0
  END as variance_coefficient_pct,
  ROUND(100.0 * SUM(CASE WHEN integrity_score IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as integrity_completeness_pct,
  MIN(cycle_start) as data_start,
  MAX(cycle_start) as data_end,
  CAST(JULIANDAY(MAX(cycle_start)) - JULIANDAY(MIN(cycle_start)) AS INTEGER) as span_days,
  SUM(CASE WHEN cycle_seal IS NOT NULL THEN 1 ELSE 0 END) = COUNT(*) as anchor_readiness
FROM cycle
WHERE status IN ('SEALED', 'VERIFIED')
  AND mill_id = ?
  AND cycle_start <= ?
GROUP BY mill_id;
```

---

## SECTION 5: ENGINE IMPLEMENTATION REQUIREMENTS

### 5.1 Code Structure
```
qualification_engine/
├── __init__.py
├── engine.py              # Main evaluation logic
├── models.py              # QualificationResult, PathwayEvidence dataclasses
├── queries.py             # SQL query constants
├── database.py            # Cycle table access layer
└── tests/                 # Comprehensive test suite
```

### 5.2 Testing Requirements
- **Unit tests:** Each pathway evaluation function
- **Integration tests:** Full engine against test databases
- **Replay verification:** Engine results must match manual SQL queries
- **Regression tests:** Historical qualification decisions must replay correctly

### 5.3 Performance Requirements
- **Evaluation time:** < 5 seconds per node
- **Memory usage:** < 100MB per evaluation
- **Concurrent evaluations:** Support 100+ simultaneous evaluations

### 5.4 Audit Trail
Every evaluation must record:
- Input parameters (node_id, as_of_date)
- Execution timestamp
- Data snapshot hash
- Result object (full serialization)
- Replay query hashes

---

## SECTION 6: GOVERNANCE & VERSION CONTROL

### 6.1 Version Control
- **Specification:** v1.0 (frozen May 8, 2026)
- **Implementation:** Must implement specification exactly
- **Updates:** Require specification amendment first, then implementation update

### 6.2 Monitoring & Alerting
- **Evaluation failures:** Alert if >5% of evaluations fail
- **Performance degradation:** Alert if evaluation time >10 seconds
- **Result consistency:** Daily replay verification of recent evaluations

### 6.3 Disaster Recovery
- **Engine failure:** Manual evaluation fallback procedure
- **Data corruption:** Ability to replay from backup data snapshots
- **Result invalidation:** Automatic re-evaluation if underlying data changes

---

## APPENDIX A: IMPLEMENTATION PSEUDO-CODE

```python
# Main evaluation function
def evaluate_qualification(node_id: str, as_of_date: datetime) -> QualificationResult:
    # Validate inputs
    if not node_id or not as_of_date:
        raise ValueError("node_id and as_of_date required")
    
    # Get data snapshot hash
    data_snapshot_hash = get_cycle_table_hash(node_id, as_of_date)
    
    # Evaluate each pathway
    baseline = evaluate_baseline(node_id, as_of_date)
    glass_box = evaluate_glass_box(node_id, as_of_date)
    forensic = evaluate_forensic(node_id, as_of_date)
    esg = PathwayEvidence(eligible=False, reason="ESG pathway not yet implemented", ...)
    
    # Build result
    result = QualificationResult(
        node_id=node_id,
        evaluation_timestamp=datetime.now(),
        as_of_date=as_of_date,
        baseline_eligible=baseline.eligible,
        glass_box_eligible=glass_box.eligible,
        forensic_eligible=forensic.eligible,
        esg_eligible=esg.eligible,
        baseline_evidence=baseline,
        glass_box_evidence=glass_box,
        forensic_evidence=forensic,
        esg_evidence=esg,
        replay_queries={
            'baseline': BASELINE_REPLAY_QUERY,
            'glass_box': GLASS_BOX_REPLAY_QUERY,
            'forensic': FORENSIC_REPLAY_QUERY
        },
        data_snapshot_hash=data_snapshot_hash
    )
    
    # Log evaluation
    log_evaluation(result)
    
    return result
```

---

**Document Version:** 1.0  
**Effective Date:** May 8, 2026  
**Implementation Deadline:** June 8, 2026 (30 days)  
**Governance Authority:** GridLedger Risk & Verification Committee  
**Next Review:** November 8, 2026 (mandatory 6-month governance review)

