from datetime import datetime, timezone
from sqlmodel import Session, select

from scripts.init_db import engine, Mill, TokenPurchase, DailyReport, Cycle, Operator
from backend.cycle_manager import reconcile_cycle, can_purchase_token
from backend.capital_controls import CapitalControls, CapitalControlsError
from backend.capital_at_risk import CapitalAtRisk, CapitalAtRiskError
from backend.ear_thresholds import get_ear_tier, ear_status_summary

# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 Forensic Audit: Unified Baseline Constants (Node 02 - Nabiwi)
# ─────────────────────────────────────────────────────────────────────────────
# NABIWI_VERIFIED_LEAKAGE: Audit-proven leakage value ("Sovereign Number")
# Used in all DCE calculations and primary financial metrics
NABIWI_VERIFIED_LEAKAGE = 6833  # kWh - Phase 2 forensic audit verified

# NABIWI_HISTORICAL_ESTIMATE: Lower-confidence historical estimate
# Includes periods before full forensic audit, unverified system states
# Used only for historical context and transparency notes
NABIWI_HISTORICAL_ESTIMATE = 10991  # kWh - Historical estimate including unverified periods

# Forensic audit note for consistency across API responses
FORENSIC_AUDIT_NOTE = "Includes lower-confidence historical periods totaling 10,991 kWh."


def get_mill_performance_summary(mill_id: str):
    with Session(engine) as session:
        mill = session.get(Mill, mill_id)
        if not mill:
            return {"error": f"Mill {mill_id} not found"}

        cycle_records = session.exec(
            select(Cycle)
            .where(Cycle.mill_id == mill_id)
            .order_by(Cycle.reconciled_at.desc())
        ).all()

        cycles = []
        total_leakage = 0.0
        avg_ear = 0.0
        total_vt = 0.0

        for cycle in cycle_records[:5]:
            variance = cycle.variance
            if variance < 0:
                total_leakage += abs(variance)

            cycle_days = max(1, (cycle.cycle_end - cycle.cycle_start).days)
            utilization_pct = round((cycle.total_usage_kwh / (cycle_days * 100)) * 100, 2)

            cycles.append({
                "cycle_start": cycle.cycle_start.isoformat(),
                "cycle_end": cycle.cycle_end.isoformat(),
                "total_usage_kwh": cycle.total_usage_kwh,
                "total_actual_cash": cycle.total_actual_cash,
                "expected_revenue": cycle.expected_revenue,
                "variance": cycle.variance,
                "status": cycle.status,
                "capacity_utilization_pct": utilization_pct,
                "audit_summary": cycle.audit_summary,
            })

        # Calculate average EAR and total VT from reconciliation records
        from scripts.init_db import ReconciliationRecord
        recon_records = session.exec(
            select(ReconciliationRecord)
            .where(ReconciliationRecord.mill_id == mill_id)
            .order_by(ReconciliationRecord.timestamp.desc())
        ).all()[:5]
        
        if recon_records:
            avg_ear = sum(r.energy_accountability_ratio for r in recon_records) / len(recon_records)
            total_vt = sum(r.verified_throughput for r in recon_records)

        performance_summary = {
            "mill_id": mill_id,
            "mill_name": mill.name,
            "location": mill.location,
            "cycles": cycles,
            "total_leakage": total_leakage,
            # Phase 2 Forensic Audit: Use verified baseline for Node 02 (Nabiwi)
            "total_hidden_energy_verified_kWh": (
                NABIWI_VERIFIED_LEAKAGE if mill_id == "NABIWI" else total_leakage
            ),
            "historical_estimate_note": (
                FORENSIC_AUDIT_NOTE if mill_id == "NABIWI" else None
            ),
            "last_5_cycles": len(cycles),
            "average_energy_accountability_ratio": round(avg_ear, 4),
            "total_verified_throughput_kwh": round(total_vt, 2),
        }

        return performance_summary


def get_operator_integrity() -> dict:
    with Session(engine) as session:
        operators = session.exec(select(Operator)).all()

        operator_scores = []
        for op in operators:
            reports = session.exec(
                select(DailyReport).where(DailyReport.operator_id == op.operator_id)
            ).all()

            total_reports = len(reports)
            total_usage = sum((r.closing_kwh - r.opening_kwh) for r in reports)
            total_cash = sum(r.actual_cash for r in reports)
            expected_cash = total_usage * 1300
            variance = total_cash - expected_cash

            # operator integrity metric (0-100)
            base_score = 100
            penalty = abs(variance) / 1000
            penalty += total_reports * 0.1
            integrity_score = max(0, base_score - penalty)

            operator_scores.append({
                'operator_id': op.operator_id,
                'name': op.name,
                'phone': op.phone,
                'mill_id': op.mill_id,
                'total_reports': total_reports,
                'variance': variance,
                'integrity_score': round(integrity_score, 2),
            })

        operator_scores.sort(key=lambda x: x['integrity_score'], reverse=True)
        return {'operator_integrity_scores': operator_scores}


def get_mill_status(mill_id: str):
    with Session(engine) as session:
        mill = session.get(Mill, mill_id)
        if not mill:
            return {"error": f"Mill {mill_id} not found"}

        last_token = session.exec(
            select(TokenPurchase)
            .where(TokenPurchase.mill_id == mill_id)
            .order_by(TokenPurchase.purchase_date.desc())
        ).first()

        cycle_info = reconcile_cycle(mill_id)
        total_usage_since_token = 0.0
        total_cash_since_token = 0.0
        if last_token:
            reports = session.exec(
                select(DailyReport)
                .where(DailyReport.mill_id == mill_id)
                .where(DailyReport.report_date > last_token.purchase_date)
            ).all()
            total_usage_since_token = sum((r.closing_kwh - r.opening_kwh) for r in reports)
            total_cash_since_token = sum(r.actual_cash for r in reports)

        token_balance_kwh = None
        if last_token:
            token_balance_kwh = round(last_token.units_kwh - total_usage_since_token, 2)

        # Get latest reconciliation record for EAR and VT
        from scripts.init_db import ReconciliationRecord
        latest_recon = session.exec(
            select(ReconciliationRecord)
            .where(ReconciliationRecord.mill_id == mill_id)
            .order_by(ReconciliationRecord.timestamp.desc())
        ).first()

        status_response = {
            "lock_status": "Unlocked" if can_purchase_token(mill_id) else "Locked",
            "token_balance_kwh": token_balance_kwh,
            "current_cycle_variance": total_cash_since_token - (total_usage_since_token * mill.efficiency_baseline),
            "cycle_reconciliation": cycle_info,
        }

        if latest_recon:
            status_response["energy_accountability_ratio"] = round(latest_recon.energy_accountability_ratio, 4)
            status_response["verified_throughput_kwh"] = round(latest_recon.verified_throughput, 2)

        return status_response


def get_mill_credit_metrics(mill_id: str):
    """
    Get Dynamic Credit Envelope (DCE) and capital control metrics for a mill.
    
    DCE = α × VR × EAR × (1 − RiskPenalty)
    
    Returns comprehensive credit assessment including components breakdown,
    risk assessment, and financing recommendation.
    """
    try:
        dce_result = CapitalControls.calculate_dce(mill_id)
        return dce_result
    except CapitalControlsError as e:
        return {
            "error": str(e),
            "mill_id": mill_id,
        }


def get_mill_credit_history(mill_id: str, days: int = 30):
    """
    Get historical DCE calculations for a mill over the specified period.
    
    Useful for tracking credit envelope trends and risk evolution.
    
    Args:
        mill_id: Mill identifier
        days: Historical window (default 30 days)
    
    Returns:
        List of DCE snapshots with timestamps and components
    """
    with Session(engine) as session:
        mill = session.get(Mill, mill_id)
        if not mill:
            return {"error": f"Mill {mill_id} not found"}
    
    history = CapitalControls.get_dce_history(mill_id, days=days)
    
    return {
        "mill_id": mill_id,
        "mill_name": mill.name,
        "period_days": days,
        "dce_history": history,
    }


def get_capital_tier_recommendation(mill_id: str):
    """
    Get financing tier recommendation based on DCE and trust metrics.
    
    Combines DCE with trust scorecard to determine:
    - Tier 1 (Institutional): DCE >= 60% VR, EAR >= 95%, Zero breaches
    - Tier 2 (Commercial): DCE >= 40% VR, EAR >= 85%, Stable
    - Tier 3 (Subprime): DCE >= 20% VR, EAR >= 70%, Under review
    - Tier 4 (Restricted): DCE < 20% VR or persistent breaches
    """
    from backend.trust_scorecard import TrustScorecardGenerator
    
    try:
        dce_result = CapitalControls.calculate_dce(mill_id)
    except CapitalControlsError as e:
        return {"error": str(e), "mill_id": mill_id}
    
    dce = dce_result["dynamic_credit_envelope"]
    vr = dce_result["components"]["verified_revenue_vr"]
    ear = dce_result["components"]["energy_accountability_ratio_ear"]
    breach_count = dce_result["metrics"]["breaches_30d"]
    
    dce_pct = (dce / vr * 100) if vr > 0 else 0
    
    # Determine tier
    if dce_pct >= 60 and ear >= 0.95 and breach_count == 0:
        tier = "TIER_1_INSTITUTIONAL"
        max_leverage = 3.5
        interest_adjustment_bps = -500
        rationale = "Excellent accountability and track record"
    elif dce_pct >= 40 and ear >= 0.85:
        tier = "TIER_2_COMMERCIAL"
        max_leverage = 2.5
        interest_adjustment_bps = -250
        rationale = "Stable performance with acceptable variance"
    elif dce_pct >= 20 and ear >= 0.70:
        tier = "TIER_3_SUBPRIME"
        max_leverage = 1.5
        interest_adjustment_bps = 0
        rationale = "Acceptable but with elevated monitoring"
    else:
        tier = "TIER_4_RESTRICTED"
        max_leverage = 1.0
        interest_adjustment_bps = 300
        rationale = "Restricted lending due to weak DCE or accountability"
    
    return {
        "mill_id": mill_id,
        "capital_tier": tier,
        "dce_percentage_of_vr": round(dce_pct, 1),
        "max_leverage_ratio": round(max_leverage, 2),
        "interest_rate_adjustment_bps": int(interest_adjustment_bps),
        "interest_rate_adjustment_pct": round(interest_adjustment_bps / 100, 2),
        "rationale": rationale,
        "dce_data": dce_result,
    }


def get_capital_exposure_summary(mill_id: str):
    """
    Get capital at risk summary for a mill.
    
    Includes:
    - Current outstanding balance (DCE)
    - Credit status (ACTIVE or SUSPENDED)
    - Recent capital control events
    - Cash swept and interest impacts
    
    Returns:
        Dict with exposure summary and recent events
    """
    try:
        return CapitalAtRisk.get_capital_exposure_summary(mill_id)
    except CapitalAtRiskError as e:
        return {"error": str(e), "mill_id": mill_id}


def get_capital_events(mill_id: str, days: int = 30, action_type: str = None):
    """
    Get capital control events for a mill.
    
    Filters by:
    - Time window (last N days)
    - Action type (CASH_SWEEP, CREDIT_COMPRESSION, PRICING_ESCALATION)
    
    Args:
        mill_id: Mill identifier
        days: Historical window (default 30)
        action_type: Filter by action type (optional)
    
    Returns:
        List of capital control events
    """
    try:
        events = CapitalAtRisk.get_credit_events(mill_id, days=days, action_type=action_type)
        return {
            "mill_id": mill_id,
            "period_days": days,
            "event_count": len(events),
            "events": events,
        }
    except CapitalAtRiskError as e:
        return {"error": str(e), "mill_id": mill_id}


def get_ear_accountability_status(mill_id: str):
    """
    Get Energy Accountability Ratio (EAR) status for a mill.
    
    Applies Bounded Imperfection Doctrine:
    - EAR >= 95%: Full credit unlock (excellent accountability)
    - 90% <= EAR < 95%: Conditional financeable (acceptable with monitoring)
    - EAR < 90%: Restricted (concerning, needs investigation)
    
    Returns:
        Dict with EAR value, tier classification, and recommendations
    """
    with Session(engine) as session:
        mill = session.get(Mill, mill_id)
        if not mill:
            return {"error": f"Mill {mill_id} not found", "mill_id": mill_id}
        
        # Get latest reconciliation record for EAR
        from scripts.init_db import ReconciliationRecord
        latest_recon = session.exec(
            select(ReconciliationRecord)
            .where(ReconciliationRecord.mill_id == mill_id)
            .order_by(ReconciliationRecord.end_time.desc())
        ).first()
        
        if not latest_recon:
            return {
                "mill_id": mill_id,
                "mill_name": mill.name,
                "error": "No reconciliation records found",
                "ear_value": None,
            }
        
        ear = latest_recon.energy_accountability_ratio or 0.0
        
        # Get comprehensive status
        status = ear_status_summary(ear)
        
        # Add historical trend (last 5 records)
        recent_records = session.exec(
            select(ReconciliationRecord)
            .where(ReconciliationRecord.mill_id == mill_id)
            .order_by(ReconciliationRecord.end_time.desc())
            .limit(5)
        ).all()
        
        ear_history = [
            {
                "date": r.end_time.isoformat(),
                "ear": round(r.energy_accountability_ratio or 0.0, 4),
                "tier": get_ear_tier(r.energy_accountability_ratio or 0.0).name,
            }
            for r in reversed(recent_records)
        ]
        
        return {
            "mill_id": mill_id,
            "mill_name": mill.name,
            "current_ear": status,
            "history_5_days": ear_history,
            "thresholds": {
                "full_credit_unlock": "EAR >= 95%",
                "conditional_financeable": "90% <= EAR < 95%",
                "restricted": "EAR < 90%",
            },
            "note": "Bounded Imperfection Doctrine: EAR below 100% is acceptable if within tier thresholds",
        }


