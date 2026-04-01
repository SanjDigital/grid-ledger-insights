"""
Capital at Risk Handling Module.

Implements capital control actions triggered by mill integrity state transitions.
When a mill enters BREACH, COMPROMISED, or SUSPENDED states, this module:

1. CASH_SWEEP: Redirect incoming revenue to reduce outstanding exposure
2. CREDIT_COMPRESSION: Set remaining credit to zero
3. PRICING_ESCALATION: Apply penalty rate to outstanding balance

All actions are logged to CreditEvent table for audit trail.
Designed for gradual integration with actual cash movement systems.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional, List
from sqlmodel import Session, select

from scripts.init_db import (
    engine,
    Mill,
    CreditEvent,
    CreditMetrics,
    MillIntegrityState,
    TokenPurchase,
)

logger = logging.getLogger(__name__)


class CapitalAtRiskError(Exception):
    """Raised when capital control actions fail."""
    pass


class CapitalAtRisk:
    """Capital at Risk handling and enforcement."""

    # Default capital control parameters
    DEFAULT_CASH_SWEEP_PRIORITY = 0.9  # Sweep 90% of incoming revenue
    DEFAULT_PENALTY_RATE_BPS = 500     # +500 basis points (+5%)
    DEFAULT_CREDIT_COMPRESSION_RATE = 1.0  # Compress to zero immediately

    @classmethod
    def handle_state_transition(
        cls,
        mill_id: str,
        old_state: str,
        new_state: str,
        breach_reason: str,
    ) -> List[Dict]:
        """
        Trigger capital control actions when mill enters BREACH/COMPROMISED/SUSPENDED state.
        
        Args:
            mill_id: Mill identifier
            old_state: Previous integrity state
            new_state: New integrity state
            breach_reason: Reason for state transition (e.g., "GAP_BREACH", "ECONOMIC_DEFICIT")
        
        Returns:
            List of executed credit events (dicts)
        
        This is the main entry point for capital controls triggered by state changes.
        """
        logger.info(
            f"Capital at Risk handling triggered for {mill_id}: {old_state} -> {new_state} "
            f"(reason: {breach_reason})"
        )
        
        executed_events = []
        
        # Determine which actions to take based on new state
        if new_state in ["BREACH", "COMPROMISED", "SUSPENDED"]:
            # Escalate capital controls based on severity
            if new_state == "SUSPENDED":
                # Maximum enforcement: all three actions
                executed_events.extend(cls.trigger_cash_sweep(mill_id, new_state, breach_reason))
                executed_events.extend(cls.trigger_credit_compression(mill_id, new_state, breach_reason))
                executed_events.extend(cls.trigger_pricing_escalation(mill_id, new_state, breach_reason))
            
            elif new_state == "COMPROMISED":
                # Medium enforcement: cash sweep + pricing escalation
                executed_events.extend(cls.trigger_cash_sweep(mill_id, new_state, breach_reason))
                executed_events.extend(cls.trigger_pricing_escalation(mill_id, new_state, breach_reason))
            
            # For BREACH: handled via credit tier downgrade in DCE module
        
        return executed_events

    @classmethod
    def trigger_cash_sweep(
        cls,
        mill_id: str,
        trigger_state: str,
        trigger_reason: str,
        sweep_rate: float = DEFAULT_CASH_SWEEP_PRIORITY,
    ) -> List[Dict]:
        """
        Trigger cash sweep action: redirect incoming revenue to reduce outstanding exposure.
        
        Mechanism:
        1. Identify outstanding balance (credit extended to mill)
        2. Calculate sweep amount: incoming_revenue × sweep_rate
        3. Redirect sweep amount toward outstanding balance reduction
        4. Log action in CreditEvent with LOGGED status
        5. Prepare for payment processing system integration
        
        Args:
            mill_id: Mill identifier
            trigger_state: State that triggered action (COMPROMISED, SUSPENDED)
            trigger_reason: Breach type (GAP_BREACH, ECONOMIC_DEFICIT, etc.)
            sweep_rate: Fraction of incoming revenue to sweep (default 0.9 = 90%)
        
        Returns:
            List of CreditEvent dicts created
        """
        with Session(engine) as session:
            mill = session.get(Mill, mill_id)
            if not mill:
                raise CapitalAtRiskError(f"Mill {mill_id} not found")
            
            # Get latest credit metrics for this mill
            latest_metrics = session.exec(
                select(CreditMetrics)
                .where(CreditMetrics.mill_id == mill_id)
                .order_by(CreditMetrics.timestamp.desc())
            ).first()
            
            # Estimate outstanding balance
            # In production: fetch from Accounts Receivable / Credit Facility table
            # For now: estimate as DCE value (credit extended)
            outstanding_balance = latest_metrics.dynamic_credit_envelope if latest_metrics else 0.0
            
            if outstanding_balance <= 0:
                logger.warning(f"Cash sweep triggered for {mill_id}: outstanding_balance <= 0, skipping")
                return []
            
            # Simulate incoming revenue (in production: from payment stream)
            # For logging: assume typical daily revenue
            estimated_daily_revenue = latest_metrics.verified_revenue / 30 if latest_metrics else outstanding_balance / 10
            
            # Calculate sweep amount
            sweep_amount = estimated_daily_revenue * sweep_rate
            
            logger.info(
                f"CASH_SWEEP initiated for {mill_id}: "
                f"outstanding_balance={outstanding_balance:.2f}, "
                f"estimated_daily_revenue={estimated_daily_revenue:.2f}, "
                f"sweep_amount={sweep_amount:.2f}"
            )
            
            # Create CreditEvent record
            credit_event = CreditEvent(
                mill_id=mill_id,
                timestamp=datetime.now(timezone.utc),
                action_type="CASH_SWEEP",
                trigger_state=trigger_state,
                trigger_reason=trigger_reason,
                outstanding_balance=outstanding_balance,
                action_amount=sweep_amount,
                action_status="LOGGED",
                notes=(
                    f"Sweep {sweep_rate*100:.0f}% of incoming revenue ({sweep_amount:.2f}) "
                    f"toward outstanding balance ({outstanding_balance:.2f}). "
                    f"Ready for integration with payment processing system."
                ),
                credit_metric_id=latest_metrics.id if latest_metrics else None,
            )
            session.add(credit_event)
            session.commit()
            session.refresh(credit_event)
            
            return [
                {
                    "event_id": credit_event.id,
                    "action_type": "CASH_SWEEP",
                    "outstanding_balance": outstanding_balance,
                    "sweep_amount": sweep_amount,
                    "status": "LOGGED",
                }
            ]

    @classmethod
    def trigger_credit_compression(
        cls,
        mill_id: str,
        trigger_state: str,
        trigger_reason: str,
    ) -> List[Dict]:
        """
        Trigger credit compression action: set remaining credit to zero.
        
        Mechanism:
        1. Get current DCE from latest CreditMetrics
        2. Mark credit as "SUSPENDED" (zero remaining credit available)
        3. Block new token purchases
        4. Log action with timestamp of execution
        5. Prepare for credit facility system integration
        
        Args:
            mill_id: Mill identifier
            trigger_state: State that triggered action (COMPROMISED, SUSPENDED)
            trigger_reason: Breach type
        
        Returns:
            List of CreditEvent dicts created
        """
        with Session(engine) as session:
            mill = session.get(Mill, mill_id)
            if not mill:
                raise CapitalAtRiskError(f"Mill {mill_id} not found")
            
            # Get latest credit metrics
            latest_metrics = session.exec(
                select(CreditMetrics)
                .where(CreditMetrics.mill_id == mill_id)
                .order_by(CreditMetrics.timestamp.desc())
            ).first()
            
            dce_before = latest_metrics.dynamic_credit_envelope if latest_metrics else 0.0
            
            logger.info(
                f"CREDIT_COMPRESSION initiated for {mill_id}: "
                f"dce_before={dce_before:.2f} -> dce_after=0.0"
            )
            
            # Update CreditMetrics status to SUSPENDED
            if latest_metrics:
                latest_metrics.status = "SUSPENDED"
                session.add(latest_metrics)
                session.commit()
            
            # Create CreditEvent record
            credit_event = CreditEvent(
                mill_id=mill_id,
                timestamp=datetime.now(timezone.utc),
                action_type="CREDIT_COMPRESSION",
                trigger_state=trigger_state,
                trigger_reason=trigger_reason,
                outstanding_balance=dce_before,
                action_amount=dce_before,  # Full compression
                action_status="COMPLETED",
                execution_timestamp=datetime.now(timezone.utc),
                notes=(
                    f"Credit line compressed from {dce_before:.2f} to 0.0. "
                    f"All new credit facilities suspended. "
                    f"Existing outstanding balance remains due."
                ),
                credit_metric_id=latest_metrics.id if latest_metrics else None,
            )
            session.add(credit_event)
            session.commit()
            session.refresh(credit_event)
            
            return [
                {
                    "event_id": credit_event.id,
                    "action_type": "CREDIT_COMPRESSION",
                    "compressed_from": dce_before,
                    "compressed_to": 0.0,
                    "status": "COMPLETED",
                }
            ]

    @classmethod
    def trigger_pricing_escalation(
        cls,
        mill_id: str,
        trigger_state: str,
        trigger_reason: str,
        penalty_rate_bps: int = DEFAULT_PENALTY_RATE_BPS,
    ) -> List[Dict]:
        """
        Trigger pricing escalation action: apply penalty rate to outstanding balance.
        
        Mechanism:
        1. Get outstanding balance (from DCE)
        2. Apply penalty rate (e.g., +500 bps = +5%)
        3. Calculate equivalent annual interest increase
        4. Log action with penalty details
        5. Prepare for interest accrual system integration
        
        Args:
            mill_id: Mill identifier
            trigger_state: State that triggered action
            trigger_reason: Breach type
            penalty_rate_bps: Penalty rate in basis points (default 500 = +5%)
        
        Returns:
            List of CreditEvent dicts created
        """
        with Session(engine) as session:
            mill = session.get(Mill, mill_id)
            if not mill:
                raise CapitalAtRiskError(f"Mill {mill_id} not found")
            
            # Get latest credit metrics
            latest_metrics = session.exec(
                select(CreditMetrics)
                .where(CreditMetrics.mill_id == mill_id)
                .order_by(CreditMetrics.timestamp.desc())
            ).first()
            
            outstanding_balance = latest_metrics.dynamic_credit_envelope if latest_metrics else 0.0
            
            # Calculate interest impact
            penalty_pct = penalty_rate_bps / 10000.0  # Convert bps to decimal
            annual_interest_increase = outstanding_balance * penalty_pct
            
            logger.info(
                f"PRICING_ESCALATION initiated for {mill_id}: "
                f"outstanding_balance={outstanding_balance:.2f}, "
                f"penalty_rate={penalty_rate_bps} bps, "
                f"annual_interest_increase={annual_interest_increase:.2f}"
            )
            
            # Create CreditEvent record
            credit_event = CreditEvent(
                mill_id=mill_id,
                timestamp=datetime.now(timezone.utc),
                action_type="PRICING_ESCALATION",
                trigger_state=trigger_state,
                trigger_reason=trigger_reason,
                outstanding_balance=outstanding_balance,
                action_amount=annual_interest_increase,
                penalty_rate_bps=penalty_rate_bps,
                action_status="LOGGED",
                notes=(
                    f"Penalty rate of {penalty_rate_bps} bps applied to outstanding balance of {outstanding_balance:.2f}. "
                    f"Previously favorable financing terms suspended. "
                    f"Annual interest cost increases by {annual_interest_increase:.2f}. "
                    f"Ready for integration with interest accrual system."
                ),
                credit_metric_id=latest_metrics.id if latest_metrics else None,
            )
            session.add(credit_event)
            session.commit()
            session.refresh(credit_event)
            
            return [
                {
                    "event_id": credit_event.id,
                    "action_type": "PRICING_ESCALATION",
                    "outstanding_balance": outstanding_balance,
                    "penalty_rate_bps": penalty_rate_bps,
                    "annual_interest_increase": annual_interest_increase,
                    "status": "LOGGED",
                }
            ]

    @classmethod
    def get_credit_events(
        cls,
        mill_id: str,
        days: int = 30,
        action_type: Optional[str] = None,
    ) -> List[Dict]:
        """
        Retrieve capital control events for a mill.
        
        Args:
            mill_id: Mill identifier
            days: Historical window (default 30)
            action_type: Filter by action type (CASH_SWEEP, CREDIT_COMPRESSION, PRICING_ESCALATION)
        
        Returns:
            List of credit events as dicts
        """
        from datetime import timedelta
        
        with Session(engine) as session:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            query = select(CreditEvent).where(
                CreditEvent.mill_id == mill_id,
                CreditEvent.timestamp >= cutoff_date,
            )
            
            if action_type:
                query = query.where(CreditEvent.action_type == action_type)
            
            events = session.exec(query.order_by(CreditEvent.timestamp.desc())).all()
            
            return [
                {
                    "event_id": e.id,
                    "timestamp": e.timestamp.isoformat(),
                    "action_type": e.action_type,
                    "trigger_state": e.trigger_state,
                    "trigger_reason": e.trigger_reason,
                    "outstanding_balance": round(e.outstanding_balance, 2),
                    "action_amount": round(e.action_amount, 2),
                    "penalty_rate_bps": e.penalty_rate_bps,
                    "action_status": e.action_status,
                    "notes": e.notes,
                }
                for e in events
            ]

    @classmethod
    def get_capital_exposure_summary(mill_id: str) -> Dict:
        """
        Get summary of capital at risk for a mill.
        
        Returns:
            Dict with:
            - Outstanding balance (current DCE)
            - Active credit events in last 30 days
            - Estimated interest impact from pricing escalations
            - Total cash swept in last 30 days
        """
        with Session(engine) as session:
            mill = session.get(Mill, mill_id)
            if not mill:
                raise CapitalAtRiskError(f"Mill {mill_id} not found")
            
            # Get latest metrics
            latest_metrics = session.exec(
                select(CreditMetrics)
                .where(CreditMetrics.mill_id == mill_id)
                .order_by(CreditMetrics.timestamp.desc())
            ).first()
            
            outstanding_balance = latest_metrics.dynamic_credit_envelope if latest_metrics else 0.0
            
            # Get recent credit events
            from datetime import timedelta
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
            
            events = session.exec(
                select(CreditEvent)
                .where(
                    CreditEvent.mill_id == mill_id,
                    CreditEvent.timestamp >= cutoff_date,
                )
                .order_by(CreditEvent.timestamp.desc())
            ).all()
            
            # Calculate aggregates
            total_cash_swept = sum(
                (e.action_amount for e in events if e.action_type == "CASH_SWEEP"),
                0.0
            )
            
            total_interest_impact = sum(
                (e.action_amount for e in events if e.action_type == "PRICING_ESCALATION"),
                0.0
            )
            
            is_credit_suspended = any(
                e.action_type == "CREDIT_COMPRESSION" and e.action_status in ["LOGGED", "COMPLETED"]
                for e in events
            )
            
            return {
                "mill_id": mill_id,
                "mill_name": mill.name,
                "outstanding_balance": round(outstanding_balance, 2),
                "credit_status": "SUSPENDED" if is_credit_suspended else "ACTIVE",
                "capital_events_30d": len(events),
                "cash_swept_30d": round(total_cash_swept, 2),
                "interest_impact_annual": round(total_interest_impact, 2),
                "recent_events": CapitalAtRisk.get_credit_events(mill_id, days=30),
            }
