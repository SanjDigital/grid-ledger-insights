from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List
from sqlmodel import Session, select

from scripts.init_db import engine, ReconciliationRecord, OperatorProfile, EventLog, Mill


class TrustScorecardGenerator:
    """
    Aggregates technical audit data from reconciliation, consistency, and authority engines
    into a weighted Integrity Confidence Metric for investor and stakeholder disclosure.
    """

    def __init__(self, mill_id: str):
        self.mill_id = mill_id
        # Weights for the final Trust Score
        self.WEIGHTS = {
            "reconciliation": 0.50,  # Physical vs Ledger (The Anchor)
            "consistency": 0.30,     # Statistical Anomaly (The Brain)
            "authority": 0.20        # RBAC/Signatures (The Gatekeeper)
        }

    def generate_daily_scorecard(self, date: datetime) -> Dict:
        """
        Translates technical audit data into an Investor-Grade Trust Score.
        
        Args:
            date: The date for which to generate the scorecard
        
        Returns:
            Dict with metadata, KPIs, and investor verdict
        """
        with Session(engine) as session:
            mill = session.get(Mill, self.mill_id)
            if not mill:
                raise ValueError(f"Mill {self.mill_id} not found")

            # 1. Physical Sovereignty Component (0-100)
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
            end_of_day = start_of_day + timedelta(days=1)

            recon = session.exec(
                select(ReconciliationRecord)
                .where(
                    ReconciliationRecord.mill_id == self.mill_id,
                    # Match the reconciliation record by the day it ended.
                    ReconciliationRecord.end_time >= start_of_day,
                    ReconciliationRecord.end_time < end_of_day,
                )
            ).first()

            recon_score = 100.0
            recon_variance = 0.0
            root_hash = "UNANCHORED"
            recon_status = "NO_RECORD"

            if recon:
                recon_variance = recon.variance_pct
                recon_score = max(0.0, min(100.0, 100.0 - (recon_variance * 10)))
                root_hash = recon.root_hash
                recon_status = recon.status

            # 2. Statistical Integrity Component (0-100)
            daily_events = session.exec(
                select(EventLog)
                .where(
                    EventLog.mill_id == self.mill_id,
                    EventLog.event_time >= start_of_day,
                    EventLog.event_time < end_of_day,
                )
            ).all()

            # Count flagged events (FLAGGED_SUSPICION status indicates elevated suspicion)
            flagged_count = sum(1 for e in daily_events if e.status == "FLAGGED_SUSPICION")
            event_count = len(daily_events)
            violation_rate = (flagged_count / event_count * 100) if event_count > 0 else 0.0

            consistency_score = max(0.0, min(100.0, 100.0 - violation_rate))

            # 3. Governance Component (0-100)
            # Count rejected signatures and replays
            rejected_count = sum(1 for e in daily_events if e.status in ["REJECTED_SIGNATURE", "REJECTED_REPLAY"])
            governance_deduction = rejected_count * 10
            governance_score = max(0.0, 100.0 - governance_deduction)

            # 4. Final Weighted Trust Score
            trust_score = (
                (recon_score * self.WEIGHTS["reconciliation"]) +
                (consistency_score * self.WEIGHTS["consistency"]) +
                (governance_score * self.WEIGHTS["authority"])
            )

        efficiency = self._calculate_efficiency(event_count)
        verdict = self._generate_verdict(trust_score, recon_score)
        fraud_risk = self._assess_fraud_risk(trust_score, consistency_score)
        capital_impact = self.calculate_capital_impact(trust_score, recon_variance)

        return {
            "metadata": {
                "mill_id": self.mill_id,
                "mill_name": mill.name if mill else "UNKNOWN",
                "date": date.strftime("%Y-%m-%d"),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "sovereign_anchor": root_hash,
                "reconciliation_status": recon_status,
            },
            "components": {
                "reconciliation_score": round(recon_score, 1),
                "consistency_score": round(consistency_score, 1),
                "governance_score": round(governance_score, 1),
            },
            "kpis": {
                "trust_integrity_score": round(trust_score, 1),
                "reconciliation_variance_pct": round(recon_variance, 2),
                "energy_efficiency_kwh_per_unit": efficiency,
                "energy_accountability_ratio": round(recon.energy_accountability_ratio, 4) if recon else 0.0,
                "verified_throughput_kwh": round(recon.verified_throughput, 2) if recon else 0.0,
                "fraud_risk_level": fraud_risk,
                "event_count": event_count,
                "flagged_events": flagged_count,
            },
            "capital_impact": capital_impact,
            "investor_verdict": verdict,
        }

    def generate_scorecard_range(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        Generate a rolling scorecard for a date range (e.g., 30-day or 90-day audit).
        
        Args:
            start_date: Start of audit period
            end_date: End of audit period
        
        Returns:
            Aggregated scorecard with trend analysis
        """
        daily_scores = []
        current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        end_date_norm = end_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)

        while current_date < end_date_norm:
            try:
                daily_score = self.generate_daily_scorecard(current_date)
                daily_scores.append(daily_score)
            except Exception:
                pass
            current_date += timedelta(days=1)

        if not daily_scores:
            return {"error": f"No scorecard data for {self.mill_id} between {start_date} and {end_date}"}

        avg_trust = sum(s["kpis"]["trust_integrity_score"] for s in daily_scores) / len(daily_scores)
        min_trust = min(s["kpis"]["trust_integrity_score"] for s in daily_scores)
        max_trust = max(s["kpis"]["trust_integrity_score"] for s in daily_scores)

        trend = "IMPROVING" if daily_scores[-1]["kpis"]["trust_integrity_score"] > daily_scores[0]["kpis"]["trust_integrity_score"] else "STABLE" if abs(daily_scores[-1]["kpis"]["trust_integrity_score"] - daily_scores[0]["kpis"]["trust_integrity_score"]) < 5 else "DECLINING"

        return {
            "mill_id": self.mill_id,
            "period": {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d"),
                "days_reported": len(daily_scores),
            },
            "aggregated_metrics": {
                "average_trust_score": round(avg_trust, 1),
                "min_trust_score": round(min_trust, 1),
                "max_trust_score": round(max_trust, 1),
                "trend": trend,
            },
            "daily_scores": daily_scores,
        }

    def _calculate_efficiency(self, event_count: int) -> float:
        """
        Map energy events to output efficiency (e.g., kWh per tonne of output).
        For Mkwinda, this is typically ~11.4 kWh/tonne.
        """
        if event_count == 0:
            return 0.0
        # Placeholder: in production, fetch from Mill or SitePhysicsConstraint
        return 11.4

    def _generate_verdict(self, trust_score: float, recon_score: float) -> str:
        """
        Generate investor-facing verdict based on thresholds.
        
        Note: Verdict is based on Trust Score and Reconciliation Score, not EAR alone.
        Under Bounded Imperfection Doctrine, EAR < 1.0 can still be ACCEPTABLE.
        """
        if trust_score >= 90 and recon_score >= 95:
            return "🟢 SOVEREIGN: Maximum transparency and integrity. Minor discrepancies acceptable under bounded imperfection doctrine."
        elif trust_score >= 75:
            return "🟡 STABLE: Standard operational noise within acceptable parameters. EAR below 100% is normal. Monitor trends."
        elif trust_score >= 60:
            return "🟠 CAUTION: Elevated variance detected. Verify EAR is above 90% (acceptable threshold). Manual review recommended."
        else:
            return "🔴 WARNING: Significant operational drift. EAR likely below 90% (restricted threshold). Immediate investigation required."

    def _assess_fraud_risk(self, trust_score: float, consistency_score: float) -> str:
        """Assess fraud risk based on composite scores."""
        if trust_score > 85 and consistency_score > 80:
            return "LOW"
        elif trust_score > 70:
            return "MEDIUM"
        else:
            return "HIGH"

    def calculate_capital_impact(self, trust_score: float, variance_pct: float) -> Dict:
        """
        Translates Trust Score into Financial Risk Adjustments.
        Based on standard Malawian commercial lending risk profiles.
        
        Args:
            trust_score: Composite trust integrity score (0-100)
            variance_pct: Daily reconciliation variance percentage
        
        Returns:
            Dict with financing adjustments, audit efficiency, payback acceleration, and risk classification
        """
        # 1. Financing Rate Adjustment (Basis Points)
        # High trust (90+) = -3% to -5% interest rate reduction
        # Medium trust (75-89) = -1.5% to -2.5% reduction
        rate_discount = 0.0
        if trust_score > 90:
            rate_discount = -5.0
        elif trust_score > 75:
            rate_discount = -2.5
        elif trust_score > 60:
            rate_discount = -1.0
        else:
            rate_discount = 0.5  # Risk premium for low trust

        # Convert percentage to basis points (1% = 100 bps)
        basis_points = rate_discount * 100

        # 2. Audit Cost Reduction
        # Sovereign status reduces the need for manual site visits
        if trust_score > 90:
            audit_savings = "60% Reduction (SOVEREIGN: Minimal onsite audits required)"
            audit_visit_reduction = 0.60
        elif trust_score > 75:
            audit_savings = "30% Reduction (STABLE: Quarterly verification only)"
            audit_visit_reduction = 0.30
        else:
            audit_savings = "Standard (CAUTION: Monthly audits required)"
            audit_visit_reduction = 0.0

        # 3. Payback Acceleration
        # Lower leakage speeds up capital recovery
        if variance_pct < 1.0:
            payback_boost = "4 Months Faster"
            months_acceleration = 4
        elif variance_pct < 2.0:
            payback_boost = "2 Months Faster"
            months_acceleration = 2
        else:
            payback_boost = "Neutral"
            months_acceleration = 0

        # 4. Risk Classification & Capital Structure Implications
        if trust_score > 90:
            risk_class = "INSTITUTIONAL GRADE"
            capital_tier = "Tier 1"  # Most favorable lending terms
            max_leverage = 3.5  # Can leverage 3.5x equity
        elif trust_score > 75:
            risk_class = "COMMERCIAL"
            capital_tier = "Tier 2"  # Standard commercial terms
            max_leverage = 2.5
        elif trust_score > 60:
            risk_class = "SUBPRIME"
            capital_tier = "Tier 3"  # Elevated scrutiny
            max_leverage = 1.5
        else:
            risk_class = "HIGH RISK"
            capital_tier = "Tier 4"  # Restricted lending
            max_leverage = 1.0

        # 5. Estimated Annual Savings/Costs (in basis points of financed amount)
        # Combines rate adjustment + audit savings + payback acceleration
        total_basis_points_savings = basis_points + (audit_visit_reduction * 50) + (months_acceleration * 10)

        return {
            "financing_rate_adjustment_bps": int(basis_points),
            "financing_rate_adjustment_pct": round(rate_discount, 2),
            "audit_efficiency": audit_savings,
            "audit_visit_cost_reduction_pct": round(audit_visit_reduction * 100, 1),
            "payback_acceleration": payback_boost,
            "months_faster_recovery": months_acceleration,
            "risk_classification": risk_class,
            "capital_tier": capital_tier,
            "max_leverage_ratio": round(max_leverage, 2),
            "estimated_annual_savings_bps": int(total_basis_points_savings),
            "recommendation": self._capital_recommendation(trust_score, variance_pct, basis_points),
        }

    def _capital_recommendation(self, trust_score: float, variance_pct: float, basis_points: int) -> str:
        """Generate actionable capital investment recommendation."""
        if trust_score > 90 and variance_pct < 1.0:
            return "APPROVE: Prioritize for growth capital. Lock in favorable terms while SOVEREIGN status holds."
        elif trust_score > 75:
            return "APPROVE: Standard commercial terms. Monitor variance trend quarterly."
        elif trust_score > 60:
            return "CONDITIONAL: Approve only with increased collateral (80%+ LTV) and monthly audits."
        else:
            return "DECLINE: Risk profile exceeds institutional appetite. Recommend operational remediation before reapplication."

    def format_investor_report(self, scorecard: Dict) -> str:
        """Format scorecard as investor-grade markdown report."""
        meta = scorecard["metadata"]
        kpis = scorecard["kpis"]
        components = scorecard["components"]
        capital = scorecard.get("capital_impact", {})

        report = f"""
# GridLedger Trust Scorecard

## Asset Summary
- **Mill**: {meta['mill_name']} ({meta['mill_id']})
- **Date**: {meta['date']}
- **Status**: {meta['reconciliation_status']}

## Trust Integrity Score: **{kpis['trust_integrity_score']}/100** ({self._score_grade(kpis['trust_integrity_score'])})

### Component Breakdown
- Reconciliation (Physical): {components['reconciliation_score']}/100
- Consistency (Statistical): {components['consistency_score']}/100
- Governance (RBAC): {components['governance_score']}/100

## Key Performance Indicators

| Metric | Value |
|--------|-------|
| Reconciliation Variance | {kpis['reconciliation_variance_pct']}% |
| Energy Accountability Ratio (EAR) | {kpis['energy_accountability_ratio']} |
| Verified Throughput (VT) | {kpis['verified_throughput_kwh']} kWh |
| Energy Efficiency | {kpis['energy_efficiency_kwh_per_unit']} kWh/unit |
| Fraud Risk Level | {kpis['fraud_risk_level']} |
| Events Verified | {kpis['event_count']} |
| Flagged Events | {kpis['flagged_events']} |

## Capital Impact & Financial Implications

### Risk Classification: **{capital.get('risk_classification', 'N/A')}**
- **Capital Tier**: {capital.get('capital_tier', 'N/A')}
- **Max Leverage Ratio**: {capital.get('max_leverage_ratio', 'N/A')}x

### Financing Terms
- **Rate Adjustment**: {capital.get('financing_rate_adjustment_pct', 0)}% ({capital.get('financing_rate_adjustment_bps', 0)} basis points)
- **Estimated Annual Savings**: {capital.get('estimated_annual_savings_bps', 0)} basis points (~{round(capital.get('estimated_annual_savings_bps', 0) / 100, 2)}%)

### Operational Efficiency
- **Audit Cost Reduction**: {capital.get('audit_efficiency', 'Standard')}
- **Payback Acceleration**: {capital.get('payback_acceleration', 'Neutral')} ({capital.get('months_faster_recovery', 0)} months)

### Investment Recommendation
> **{capital.get('recommendation', 'Further analysis required')}**

## Cryptographic Anchor
**Root Hash**: `{meta['sovereign_anchor']}`

This hash cryptographically binds the physical meter reading to the exact state of the digital chain, providing forensic proof of data integrity.

## Investor Verdict
{scorecard['investor_verdict']}

---
*Report Generated: {meta['generated_at']}*
"""
        return report.strip()

    @staticmethod
    def _score_grade(score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 95:
            return "A+ (Excellent)"
        elif score >= 85:
            return "A (Very Good)"
        elif score >= 75:
            return "B (Good)"
        elif score >= 60:
            return "C (Acceptable)"
        else:
            return "D (Poor)"
