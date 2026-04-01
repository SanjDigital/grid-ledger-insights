from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlmodel import Session, select, func
import logging
import json
from scripts.init_db import engine, Mill, TokenPurchase, DailyReport, Cycle, WalletLineage, EventLog, Operator, MillIntegrityState, TokenAllocation, CashReceipt
from backend.core_engine import Gatekeeper, AssetStatus
from backend.identity_manager import IdentityManager, IdentityError, ReplayError
from backend.authority_engine import AuthorityEngine, GapBreachError, AuthorityError
from backend.consistency_engine import ConsistencyEngine, SuspicionReport
from backend.reconciliation_engine import ReconciliationEngine, ReconError
from backend.enforcement_engine import EnforcementEngine
from backend.temporal_guard import TemporalGuard, TemporalWarning, TemporalBreach
from backend.revenue_engine import get_last_cycle_adherence, get_last_cycle_lag
from backend.policy_execution_engine import compute_per_cycle_advance_rate
from backend.config import BASE_ADVANCE_RATE


class FiduciaryLockError(Exception):
    """Raised when a cycle is in RED/blocked fiduciary lock state."""
    pass


logger = logging.getLogger(__name__)


def get_last_token_purchase(mill_id: str):
    with Session(engine) as session:
        stmt = select(TokenPurchase).where(TokenPurchase.mill_id == mill_id).order_by(TokenPurchase.purchase_date.desc())
        return session.exec(stmt).first()


def evaluate_mill_capital(mill_id: str, trust_score: float, session: Session) -> float:
    """
    Compute the advance rate for NEXT cycle based on LAST cycle's performance.
    
    This is the core integration point for per-cycle token allocation:
    - Fetches last cycle's adherence (cash_remitted / expected_revenue)
    - Fetches last cycle's latency (hours from allocation to receipt)
    - Applies both penalties to base_rate for next cycle
    
    Formula:
        advance_rate = base_rate × (trust_score/100) × (adherence²) × latency_penalty(lag_hours)
    
    Scenarios:
    - Perfect previous cycle (adherence 1.0, <24h lag) → normal rate
    - Good cycle (adherence 0.95, 30h lag) → ~30% reduction
    - Disputed cycle (adherence 0.0) → severe reduction
    - MISSING cycle (adherence 0.0) → severe reduction
    
    Args:
        mill_id: Mill identifier
        trust_score: Operator integrity score (0-100) from trust scorecard
        session: SQLModel session for database queries
    
    Returns:
        float: Effective advance rate for next token allocation (0.0 to base_rate)
    
    Called by:
        - issue_token() when allocating next token
        - API endpoints computing next cycle capital
        - Batch jobs determining allocation eligibility
    """
    try:
        # Fetch prior cycle performance metrics
        adherence = get_last_cycle_adherence(mill_id, session)
        lag_hours = get_last_cycle_lag(mill_id, session)
        
        logger.debug(
            f"evaluate_mill_capital({mill_id}): "
            f"trust={trust_score}, adherence={adherence}, lag={lag_hours}h"
        )
        
        # Compute advance rate for this mill's next cycle
        rate = compute_per_cycle_advance_rate(
            trust_score=trust_score,
            adherence=adherence,
            lag_hours=lag_hours,
            base_rate=BASE_ADVANCE_RATE
        )
        
        logger.info(
            f"Computed next advance rate for {mill_id}: "
            f"{rate:.4f} (trust={trust_score}, adherence={adherence:.2f}, lag={lag_hours}h)"
        )
        
        return rate
        
    except Exception as e:
        logger.error(f"evaluate_mill_capital({mill_id}) failed: {e}", exc_info=True)
        # Fail-safe: return minimum rate
        return 0.0


def reconcile_cycle(mill_id: str):
    with Session(engine) as session:
        mill = session.get(Mill, mill_id)
        if not mill:
            return {"error": f"Mill {mill_id} not found", "status": "UNKNOWN"}

        last_purchase = get_last_token_purchase(mill_id)
        if last_purchase:
            since_date = last_purchase.purchase_date
        else:
            since_date = datetime(1970, 1, 1, tzinfo=timezone.utc)

        reports = session.exec(
            select(DailyReport)
            .where(DailyReport.mill_id == mill_id)
            .where(DailyReport.report_date > since_date)
        ).all()

        total_usage = 0.0
        total_actual_cash = 0.0

        for r in reports:
            total_usage += (r.closing_kwh - r.opening_kwh)
            total_actual_cash += r.actual_cash

        expected_revenue = total_usage * mill.efficiency_baseline
        variance = total_actual_cash - expected_revenue

        gate = Gatekeeper()
        gate_status = gate.reconcile(total_actual_cash, expected_revenue)

        # Gap-breach detection: meter continuity check between DailyReports
        gap_breaches = AuthorityEngine.detect_gap_breaches(mill_id)
        gap_breach_detected = len(gap_breaches) > 0

        if gate_status == AssetStatus.UNLOCKED and not gap_breach_detected:
            status = "RECONCILED"
            audit_summary = f"{mill.name} ({mill.location}) reconciled with variance MK {variance:,.0f}."
        elif gap_breach_detected:
            status = "BLOCKED"
            gap_detail = "; ".join([
                f"gap {g['gap']} between report {g['previous_report_id']} and {g['current_report_id']}"
                for g in gap_breaches
            ])
            audit_summary = f"{mill.name} ({mill.location}) blocked due to gap breach: {gap_detail}."
            # record as fiscal incident if not yet blocked by gate status
            gate.trigger_fiscal_lock_incident(
                site_id=mill_id,
                score=0.0,
                reason="Gap breach in meter continuity detected",
                payload={"breaches": gap_breaches},
            )
        elif gate_status == AssetStatus.LOCKED:
            status = "RESTRICTED"
            audit_summary = f"{mill.name} ({mill.location}) under restriction: variance MK {variance:,.0f}."
        else:
            status = "BLOCKED"
            audit_summary = f"{mill.name} ({mill.location}) blocked fiduciary state: variance MK {variance:,.0f}."

        # Persist as audit trail in Cycle table (idempotent on same period)
        cycle_end = datetime.now(timezone.utc)
        with Session(engine) as inner_session:
            existing_cycle = inner_session.exec(
                select(Cycle)
                .where(Cycle.mill_id == mill_id)
                .where(Cycle.cycle_start == since_date)
                .where(Cycle.token_id == (last_purchase.token_id if last_purchase else None))
            ).first()

            if not existing_cycle:
                cycle_entry = Cycle(
                    mill_id=mill_id,
                    token_id=last_purchase.token_id if last_purchase else None,
                    revenue_wallet_id=last_purchase.revenue_wallet_id if last_purchase else None,
                    opex_wallet_id=last_purchase.opex_wallet_id if last_purchase else None,
                    integrity_score=100.0 if status == "RECONCILED" else (80.0 if status == "RESTRICTED" else 50.0),
                    cycle_start=since_date,
                    cycle_end=cycle_end,
                    total_usage_kwh=total_usage,
                    total_actual_cash=total_actual_cash,
                    expected_revenue=expected_revenue,
                    variance=variance,
                    status=status,
                    audit_summary=audit_summary,
                    gap_breach_detected=gap_breach_detected,
                    gap_breach_details="; ".join([
                        f"{g['previous_report_id']}->{g['current_report_id']} gap={g['gap']}"
                        for g in gap_breaches
                    ]) if gap_breach_detected else None,
                )
                inner_session.add(cycle_entry)
                inner_session.commit()

                lineage_event = WalletLineage(
                    cycle_id=cycle_entry.id,
                    token_id=cycle_entry.token_id,
                    from_wallet_id=cycle_entry.revenue_wallet_id,
                    to_wallet_id=cycle_entry.opex_wallet_id,
                    integrity_score=cycle_entry.integrity_score,
                    reason="Cycle custody trace created",
                    created_by_reconcile=True,
                )
                inner_session.add(lineage_event)
                inner_session.commit()

        return {
            "mill_id": mill_id,
            "mill_name": mill.name,
            "location": mill.location,
            "total_usage_kwh": total_usage,
            "total_actual_cash": total_actual_cash,
            "expected_revenue": expected_revenue,
            "variance": variance,
            "status": status,
            "audit_summary": audit_summary,
            "last_purchase_date": since_date,
            "reports_count": len(reports),
        }


def ingest_event(mill_id: str, operator_id: str, payload_json: str, signature_b64: str):
    """Append-only event ingestion with cryptographic verify and replay track."""

    with Session(engine) as session:
        operator = session.get(Operator, operator_id)
        if not operator:
            raise KeyError(f"Operator {operator_id} not found")

        status = "VERIFIED"
        prev_hash = operator.last_event_hash or ""
        payload_hash = IdentityManager.compute_payload_hash(payload_json)

        # ═══════════════════════════════════════════════════════════════════════
        # LAYER 0: Temporal Integrity Check (before all other validation)
        # ═══════════════════════════════════════════════════════════════════════
        payload_obj = json.loads(payload_json)
        event_timestamp = TemporalGuard.extract_timestamp_from_payload(payload_json)
        
        try:
            drift_seconds, temporal_status = TemporalGuard.check_timestamp_drift(
                mill_id=mill_id,
                event_timestamp=event_timestamp,
                source=f"operator:{operator_id}",
            )
        except TemporalBreach as e:
            # Systematic clock manipulation detected: escalate to UNDER_REVIEW
            status = "FLAGGED_TEMPORAL_BREACH"
            # Update mill integrity state
            mill_state = session.exec(
                select(MillIntegrityState).where(MillIntegrityState.mill_id == mill_id)
            ).first()
            if not mill_state:
                mill_state = MillIntegrityState(mill_id=mill_id)
            mill_state.state = "UNDER_REVIEW"
            mill_state.severity_level = 3
            mill_state.last_trigger = "TEMPORAL_BREACH"
            mill_state.last_reason = str(e)
            mill_state.updated_at = datetime.now(timezone.utc)
            session.add(mill_state)
            session.commit()
        except TemporalWarning as e:
            # Single violation: flag but allow event processing with reduced trust
            status = "FLAGGED_TEMPORAL_WARNING"

        # ═══════════════════════════════════════════════════════════════════════
        # LAYER 1-N: Role-based permissions and behavioral guardrails
        # ═══════════════════════════════════════════════════════════════════════
        if status == "VERIFIED":  # Only proceed if no temporal breach
            try:
                AuthorityEngine.evaluate_operator_action(operator_id, "SUBMIT_REPORT", payload_obj)
            except (AuthorityError, GapBreachError) as e:
                # Operational consequence: persist enforcement state before rejecting.
                EnforcementEngine.apply_decision(
                    mill_id,
                    EnforcementEngine.classify_gap_breach(str(e))
                    if isinstance(e, GapBreachError)
                    else EnforcementEngine.classify_governance_failure("AUTHORITY_ERROR"),
                )
                raise AuthorityError(f"Operator action not permitted: {e}") from e

        # ═══════════════════════════════════════════════════════════════════════
        # Signature verification
        # ═══════════════════════════════════════════════════════════════════════
        if status == "VERIFIED":
            try:
                IdentityManager.verify_event(payload_json, signature_b64, operator.public_key)
            except IdentityError:
                status = "REJECTED_SIGNATURE"

        # Early capture of nonce to avoid replay.
        try:
            data = json.loads(payload_json)
        except json.JSONDecodeError:
            status = "REJECTED_SIGNATURE"
            data = {}

        incoming_nonce = data.get("nonce")

        # update consistency profile and suspicion scoring only on verified events
        suspicion_report: Optional[SuspicionReport] = None
        if status == "VERIFIED":
            yield_rate = float(data.get("reported_cash", 0.0)) / max(float(data.get("reported_kwh", 0.0)), 1e-9)
            opex = float(data.get("opex_mwk", 0.0))
            profile = ConsistencyEngine.update_profile(operator_id, yield_rate, opex)
            suspicion_report = ConsistencyEngine.calculate_suspicion_score(data, profile)
            if suspicion_report.score >= 20:
                # if suspicion is elevated, treat as red alert -> block
                status = "FLAGGED_SUSPICION"

                # also in real pipeline, emit to incident stream (not shown)

        if status == "VERIFIED":
            try:
                IdentityManager.verify_nonce(incoming_nonce, operator.last_nonce)
            except ReplayError:
                status = "REJECTED_REPLAY"

        # Economic ceiling check (Token Gap Engine) — conservative:
        # only enforced when TokenPurchase exists for this mill.
        if status == "VERIFIED":
            decision = EnforcementEngine.check_economic_ceiling(mill_id, tolerance_pct=2.0)
            if decision is not None:
                EnforcementEngine.apply_decision(mill_id, decision)
                status = "FLAGGED_ECONOMIC_DEFICIT"

        event = EventLog(
            mill_id=mill_id,
            operator_id=operator_id,
            payload_json=payload_json,
            payload_hash=payload_hash,
            signature=signature_b64,
            prev_hash=prev_hash,
            status=status,
        )
        session.add(event)

        if status == "VERIFIED":
            operator.last_nonce = incoming_nonce
            operator.last_event_hash = payload_hash

        session.commit()
        # Ensure the returned ORM instance stays usable after the session
        # context exits (avoids DetachedInstanceError in tests).
        session.refresh(event)

        if status in {"REJECTED_SIGNATURE", "REJECTED_REPLAY"}:
            EnforcementEngine.apply_decision(mill_id, EnforcementEngine.classify_governance_failure(status))

        if status == "FLAGGED_TEMPORAL_BREACH":
            EnforcementEngine.apply_decision(mill_id, EnforcementEngine.classify_governance_failure("TEMPORAL_BREACH"))
            raise TemporalBreach(f"Event from {operator_id} rejected: temporal breach detected for mill {mill_id}")

        if status == "FLAGGED_TEMPORAL_WARNING":
            # Log the warning but allow event to be processed (reduced trust)
            EnforcementEngine.apply_decision(mill_id, EnforcementEngine.classify_governance_failure("TEMPORAL_WARNING"))

        if status == "REJECTED_REPLAY":
            raise ReplayError("Replay detected; event rejected and gate locked.")

        if status == "REJECTED_SIGNATURE":
            raise IdentityError("Invalid signature; event rejected.")

        return event


def can_purchase_token(mill_id: str):
    cycle_info = reconcile_cycle(mill_id)

    if "error" in cycle_info:
        return False

    # Enforcement control surface: suspended mills cannot purchase tokens.
    from scripts.init_db import MillIntegrityState
    with Session(engine) as session:
        state = session.get(MillIntegrityState, mill_id)
        if state is not None and state.state == "SUSPENDED":
            return False

    # Circuit breaker: block if last cycle is blocked due to fiduciary red state
    if cycle_info["status"] == "BLOCKED":
        return False

    # If no DailyReport data exists yet, allow initial token purchase
    if cycle_info["reports_count"] == 0:
        return True

    # Only allow next token if the previous cycle has been reconciled
    return cycle_info["status"] == "RECONCILED"


def detect_missing_cycles() -> int:
    """
    Background job: detect PENDING allocations older than MISSING_CYCLE_TIMEOUT_HOURS
    and mark them as MISSING.
    
    A PENDING allocation becomes MISSING when:
    - Status is 'PENDING' (no cash receipt observed)
    - Allocated more than MISSING_CYCLE_TIMEOUT_HOURS ago (default 48h)
    - Not yet marked DISPUTED (admin resolution takes precedence)
    
    This runs periodically to enforce timely cash reconciliation. Mills with
    MISSING cycles incur adherence penalty (0.0) when computing next cycle's
    advance rate.
    
    Returns:
        int: Count of cycles marked MISSING in this run
    
    Raises:
        Exception: If database operations fail (logged but not fatal)
    """
    from backend.config import MISSING_CYCLE_TIMEOUT_HOURS
    
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=MISSING_CYCLE_TIMEOUT_HOURS)
        
        with Session(engine) as session:
            # Find all PENDING allocations past the timeout window
            pending_allocations = session.exec(
                select(TokenAllocation).where(
                    TokenAllocation.status == "PENDING",
                    TokenAllocation.allocated_at < cutoff
                )
            ).all()
            
            marked_count = 0
            for allocation in pending_allocations:
                allocation.status = "MISSING"
                session.add(allocation)
                marked_count += 1
                
                logger.warning(
                    f"Marked allocation {allocation.id} (mill={allocation.mill_id}) as MISSING "
                    f"(allocated_at={allocation.allocated_at}, cutoff={cutoff})"
                )
            
            if marked_count > 0:
                session.commit()
                logger.info(f"detect_missing_cycles() marked {marked_count} allocations as MISSING")
            else:
                logger.debug("detect_missing_cycles() found no PENDING allocations past timeout")
        
        return marked_count
        
    except Exception as e:
        logger.error(f"detect_missing_cycles() failed: {e}", exc_info=True)
        return 0


def resolve_dispute(allocation_id: int, resolved_by: str, resolution_notes: str) -> dict:
    """
    Admin endpoint: RESOLVE a disputed allocation by marking it CLOSED.
    
    A DISPUTED allocation results from:
    - Cash remitted doesn't match expected revenue (variance beyond tolerance)
    - Cash receipt arrives late (past MISSING_CYCLE_TIMEOUT_HOURS)
    - Operator challenges allocation decision
    
    Admin resolution process:
    - Investigates the discrepancy
    - Determines acceptable explanation (meter error, network delay, etc.)
    - Marks allocation CLOSED to release capital for next cycle
    - Records notes explaining the resolution
    
    Post-resolution:
    - get_last_cycle_adherence() now sees CLOSED (verified receipt) → returns actual cash/expected
    - Penalty no longer applied unless new issues arise
    - Next cycle can proceed with normal advance rate calculation
    
    Args:
        allocation_id: ID of the DISPUTED cycle to resolve
        resolved_by: Admin name/ID performing resolution
        resolution_notes: Explanation of resolution (e.g., "Network delay confirmed, 49h is normal for MTN")
    
    Returns:
        dict with status, allocation details, and any error
    
    Raises:
        ValueError: If allocation not DISPUTED or not found
    """
    try:
        with Session(engine) as session:
            allocation = session.get(TokenAllocation, allocation_id)
            
            if not allocation:
                return {
                    "status": "ERROR",
                    "error": f"Allocation {allocation_id} not found",
                    "allocation_id": allocation_id
                }
            
            # Only DISPUTED allocations can be resolved
            if allocation.status == "CLOSED":
                reason = allocation.resolution_notes if allocation.resolution_notes else "closed normally"
                return {
                    "status": "ERROR",
                    "error": f"Allocation {allocation_id} is already CLOSED ({reason})",
                    "allocation_id": allocation_id,
                    "current_status": "CLOSED"
                }
            elif allocation.status != "DISPUTED":
                return {
                    "status": "ERROR",
                    "error": f"Cannot resolve: allocation is {allocation.status}, not DISPUTED",
                    "allocation_id": allocation_id,
                    "current_status": allocation.status
                }
            
            # Find associated cash receipt
            receipt = session.exec(
                select(CashReceipt).where(CashReceipt.allocation_id == allocation_id)
            ).first()
            
            if not receipt:
                return {
                    "status": "ERROR",
                    "error": f"No cash receipt found for allocation {allocation_id}",
                    "allocation_id": allocation_id
                }
            
            # Resolve: mark allocation CLOSED and receipt VERIFIED
            allocation.status = "CLOSED"
            allocation.resolved_by = resolved_by
            allocation.resolved_at = datetime.now(timezone.utc)
            allocation.resolution_notes = resolution_notes
            
            receipt.verified = True
            
            session.add(allocation)
            session.add(receipt)
            session.commit()
            
            logger.info(
                f"RESOLVED dispute for allocation {allocation_id} (mill={allocation.mill_id}) "
                f"by {resolved_by}: {resolution_notes}"
            )
            
            return {
                "status": "SUCCESS",
                "allocation_id": allocation_id,
                "mill_id": allocation.mill_id,
                "allocation_status": "CLOSED",
                "receipt_verified": True,
                "resolved_by": resolved_by,
                "resolved_at": allocation.resolved_at.isoformat(),
                "resolution_notes": resolution_notes,
                "message": "Dispute resolved and allocation closed"
            }
    
    except Exception as e:
        logger.error(f"resolve_dispute({allocation_id}) failed: {e}", exc_info=True)
        return {
            "status": "ERROR",
            "error": f"Internal error: {str(e)}",
            "allocation_id": allocation_id
        }


def issue_token(
    mill_id: str,
    token_id: str,
    units_kwh: float,
    cost_mwk: float,
    revenue_wallet_id: str,
    opex_wallet_id: str,
    manual_clearance_code: Optional[str] = None,
):
    """Issue token only when fiduciary state allows it."""
    from scripts.init_db import engine

    cycle_status = reconcile_cycle(mill_id)["status"]
    if cycle_status == "BLOCKED":
        if manual_clearance_code != "FORCE-UNLOCK-001":
            raise FiduciaryLockError(
                "Cannot issue token: mill is in RED/BLOCKED fiduciary state. Manual clearance required."
            )
        # fallback path: allow with manual clearance, but preserve carefully

    if not can_purchase_token(mill_id) and cycle_status != "BLOCKED":
        raise FiduciaryLockError("Cannot issue token: previous cycle is not reconciled.")

    with Session(engine) as session:
        token = TokenPurchase(
            token_id=token_id,
            mill_id=mill_id,
            units_kwh=units_kwh,
            cost_mwk=cost_mwk,
            revenue_wallet_id=revenue_wallet_id,
            opex_wallet_id=opex_wallet_id,
        )
        session.add(token)
        session.commit()

    return token


def trigger_daily_recon(mill_id: str, physical_reading: float, tolerance_pct: float = 2.0) -> dict:
    """
    Trigger a daily reconciliation for a mill.
    
    Args:
        mill_id: The mill ID
        physical_reading: The physical meter reading at end of day
        tolerance_pct: Variance tolerance (default 2%)
    
    Returns:
        Dict with reconciliation status and details
    
    Raises:
        ValueError if window is in the future
        ReconError if reconciliation fails
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=1)

    try:
        record = ReconciliationEngine.store_reconciliation(
            mill_id=mill_id,
            physical_reading=physical_reading,
            start_time=start_time,
            end_time=end_time,
            tolerance_pct=tolerance_pct,
        )

        result = {
            "mill_id": mill_id,
            "status": record.status,
            "variance_pct": record.variance_pct,
            "event_count": record.event_count,
            "root_hash": record.root_hash,
            "physical_kwh": record.physical_consumed,
            "reported_kwh": record.reported_kwh,
            "total_cash": record.total_cash,
        }

        if record.status == "UNDER_REVIEW":
            EnforcementEngine.apply_decision(
                mill_id,
                EnforcementEngine.classify_variance_breach(record.variance_pct, tolerance_pct),
            )
            gate = Gatekeeper()
            gate.trigger_fiscal_lock_incident(
                site_id=mill_id,
                score=100.0 - record.variance_pct,
                reason=f"Daily reconciliation under review: variance {record.variance_pct:.2f}%",
                payload={"record_id": record.id, "root_hash": record.root_hash},
            )

        return result

    except ValueError as ve:
        raise ve
    except Exception as e:
        raise ReconError(f"Daily reconciliation failed for {mill_id}: {e}") from e
