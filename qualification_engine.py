#!/usr/bin/env python3
"""
GridLedger Qualification Engine v1.0
Automated node qualification evaluation per QUALIFICATION_ENGINE_SPECIFICATION_V1_0.md

This module implements node.evaluate_qualification() with deterministic, replayable logic.
"""

import sqlite3
import hashlib
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
from pathlib import Path

# Database configuration
DB_PATH = 'data/gridledger.db'

# SQL Query Constants (from specification)
BASELINE_REPLAY_QUERY = """
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
"""

GLASS_BOX_REPLAY_QUERY = """
WITH clean_candidates AS (
  SELECT
    mill_id,
    id as cycle_id,
    cycle_start,
    status,
    gap_breach_detected,
    expected_revenue,
    total_actual_cash,
    CASE
      WHEN status IN ('SEALED', 'VERIFIED')
        AND gap_breach_detected = 0
        AND expected_revenue > 0
        AND (1.0 - (expected_revenue - total_actual_cash) / expected_revenue) >= 0.90
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
"""

FORENSIC_REPLAY_QUERY = """
SELECT
  mill_id,
  COUNT(*) as cycle_count,
  ROUND(AVG((ABS(expected_revenue - total_actual_cash) - sub.avg_variance) * (ABS(expected_revenue - total_actual_cash) - sub.avg_variance)), 2) as variance_squared,
  ROUND(AVG(ABS(expected_revenue - total_actual_cash)), 2) as avg_abs_variance,
  CASE WHEN AVG(ABS(expected_revenue - total_actual_cash)) > 0
    THEN ROUND(100.0 * SQRT(AVG((ABS(expected_revenue - total_actual_cash) - sub.avg_variance) * (ABS(expected_revenue - total_actual_cash) - sub.avg_variance))) / AVG(ABS(expected_revenue - total_actual_cash)), 2)
    ELSE 0
  END as variance_coefficient_pct,
  ROUND(100.0 * SUM(CASE WHEN integrity_score IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as integrity_completeness_pct,
  MIN(cycle_start) as data_start,
  MAX(cycle_start) as data_end,
  CAST(JULIANDAY(MAX(cycle_start)) - JULIANDAY(MIN(cycle_start)) AS INTEGER) as span_days,
  SUM(CASE WHEN cycle_seal IS NOT NULL THEN 1 ELSE 0 END) = COUNT(*) as anchor_readiness
FROM cycle,
     (SELECT AVG(ABS(expected_revenue - total_actual_cash)) as avg_variance
      FROM cycle
      WHERE status IN ('SEALED', 'VERIFIED') AND mill_id = ? AND cycle_start <= ?) as sub
WHERE status IN ('SEALED', 'VERIFIED')
  AND mill_id = ?
  AND cycle_start <= ?
GROUP BY mill_id;
"""

@dataclass
class PathwayEvidence:
    eligible: bool
    reason: str
    metrics: Dict[str, Any]
    threshold_checks: Dict[str, bool]
    disqualifying_factors: List[str]
    replay_query: str

@dataclass
class QualificationResult:
    node_id: str
    evaluation_timestamp: datetime
    as_of_date: datetime
    baseline_eligible: bool
    glass_box_eligible: bool
    forensic_eligible: bool
    esg_eligible: bool
    baseline_evidence: PathwayEvidence
    glass_box_evidence: PathwayEvidence
    forensic_evidence: PathwayEvidence
    esg_evidence: PathwayEvidence
    replay_queries: Dict[str, str]
    data_snapshot_hash: str

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        # Convert datetime objects to ISO strings
        result['evaluation_timestamp'] = self.evaluation_timestamp.isoformat()
        result['as_of_date'] = self.as_of_date.isoformat()
        return result

    def to_json(self):
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2, default=str)

class QualificationEngine:
    """GridLedger Qualification Engine v1.0"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._validate_database()

    def _validate_database(self):
        """Ensure database and tables exist"""
        if not Path(self.db_path).exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Check cycle table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cycle'")
            if not cursor.fetchone():
                raise ValueError("cycle table not found in database")

    def _get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def _query_cycles(self, node_id: str, as_of_date: datetime):
        """Query cycles for node up to as_of_date"""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM cycle
                WHERE mill_id = ? AND cycle_start <= ?
                ORDER BY cycle_start
            """, (node_id, as_of_date))
            return [dict(row) for row in cursor.fetchall()]

    def _get_data_snapshot_hash(self, node_id: str, as_of_date: datetime) -> str:
        """Generate hash of cycle data for audit trail"""
        cycles = self._query_cycles(node_id, as_of_date)
        data_str = json.dumps(cycles, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()

    def evaluate_baseline(self, node_id: str, as_of_date: datetime) -> PathwayEvidence:
        """Evaluate Baseline pathway eligibility"""
        cycles = self._query_cycles(node_id, as_of_date)

        if not cycles:
            return PathwayEvidence(
                eligible=False,
                reason="No cycle records found",
                metrics={},
                threshold_checks={},
                disqualifying_factors=["No operational data"],
                replay_query=BASELINE_REPLAY_QUERY
            )

        # Calculate metrics
        total_cycles = len(cycles)
        sealed_cycles = len([c for c in cycles if c['status'] in ['SEALED', 'VERIFIED']])
        interrupted_cycles = len([c for c in cycles if c['status'] == 'INTERRUPTED'])
        completion_rate = (total_cycles - interrupted_cycles) / total_cycles if total_cycles > 0 else 0

        # Data span
        if cycles:
            start_dates = [datetime.fromisoformat(c['cycle_start']) for c in cycles]
            end_dates = [datetime.fromisoformat(c['cycle_end']) for c in cycles]
            data_span_days = (max(end_dates) - min(start_dates)).days
        else:
            data_span_days = 0

        # Variance existence
        variance_exists = all(c.get('variance') is not None for c in cycles)

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
            'completion_rate_pct': round(completion_rate * 100, 1),
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

    def evaluate_glass_box(self, node_id: str, as_of_date: datetime) -> PathwayEvidence:
        """Evaluate Glass Box pathway eligibility"""
        # Use the replay query to find max consecutive clean run
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(GLASS_BOX_REPLAY_QUERY, (node_id, as_of_date, node_id))
            result = cursor.fetchone()

        if not result or result[1] < 62:
            consecutive_count = result[1] if result else 0
            return PathwayEvidence(
                eligible=False,
                reason=f"Maximum consecutive clean cycles: {consecutive_count} (requires ≥62)",
                metrics={'max_consecutive_clean_cycles': consecutive_count},
                threshold_checks={'consecutive_clean_cycles >= 62': False},
                disqualifying_factors=["Insufficient consecutive clean cycles"],
                replay_query=GLASS_BOX_REPLAY_QUERY
            )

        # Get window details and check criteria
        mill_id, max_consecutive, window_start, window_end = result

        # Query cycles in the qualifying window
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM cycle
                WHERE mill_id = ? AND cycle_start BETWEEN ? AND ?
                ORDER BY cycle_start
            """, (node_id, window_start, window_end))
            window_cycles = [dict(row) for row in cursor.fetchall()]

        # Calculate window metrics
        adherence_rates = []
        gap_breaches = 0
        completed_cycles = 0

        for cycle in window_cycles:
            expected = cycle.get('expected_revenue', 0)
            actual = cycle.get('total_actual_cash', 0)

            if expected and expected > 0:
                adherence = 1.0 - (expected - actual) / expected
                adherence_rates.append(adherence)

            if cycle.get('gap_breach_detected'):
                gap_breaches += 1

            if cycle.get('status') in ['SEALED', 'VERIFIED']:
                completed_cycles += 1

        avg_adherence = sum(adherence_rates) / len(adherence_rates) if adherence_rates else 0
        completion_rate_pct = (completed_cycles / len(window_cycles)) * 100 if window_cycles else 0

        threshold_checks = {
            'consecutive_clean_cycles >= 62': max_consecutive >= 62,
            'avg_adherence >= 90%': avg_adherence >= 0.90,
            'gap_breaches == 0': gap_breaches == 0,
            'completion_rate == 100%': completion_rate_pct == 100.0
        }

        eligible = all(threshold_checks.values())

        metrics = {
            'max_consecutive_clean_cycles': max_consecutive,
            'window_start': window_start,
            'window_end': window_end,
            'avg_adherence_pct': round(avg_adherence * 100, 2),
            'gap_breaches': gap_breaches,
            'completion_rate_pct': round(completion_rate_pct, 1)
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

    def evaluate_forensic(self, node_id: str, as_of_date: datetime) -> PathwayEvidence:
        """Evaluate Forensic pathway eligibility"""
        cycles = self._query_cycles(node_id, as_of_date)
        sealed_cycles = [c for c in cycles if c['status'] in ['SEALED', 'VERIFIED']]
        
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
            start_dates = [datetime.fromisoformat(c['cycle_start']) for c in sealed_cycles]
            end_dates = [datetime.fromisoformat(c['cycle_end']) for c in sealed_cycles]
            data_span_days = (max(end_dates) - min(start_dates)).days
        else:
            data_span_days = 0
        
        # Variance coefficient calculation
        variances = []
        for c in sealed_cycles:
            expected = c.get('expected_revenue', 0)
            actual = c.get('total_actual_cash', 0)
            if expected is not None and actual is not None:
                variances.append(abs(expected - actual))
        
        if variances:
            avg_variance = sum(variances) / len(variances)
            if len(variances) > 1:
                variance_sum = sum((v - avg_variance) ** 2 for v in variances)
                stdev_variance = (variance_sum / (len(variances) - 1)) ** 0.5  # sample standard deviation
            else:
                stdev_variance = 0
            variance_coefficient = (stdev_variance / avg_variance) * 100 if avg_variance > 0 else 0
        else:
            variance_coefficient = 0
        
        # Integrity completeness
        integrity_scores = [c for c in sealed_cycles if c.get('integrity_score') is not None]
        integrity_completeness = len(integrity_scores) / len(sealed_cycles) if sealed_cycles else 0
        
        # Anchor readiness
        anchored_cycles = [c for c in sealed_cycles if c.get('cycle_seal') is not None]
        anchor_readiness = len(anchored_cycles) == len(sealed_cycles)
        
        threshold_checks = {
            'sealed_cycles >= 30': len(sealed_cycles) >= 30,
            'data_span >= 60 days': data_span_days >= 60,
            'variance_coefficient <= 15%': variance_coefficient <= 15.0,
            'integrity_completeness >= 80%': integrity_completeness >= 0.80,
            'anchor_readiness == 100%': anchor_readiness
        }
        
        eligible = all(threshold_checks.values())
        
        metrics = {
            'sealed_cycles': len(sealed_cycles),
            'data_span_days': data_span_days,
            'variance_coefficient_pct': round(variance_coefficient, 2),
            'integrity_completeness_pct': round(integrity_completeness * 100, 1),
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

    def evaluate_qualification(self, node_id: str, as_of_date: datetime) -> QualificationResult:
        """
        Main evaluation function per QUALIFICATION_ENGINE_SPECIFICATION_V1_0.md

        Args:
            node_id: Mill identifier (e.g., 'NABIWI')
            as_of_date: Evaluation date (data available up to this date)

        Returns:
            QualificationResult with eligibility states and evidence
        """
        if not node_id or not as_of_date:
            raise ValueError("node_id and as_of_date required")

        # Get data snapshot hash for audit trail
        data_snapshot_hash = self._get_data_snapshot_hash(node_id, as_of_date)

        # Evaluate each pathway
        baseline = self.evaluate_baseline(node_id, as_of_date)
        glass_box = self.evaluate_glass_box(node_id, as_of_date)
        forensic = self.evaluate_forensic(node_id, as_of_date)

        # ESG pathway (reserved for Phase B)
        esg = PathwayEvidence(
            eligible=False,
            reason="ESG pathway not yet implemented (Phase B)",
            metrics={},
            threshold_checks={},
            disqualifying_factors=["Phase B implementation required"],
            replay_query="-- ESG pathway not yet implemented"
        )

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

        # Log evaluation for audit trail
        self._log_evaluation(result)

        return result

    def _log_evaluation(self, result: QualificationResult):
        """Log evaluation for audit trail (placeholder - would write to audit log)"""
        # In production, this would write to audit table or file
        print(f"[AUDIT] Evaluated {result.node_id} as of {result.as_of_date}")
        print(f"[AUDIT] Baseline: {result.baseline_eligible}, Glass Box: {result.glass_box_eligible}, Forensic: {result.forensic_eligible}")
        print(f"[AUDIT] Data snapshot hash: {result.data_snapshot_hash[:16]}...")

# Convenience function for external use
def evaluate_qualification(node_id: str, as_of_date: datetime, db_path: str = DB_PATH) -> QualificationResult:
    """Convenience function to evaluate node qualification"""
    engine = QualificationEngine(db_path)
    return engine.evaluate_qualification(node_id, as_of_date)

if __name__ == '__main__':
    # Example usage
    engine = QualificationEngine()

    # Evaluate NABIWI as of May 8, 2026
    result = engine.evaluate_qualification('NABIWI', datetime(2026, 5, 8))

    print("=" * 80)
    print("QUALIFICATION ENGINE v1.0 - RESULTS")
    print("=" * 80)
    print(f"Node: {result.node_id}")
    print(f"As of: {result.as_of_date}")
    print(f"Evaluated: {result.evaluation_timestamp}")
    print()

    print("ELIGIBILITY SUMMARY:")
    print(f"  Baseline:  {'✓' if result.baseline_eligible else '✗'}")
    print(f"  Glass Box: {'✓' if result.glass_box_eligible else '✗'}")
    print(f"  Forensic:  {'✓' if result.forensic_eligible else '✗'}")
    print(f"  ESG:       {'✓' if result.esg_eligible else '✗'}")
    print()

    print("GLASS BOX EVIDENCE:")
    gb = result.glass_box_evidence
    print(f"  Eligible: {gb.eligible}")
    print(f"  Reason: {gb.reason}")
    if gb.metrics:
        for k, v in gb.metrics.items():
            print(f"  {k}: {v}")
    print()

    print("FORENSIC EVIDENCE:")
    fr = result.forensic_evidence
    print(f"  Eligible: {fr.eligible}")
    print(f"  Reason: {fr.reason}")
    if fr.metrics:
        for k, v in fr.metrics.items():
            print(f"  {k}: {v}")
    print()

    print("REPLAY VERIFICATION:")
    print(f"Data snapshot hash: {result.data_snapshot_hash}")
    print("Replay queries available for all pathways")
