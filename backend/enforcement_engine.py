from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Literal, List, Dict

from sqlmodel import Session, select

from scripts.init_db import engine, EventLog, TokenPurchase, MillIntegrityState
from backend.capital_at_risk import CapitalAtRisk

logger = logging.getLogger(__name__)


MillState = Literal["VERIFIED", "UNDER_REVIEW", "COMPROMISED", "SUSPENDED"]
BreachType = Literal[
    "INFO",
    "WARNING",
    "GAP_BREACH",
    "VARIANCE_BREACH",
    "ECONOMIC_DEFICIT",
    "GOVERNANCE_FAILURE",
]


@dataclass(frozen=True)
class EnforcementDecision:
    breach_type: BreachType
    severity_level: int  # 1..4
    next_state: MillState
    reason: str
    audit_required: bool = False
    freeze_outputs: bool = False
    block_token_purchase: bool = False


class EnforcementEngine:
    """
    Option B implementation: classify, escalate, penalize.

    This module is intentionally conservative:
    - If required inputs do not exist (no TokenPurchase, no physical anchor), it does not invent breaches.
    - It updates mill state as a durable control surface (MillIntegrityState).
    """

    @staticmethod
    def _get_or_create_state(session: Session, mill_id: str) -> MillIntegrityState:
        state = session.get(MillIntegrityState, mill_id)
        if state is None:
            state = MillIntegrityState(mill_id=mill_id)
            session.add(state)
            session.commit()
            session.refresh(state)
        return state

    @staticmethod
    def _escalate_state(current: MillState, target: MillState) -> MillState:
        order: List[MillState] = ["VERIFIED", "UNDER_REVIEW", "COMPROMISED", "SUSPENDED"]
        return order[max(order.index(current), order.index(target))]

    @classmethod
    def apply_decision(cls, mill_id: str, decision: EnforcementDecision) -> MillIntegrityState:
        with Session(engine) as session:
            state = cls._get_or_create_state(session, mill_id)
            old_state = state.state
            
            state.state = cls._escalate_state(state.state, decision.next_state)
            state.severity_level = max(int(state.severity_level), int(decision.severity_level))
            state.last_trigger = decision.breach_type
            state.last_reason = decision.reason
            state.updated_at = datetime.now(timezone.utc)
            session.add(state)
            session.commit()
            session.refresh(state)
            
            # Trigger capital control actions if state transitions to COMPROMISED or SUSPENDED
            new_state = state.state
            if new_state in ["COMPROMISED", "SUSPENDED"] and old_state != new_state:
                logger.info(
                    f"Enforcement decision triggers capital controls: {mill_id} "
                    f"{old_state} -> {new_state} ({decision.breach_type})"
                )
                try:
                    capital_events = CapitalAtRisk.handle_state_transition(
                        mill_id=mill_id,
                        old_state=old_state,
                        new_state=new_state,
                        breach_reason=decision.breach_type,
                    )
                    logger.info(f"Capital control actions executed: {len(capital_events)} events")
                except Exception as e:
                    logger.error(f"Failed to execute capital controls for {mill_id}: {e}")
                    # Don't fail the enforcement decision if capital controls fail
                    # (capital controls are best-effort)
            
            return state

    # ──────────────────────────────────────────────────────────────────────
    # Breach classification
    # ──────────────────────────────────────────────────────────────────────
    @classmethod
    def classify_gap_breach(cls, detail: str) -> EnforcementDecision:
        return EnforcementDecision(
            breach_type="GAP_BREACH",
            severity_level=3,
            next_state="COMPROMISED",
            reason=detail,
            audit_required=True,
            freeze_outputs=True,
            block_token_purchase=True,
        )

    @classmethod
    def classify_variance_breach(cls, variance_pct: float, tolerance_pct: float) -> EnforcementDecision:
        return EnforcementDecision(
            breach_type="VARIANCE_BREACH",
            severity_level=3,
            next_state="UNDER_REVIEW",
            reason=f"variance_pct={variance_pct:.2f} exceeded tolerance_pct={tolerance_pct:.2f}",
            audit_required=True,
            freeze_outputs=False,
            block_token_purchase=False,
        )

    @classmethod
    def classify_governance_failure(cls, status: str) -> EnforcementDecision:
        return EnforcementDecision(
            breach_type="GOVERNANCE_FAILURE",
            severity_level=2,
            next_state="UNDER_REVIEW",
            reason=f"event status={status}",
            audit_required=False,
            freeze_outputs=False,
            block_token_purchase=False,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Token Gap (Economic Ceiling)
    # ──────────────────────────────────────────────────────────────────────
    @classmethod
    def check_economic_ceiling(
        cls,
        mill_id: str,
        *,
        tolerance_pct: float = 2.0,
    ) -> Optional[EnforcementDecision]:
        """
        Soft/hard enforcement hook for the Token Gap Engine.

        Current behavior (conservative):
        - If no TokenPurchase exists, return None (no decision).
        - If TokenPurchase exists, compute total VERIFIED reported_kwh since last purchase.
        - If total exceeds purchased units + tolerance, return an ECONOMIC_DEFICIT decision.
        """
        with Session(engine) as session:
            last_purchase = session.exec(
                select(TokenPurchase)
                .where(TokenPurchase.mill_id == mill_id)
                .order_by(TokenPurchase.purchase_date.desc())
            ).first()

            if last_purchase is None:
                return None

            start_time = last_purchase.purchase_date
            events = session.exec(
                select(EventLog)
                .where(
                    EventLog.mill_id == mill_id,
                    EventLog.status == "VERIFIED",
                    EventLog.event_time >= start_time,
                )
                .order_by(EventLog.event_time)
            ).all()

            total_reported_kwh = 0.0
            for e in events:
                try:
                    payload = json.loads(e.payload_json)
                    total_reported_kwh += float(payload.get("reported_kwh", 0.0))
                except Exception:
                    continue

            ceiling = float(last_purchase.units_kwh) * (1.0 + (tolerance_pct / 100.0))
            if total_reported_kwh <= ceiling:
                return None

            return EnforcementDecision(
                breach_type="ECONOMIC_DEFICIT",
                severity_level=4,
                next_state="SUSPENDED",
                reason=(
                    f"reported_kwh_since_last_token={total_reported_kwh:.3f} "
                    f"exceeded purchased_kwh_with_tolerance={ceiling:.3f} "
                    f"(token_id={last_purchase.token_id})"
                ),
                audit_required=True,
                freeze_outputs=True,
                block_token_purchase=True,
            )

