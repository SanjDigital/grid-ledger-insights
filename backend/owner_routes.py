"""
Owner App Routes — GridLedger

Capital command interface for the mill owner.
Authentication: X-API-Key header.

All monetary values use Decimal; non‑financial scores (priority, trust) use float
but are clearly marked as such. Every allocation decision is persisted for audit.
"""

import logging
import os
import statistics
import math
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select, text
from sqlalchemy import func, and_, exc as sa_exc
from sqlalchemy.orm import selectinload

from scripts.init_db import (
    CashReceipt,
    Mill,
    MillIntegrityState,
    TokenAllocation,
    DecisionAudit,
    IdempotencyRecord,
    engine,
)
from backend.config import MISSING_CYCLE_TIMEOUT_HOURS
from backend.policy_execution_engine import compute_per_cycle_advance_rate
from backend.revenue_engine import (
    get_certification_status,
    get_last_cycle_adherence,
    get_last_cycle_lag,
)
from backend.token_gateway import TokenGateway, AllocationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/owner", tags=["owner"])

# ============================================================================
# CONSTANTS (Policy Layer)
# ============================================================================

LOCKED_CYCLE_HOURS: float = MISSING_CYCLE_TIMEOUT_HOURS * 1.5
MIN_CAPITAL_AT_RISK_FOR_FEED: Decimal = Decimal("1000.0")   # MWK – noise floor
MAX_EXPOSURE_PER_MILL: Decimal = Decimal("500000.0")        # MWK – per‑mill credit limit
BASE_CYCLE_KWH: Decimal = Decimal("59.9")
ADHERENCE_WARNING: Decimal = Decimal("0.85")
SEVERITY_WEIGHTS = {
    "PENDING_NEAR_TIMEOUT": 2,
    "MISSING_RECEIPT": 4,
    "DISPUTED_RECEIPT": 3,
    "CYCLE_LOCKED": 5,
}

# Global kill switch
SYSTEM_ALLOCATION_ENABLED = os.getenv("SYSTEM_ALLOCATION_ENABLED", "true").lower() == "true"


# ============================================================================
# INTERNAL → API STATE MAPPING
# ============================================================================

MILL_STATE_API_MAP: dict[str, str] = {
    "VERIFIED": "VERIFIED",
    "UNDER_REVIEW": "UNDER_REVIEW",
    "COMPROMISED": "COMPROMISED",
    "SUSPENDED": "SUSPENDED",
    "DISPUTED": "UNDER_REVIEW",
    "MISSING": "COMPROMISED",
    "LOCKED": "SUSPENDED",
}


def _map_mill_state(internal_state: str) -> str:
    return MILL_STATE_API_MAP.get(internal_state, "UNDER_REVIEW")


# ============================================================================
# DATABASE DEPENDENCY & LOCKING
# ============================================================================

def get_session():
    with Session(engine) as session:
        yield session


@contextmanager
def get_locked_mill(mill_id: str, session: Session):
    """Row‑level lock on the Mill row for the duration of the transaction."""
    with session.begin():
        mill = session.exec(
            select(Mill).where(Mill.id == mill_id).with_for_update()
        ).first()
        if not mill:
            raise HTTPException(status_code=404, detail=f"Mill '{mill_id}' not found.")
        yield mill


# ============================================================================
# AUTH DEPENDENCY
# ============================================================================

def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    expected = os.environ.get("OWNER_API_KEY")
    if not expected:
        raise HTTPException(
            status_code=500,
            detail="Server misconfiguration: OWNER_API_KEY not set.",
        )
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
    return x_api_key


# ============================================================================
# RESPONSE MODELS (monetary = Decimal, non‑financial = float)
# ============================================================================

class PortfolioRisk(BaseModel):
    worst_10_percent_adherence: float
    top_3_failing_nodes: List[Dict[str, Any]]
    adherence_variance: float


class MillSummary(BaseModel):
    mill_id: str
    name: str
    location: str
    revenue_rate_per_kwh: Optional[Decimal]
    current_status: str
    glass_box_certified: bool


class PortfolioResponse(BaseModel):
    mills: List[MillSummary]
    portfolio_risk: PortfolioRisk


class MillStatusResponse(BaseModel):
    mill_id: str
    current_cycle_status: Optional[str]
    cycle_elapsed_hours: Optional[float]
    last_cycle_adherence: float
    last_cycle_lag_hours: float
    trust_score: float
    glass_box_certified: bool
    next_advance_rate: float
    outstanding_balance: Optional[Decimal]


class CycleSummary(BaseModel):
    cycle_id: int
    allocated_at: datetime
    allocated_kwh: Decimal
    expected_revenue: Decimal
    actual_cash: Optional[Decimal]
    adherence: Optional[float]
    lag_hours: Optional[float]
    status: str


class GlassBoxResponse(BaseModel):
    mill_id: str
    certified: bool
    certified_since: Optional[str]
    reason: Optional[str]
    criteria: dict
    evaluated_at: str


class DecisionBasis(BaseModel):
    cycle_state: str
    cycle_elapsed_hours: Optional[float]
    trust_score: float
    last_cycle_adherence: float
    last_cycle_lag_hours: float
    next_advance_rate: float
    capital_at_risk: Decimal
    time_weighted_risk: Decimal  # capital_at_risk adjusted for overdue age
    time_to_missing_hours: Optional[float]
    time_to_lock_hours: Optional[float]
    simulated_allocation_kwh: Decimal
    simulated_expected_revenue: Decimal
    exposure_used: Decimal
    exposure_limit: Decimal
    effective_rate_per_kwh: Optional[Decimal] = None  # NEW: actual_cash / allocated_kwh from latest cycle


class AllocationDecisionResponse(BaseModel):
    allowed: bool
    reason: Optional[str]
    allocation_id: Optional[int] = None
    allocated_kwh: Decimal = Decimal(0)
    expected_revenue: Decimal = Decimal(0)
    decision_basis: DecisionBasis


class DecisionFeedItem(BaseModel):
    mill_id: str
    name: str
    issue: str
    detail: str
    urgency: str
    priority_score: float   # non‑financial, log‑linear hybrid
    capital_at_risk: Decimal
    time_to_action_hours: float
    recommended_action: str


# ============================================================================
# TIMEZONE NORMALIZATION (Explicit, never assumed)
# ============================================================================

def _to_utc(dt: datetime) -> datetime:
    """Convert any datetime to UTC. Naive -> UTC, aware -> convert."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ============================================================================
# TRUST SCORE (Recency‑weighted, uses MAD for stability)
# ============================================================================

def _compute_trust_score(mill_id: str, session: Session) -> float:
    """
    Deterministic trust score (0–100). Recency‑weighted, prefetches receipts.
    """
    # 1. Adherence (last cycle)
    adherence = get_last_cycle_adherence(mill_id, session)

    # 2. Recency‑weighted consistency over last 5 cycles
    cycles = session.exec(
        select(TokenAllocation)
        .where(TokenAllocation.mill_id == mill_id)
        .order_by(TokenAllocation.allocated_at.desc())
    ).fetchmany(5)

    consistency = 1.0
    if len(cycles) >= 2:
        # Prefetch all receipts for these cycles in one query
        alloc_ids = [c.id for c in cycles]
        receipts = session.exec(
            select(CashReceipt).where(CashReceipt.allocation_id.in_(alloc_ids))
        ).all()
        receipt_map = {r.allocation_id: r for r in receipts}

        adhs = []
        for c in cycles:
            r = receipt_map.get(c.id)
            if r and c.expected_revenue:
                adhs.append(float(min(1.0, r.amount / c.expected_revenue)))
        if len(adhs) >= 2:
            # Exponential decay weights (most recent highest)
            weights = [0.5, 0.25, 0.125, 0.0625, 0.0625][:len(adhs)]
            weights = [w / sum(weights) for w in weights]
            weighted_mean = sum(a * w for a, w in zip(adhs, weights))
            weighted_mad = sum(abs(a - weighted_mean) * w for a, w in zip(adhs, weights))
            consistency = max(0.0, 1.0 - min(1.0, weighted_mad))

    # 3. Missing ratio (maturity‑weighted)
    all_cycles = session.exec(
        select(TokenAllocation)
        .where(TokenAllocation.mill_id == mill_id)
        .order_by(TokenAllocation.allocated_at.desc())
    ).fetchmany(20)
    total = len(all_cycles)
    if total == 0:
        missing_ratio_weighted = 0.0
    else:
        missing_count = sum(1 for a in all_cycles if a.status == "MISSING")
        raw_ratio = missing_count / total
        maturity = min(1.0, total / 5.0)
        missing_ratio_weighted = raw_ratio * maturity

    raw = 0.6 * adherence + 0.2 * consistency + 0.2 * (1.0 - missing_ratio_weighted)
    return round(max(0.0, min(1.0, raw)) * 100, 2)


def _require_trust_score(mill_id: str, session: Session) -> float:
    try:
        return _compute_trust_score(mill_id, session)
    except Exception as exc:
        logger.error(f"Trust score computation failed for mill {mill_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Trust score unavailable for mill '{mill_id}'. System integrity check required.",
        )


# ============================================================================
# CYCLE STATE (Atomic, timezone‑safe)
# ============================================================================

def _get_cycle_state_and_elapsed(
    mill_id: str, session: Session
) -> tuple[str, Optional[float]]:
    latest = session.exec(
        select(TokenAllocation)
        .where(TokenAllocation.mill_id == mill_id)
        .order_by(TokenAllocation.allocated_at.desc())
    ).first()

    if not latest or latest.status == "CLOSED":
        return "IDLE", None

    now_utc = datetime.now(timezone.utc)
    allocated_utc = _to_utc(latest.allocated_at)
    elapsed = round((now_utc - allocated_utc).total_seconds() / 3600.0, 2)

    if latest.status == "DISPUTED":
        return "DISPUTED", elapsed
    if latest.status == "MISSING":
        return "MISSING", elapsed
    if latest.status == "PENDING":
        if elapsed >= LOCKED_CYCLE_HOURS:
            return "LOCKED", elapsed
        return "PENDING", elapsed

    logger.warning(f"Unknown allocation status '{latest.status}' for mill {mill_id}")
    return "PENDING", elapsed


def _get_outstanding_exposure(mill_id: str, session: Session) -> Decimal:
    """
    Financial exposure: sum of (expected_revenue - actual_cash) over all cycles
    that are not fully settled. Uses a single SQL query.
    """
    stmt = select(
        func.sum(
            TokenAllocation.expected_revenue - func.coalesce(CashReceipt.amount, 0)
        )
    ).outerjoin(
        CashReceipt, CashReceipt.allocation_id == TokenAllocation.id
    ).where(
        TokenAllocation.mill_id == mill_id
    )
    result = session.exec(stmt).first()
    return Decimal(result or 0)


def _time_weighted_risk(exposure: Decimal, overdue_days: float) -> Decimal:
    """
    Apply a linear decay multiplier to exposure based on overdue days.
    Multiplier = 1 + 0.1 * overdue_days, capped at 2.0.
    
    This makes delayed allocations (unanswered receipts) progressively more expensive,
    discouraging the operator from stalling on payment.
    
    Args:
        exposure: Base capital at risk (MWK)
        overdue_days: Days since allocation without receipt
    
    Returns:
        Time-weighted exposure (exposure * multiplier)
    """
    if overdue_days <= 0:
        return exposure
    multiplier = min(2.0, 1.0 + 0.1 * overdue_days)
    return exposure * Decimal(str(multiplier))


def _compute_capital_at_risk(
    mill_id: str, cycle_state: str, session: Session
) -> tuple[Decimal, Decimal]:
    """
    Returns (capital_at_risk, time_weighted_risk).
    
    capital_at_risk: Raw shortfall (expected_revenue - actual_receipt)
    time_weighted_risk: capital_at_risk * (1 + 0.1 * overdue_days), capped at 2x
    
    Args:
        mill_id: Mill identifier
        cycle_state: Current cycle status (IDLE, PENDING, MISSING, DISPUTED)
        session: Database session
    
    Returns:
        Tuple of (raw_risk, time_weighted_risk)
    """
    if cycle_state == "IDLE":
        return Decimal(0), Decimal(0)

    latest = session.exec(
        select(TokenAllocation)
        .where(TokenAllocation.mill_id == mill_id)
        .order_by(TokenAllocation.allocated_at.desc())
    ).first()
    if not latest:
        return Decimal(0), Decimal(0)

    receipt = session.exec(
        select(CashReceipt).where(CashReceipt.allocation_id == latest.id)
    ).first()
    actual = receipt.amount if receipt else Decimal(0)
    raw_risk = max(Decimal(0), latest.expected_revenue - actual)

    # Overdue days = time since allocation (if no receipt received yet)
    now_utc = datetime.now(timezone.utc)
    allocated_utc = _to_utc(latest.allocated_at)
    overdue_days = max(0.0, (now_utc - allocated_utc).total_seconds() / 86400.0)

    time_weighted = _time_weighted_risk(raw_risk, overdue_days)
    return raw_risk, time_weighted



def _compute_allocation_size(
    mill: Mill,
    trust_score: float,
    adherence: float,
    lag_hours: float,
) -> Decimal:
    """
    Single source of truth for allocation sizing.
    Used by both the read‑only decision endpoint and the actual allocation.
    Returns Decimal kWh.
    """
    advance_rate = compute_per_cycle_advance_rate(
        trust_score=trust_score,
        adherence=adherence,
        lag_hours=lag_hours,
    )
    return BASE_CYCLE_KWH * Decimal(advance_rate)


def _compute_effective_rate_per_kwh(mill_id: str, session: Session) -> Optional[Decimal]:
    """
    Compute effective revenue per kWh from the latest allocation.
    
    Formula: effective_rate_per_kwh = actual_cash_received / allocated_kwh
    
    This metric reveals operator bucket mix and pricing strategy:
    - Within band (1,100–1,500 MWK/kWh): normal variation (bucket mix)
    - Consistently below band: possible under-reporting or excessive small buckets
    - Above band: possible premium pricing or over-reporting
    
    Note: Band (1,100–1,500) is calibrated from Nabiwi Q1 2026 data.
    Adjust per-mill as you collect forensic film ground truth.
    
    Args:
        mill_id: Mill identifier
        session: Database session
    
    Returns:
        Effective rate (MWK/kWh) or None if insufficient data
    """
    latest = session.exec(
        select(TokenAllocation)
        .where(TokenAllocation.mill_id == mill_id)
        .order_by(TokenAllocation.allocated_at.desc())
    ).first()
    
    if not latest or latest.allocated_kwh <= 0:
        return None
    
    receipt = session.exec(
        select(CashReceipt).where(CashReceipt.allocation_id == latest.id)
    ).first()
    
    if not receipt or receipt.amount <= 0:
        return None
    
    effective_rate = receipt.amount / latest.allocated_kwh
    return effective_rate.quantize(Decimal("0.01"))  # Round to 0.01 MWK/kWh


def _build_decision_basis(
    mill_id: str,
    cycle_state: str,
    elapsed_hours: Optional[float],
    trust_score: float,
    adherence: float,
    lag_hours: float,
    capital_at_risk: Decimal,
    time_weighted_risk: Decimal,
    exposure_used: Decimal,
    exposure_limit: Decimal,
    session: Session,
) -> DecisionBasis:
    mill = session.exec(select(Mill).where(Mill.id == mill_id)).first()
    simulated_allowed = (cycle_state == "IDLE") and (exposure_used < exposure_limit)
    simulated_kwh = _compute_allocation_size(mill, trust_score, adherence, lag_hours) if simulated_allowed else Decimal(0)
    simulated_revenue = simulated_kwh * Decimal(str(mill.revenue_rate_per_kwh)) if mill and mill.revenue_rate_per_kwh else Decimal(0)

    next_advance_rate = compute_per_cycle_advance_rate(
        trust_score=trust_score,
        adherence=adherence,
        lag_hours=lag_hours,
    )
    assert 0.0 <= next_advance_rate <= 1.0

    time_to_missing = None
    time_to_lock = None
    if cycle_state == "PENDING" and elapsed_hours is not None:
        time_to_missing = round(max(0.0, MISSING_CYCLE_TIMEOUT_HOURS - elapsed_hours), 2)
        time_to_lock = round(max(0.0, LOCKED_CYCLE_HOURS - elapsed_hours), 2)
    elif cycle_state == "MISSING" and elapsed_hours is not None:
        time_to_lock = round(max(0.0, LOCKED_CYCLE_HOURS - elapsed_hours), 2)

    # Compute effective rate from most recent allocation + receipt (forensic metric)
    effective_rate = _compute_effective_rate_per_kwh(mill_id, session)

    return DecisionBasis(
        cycle_state=cycle_state,
        cycle_elapsed_hours=elapsed_hours,
        trust_score=trust_score,
        last_cycle_adherence=round(adherence, 4),
        last_cycle_lag_hours=round(lag_hours, 2),
        next_advance_rate=round(next_advance_rate, 4),
        capital_at_risk=capital_at_risk,
        time_weighted_risk=time_weighted_risk,
        time_to_missing_hours=time_to_missing,
        time_to_lock_hours=time_to_lock,
        simulated_allocation_kwh=simulated_kwh,
        simulated_expected_revenue=simulated_revenue,
        exposure_used=exposure_used,
        exposure_limit=exposure_limit,
        effective_rate_per_kwh=effective_rate,
    )


def _store_decision_audit(
    mill_id: str,
    allowed: bool,
    reason: Optional[str],
    decision_basis: DecisionBasis,
    session: Session,
    allocation_id: Optional[int] = None,
) -> None:
    """Persist decision audit record. Caller is responsible for transaction commit."""
    audit = DecisionAudit(
        mill_id=mill_id,
        timestamp=datetime.now(timezone.utc),
        allowed=allowed,
        reason=reason,
        decision_basis_json=decision_basis.model_dump_json(),
        allocation_id=allocation_id,
    )
    session.add(audit)
    # No commit – outer transaction will commit



def _get_mill_state(mill_id: str, session: Session) -> str:
    state_row = session.exec(
        select(MillIntegrityState).where(MillIntegrityState.mill_id == mill_id)
    ).first()
    internal = state_row.state if state_row else "VERIFIED"
    return _map_mill_state(internal)


def _get_mill_or_404(mill_id: str, session: Session) -> Mill:
    mill = session.exec(select(Mill).where(Mill.id == mill_id)).first()
    if not mill:
        raise HTTPException(status_code=404, detail=f"Mill '{mill_id}' not found.")
    return mill


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/mills", response_model=PortfolioResponse)
def list_mills(
    session: Session = Depends(get_session),
    _: str = Depends(verify_api_key),
):
    mills = session.exec(select(Mill)).all()
    for mill in mills:
        _require_trust_score(mill.id, session)  # pre‑flight only

    mill_summaries = [
        MillSummary(
            mill_id=mill.id,
            name=mill.name,
            location=mill.location,
            revenue_rate_per_kwh=mill.revenue_rate_per_kwh,
            current_status=_get_mill_state(mill.id, session),
            glass_box_certified=mill.glass_box_certified,
        )
        for mill in mills
    ]

    # Risk dispersion
    adherence_by_mill = []
    for mill in mills:
        adherence_by_mill.append((mill.id, get_last_cycle_adherence(mill.id, session)))
    adherences = [a for _, a in adherence_by_mill]
    if not adherences:
        portfolio_risk = PortfolioRisk(
            worst_10_percent_adherence=0.0,
            top_3_failing_nodes=[],
            adherence_variance=0.0,
        )
    else:
        sorted_pairs = sorted(adherence_by_mill, key=lambda x: x[1])
        worst_n = max(1, len(sorted_pairs) // 10)
        worst_10_avg = round(sum(a for _, a in sorted_pairs[:worst_n]) / worst_n, 4)
        top_3_failing = [
            {"mill_id": mid, "adherence": round(a, 4)} for mid, a in sorted_pairs[:3]
        ]
        variance = round(statistics.variance(adherences) if len(adherences) > 1 else 0.0, 6)
        portfolio_risk = PortfolioRisk(
            worst_10_percent_adherence=worst_10_avg,
            top_3_failing_nodes=top_3_failing,
            adherence_variance=variance,
        )
    return PortfolioResponse(mills=mill_summaries, portfolio_risk=portfolio_risk)


@router.get("/mills/{mill_id}/status", response_model=MillStatusResponse)
def get_mill_status(
    mill_id: str,
    session: Session = Depends(get_session),
    _: str = Depends(verify_api_key),
):
    mill = _get_mill_or_404(mill_id, session)
    trust_score = _require_trust_score(mill_id, session)

    cycle_state, elapsed = _get_cycle_state_and_elapsed(mill_id, session)
    current_cycle_status = None if cycle_state == "IDLE" else cycle_state

    adherence = get_last_cycle_adherence(mill_id, session)
    lag_hours = get_last_cycle_lag(mill_id, session)
    next_advance_rate = compute_per_cycle_advance_rate(
        trust_score=trust_score,
        adherence=adherence,
        lag_hours=lag_hours,
    )
    return MillStatusResponse(
        mill_id=mill_id,
        current_cycle_status=current_cycle_status,
        cycle_elapsed_hours=elapsed,
        last_cycle_adherence=round(adherence, 4),
        last_cycle_lag_hours=round(lag_hours, 2),
        trust_score=trust_score,
        glass_box_certified=mill.glass_box_certified,
        next_advance_rate=round(next_advance_rate, 4),
        outstanding_balance=_get_outstanding_exposure(mill_id, session),
    )


@router.get("/mills/{mill_id}/cycles", response_model=List[CycleSummary])
def get_mill_cycles(
    mill_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
    _: str = Depends(verify_api_key),
):
    _get_mill_or_404(mill_id, session)
    # Prefetch receipts to avoid N+1
    allocations = session.exec(
        select(TokenAllocation)
        .where(TokenAllocation.mill_id == mill_id)
        .order_by(TokenAllocation.allocated_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    alloc_ids = [a.id for a in allocations]
    receipts = {}
    if alloc_ids:
        rows = session.exec(
            select(CashReceipt).where(CashReceipt.allocation_id.in_(alloc_ids))
        ).all()
        receipts = {r.allocation_id: r for r in rows}
    result = []
    for alloc in allocations:
        receipt = receipts.get(alloc.id)
        actual_cash = receipt.amount if receipt else None
        adherence = None
        lag_hours = None
        if receipt and alloc.expected_revenue:
            adherence = round(min(1.0, max(0.0, receipt.amount / alloc.expected_revenue)), 4)
            lag_hours = round(
                (receipt.received_at - alloc.allocated_at).total_seconds() / 3600.0, 2
            )
        result.append(
            CycleSummary(
                cycle_id=alloc.id,
                allocated_at=alloc.allocated_at,
                allocated_kwh=alloc.allocated_kwh,
                expected_revenue=alloc.expected_revenue,
                actual_cash=actual_cash,
                adherence=adherence,
                lag_hours=lag_hours,
                status=alloc.status,
            )
        )
    return result


@router.get("/mills/{mill_id}/glass-box", response_model=GlassBoxResponse)
def get_glass_box_endpoint(
    mill_id: str,
    session: Session = Depends(get_session),
    _: str = Depends(verify_api_key),
):
    _get_mill_or_404(mill_id, session)
    result = get_certification_status(mill_id, session)
    certified_since = None
    if result["certified"]:
        try:
            earliest_clean = session.exec(
                select(TokenAllocation)
                .where(
                    TokenAllocation.mill_id == mill_id,
                    TokenAllocation.status == "CLOSED",
                )
                .order_by(TokenAllocation.allocated_at.asc())
            ).fetchmany(10)
            if earliest_clean:
                certified_since = earliest_clean[0].allocated_at.date().isoformat()
        except Exception:
            pass
    return GlassBoxResponse(
        mill_id=mill_id,
        certified=result["certified"],
        certified_since=certified_since,
        reason=result.get("reason"),
        criteria=result["criteria"],
        evaluated_at=result["evaluated_at"],
    )


@router.get("/mills/{mill_id}/decision", response_model=AllocationDecisionResponse)
def get_mill_decision(
    mill_id: str,
    session: Session = Depends(get_session),
    _: str = Depends(verify_api_key),
):
    """
    Read‑only decision brain. Simulates allocation outcome without executing it.
    Uses the same allocation size logic as the real endpoint.
    """
    mill = _get_mill_or_404(mill_id, session)
    if not mill.revenue_rate_per_kwh:
        raise HTTPException(400, f"Mill '{mill_id}' has no revenue rate configured.")

    trust_score = _require_trust_score(mill_id, session)
    cycle_state, elapsed = _get_cycle_state_and_elapsed(mill_id, session)
    adherence = get_last_cycle_adherence(mill_id, session)
    lag_hours = get_last_cycle_lag(mill_id, session)
    capital_at_risk, time_weighted_risk = _compute_capital_at_risk(mill_id, cycle_state, session)
    exposure_used = _get_outstanding_exposure(mill_id, session)

    allowed = (cycle_state == "IDLE") and (exposure_used < MAX_EXPOSURE_PER_MILL)
    reason = None
    if cycle_state != "IDLE":
        reason = f"BLOCKED_{cycle_state}"
    elif exposure_used >= MAX_EXPOSURE_PER_MILL:
        reason = "BLOCKED_EXPOSURE_LIMIT"

    basis = _build_decision_basis(
        mill_id=mill_id,
        cycle_state=cycle_state,
        elapsed_hours=elapsed,
        trust_score=trust_score,
        adherence=adherence,
        lag_hours=lag_hours,
        capital_at_risk=capital_at_risk,
        time_weighted_risk=time_weighted_risk,
        exposure_used=exposure_used,
        exposure_limit=MAX_EXPOSURE_PER_MILL,
        session=session,
    )

    return AllocationDecisionResponse(
        allowed=allowed,
        reason=reason,
        decision_basis=basis,
    )


@router.post("/mills/{mill_id}/allocate-token", response_model=AllocationDecisionResponse)
def allocate_token(
    mill_id: str,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    session: Session = Depends(get_session),
    _: str = Depends(verify_api_key),
):
    # --- IDEMPOTENCY CHECK (FIRST) ---
    now_utc = datetime.now(timezone.utc)
    existing = session.exec(
        select(IdempotencyRecord).where(
            IdempotencyRecord.idempotency_key == idempotency_key,
            IdempotencyRecord.mill_id == mill_id,
            IdempotencyRecord.expires_at > now_utc,
        )
    ).first()
    if existing:
        # Return the stored response – no new allocation
        return AllocationDecisionResponse.model_validate_json(existing.response_json)

    # --- GLOBAL KILL SWITCH ---
    if not SYSTEM_ALLOCATION_ENABLED:
        raise HTTPException(status_code=503, detail="System allocation disabled by operator.")

    with get_locked_mill(mill_id, session) as mill:
        # Pre‑checks that don't require a lock repeat
        if not mill.revenue_rate_per_kwh:
            raise HTTPException(400, f"Mill '{mill_id}' has no revenue rate configured.")

        # Re‑check active cycle under the same row lock
        active_cycle = session.exec(
            select(TokenAllocation)
            .where(
                TokenAllocation.mill_id == mill_id,
                TokenAllocation.status.in_(["PENDING", "MISSING", "DISPUTED"])
            )
            .with_for_update()
        ).first()
        if active_cycle:
            cycle_state = active_cycle.status
            # Build decision basis (reuse helper)
            trust_score = _require_trust_score(mill_id, session)
            cycle_state_str, elapsed = _get_cycle_state_and_elapsed(mill_id, session)
            adherence = get_last_cycle_adherence(mill_id, session)
            lag_hours = get_last_cycle_lag(mill_id, session)
            capital_at_risk, time_weighted_risk = _compute_capital_at_risk(mill_id, cycle_state_str, session)
            exposure_used = _get_outstanding_exposure(mill_id, session)
            basis = _build_decision_basis(
                mill_id=mill_id,
                cycle_state=cycle_state_str,
                elapsed_hours=elapsed,
                trust_score=trust_score,
                adherence=adherence,
                lag_hours=lag_hours,
                capital_at_risk=capital_at_risk,
                time_weighted_risk=time_weighted_risk,
                exposure_used=exposure_used,
                exposure_limit=MAX_EXPOSURE_PER_MILL,
                session=session,
            )
            # Store audit in same transaction (no commit yet)
            _store_decision_audit(mill_id, False, f"BLOCKED_{cycle_state_str}", basis, session)
            # Roll back? No, we are inside a transaction that will be committed or rolled back by outer block.
            # Return the blocked response – note that the transaction will still be committed (audit stored).
            # To avoid storing audit on a blocked request, we can rollback, but it's fine to record blocked attempts.
            return AllocationDecisionResponse(
                allowed=False,
                reason=f"BLOCKED_{cycle_state_str}",
                decision_basis=basis,
            )

        # No active cycle – proceed with normal decision flow
        trust_score = _require_trust_score(mill_id, session)
        cycle_state, elapsed = _get_cycle_state_and_elapsed(mill_id, session)
        adherence = get_last_cycle_adherence(mill_id, session)
        lag_hours = get_last_cycle_lag(mill_id, session)
        capital_at_risk, time_weighted_risk = _compute_capital_at_risk(mill_id, cycle_state, session)
        exposure_used = _get_outstanding_exposure(mill_id, session)

        allowed = (cycle_state == "IDLE") and (exposure_used < MAX_EXPOSURE_PER_MILL)
        reason = None
        if cycle_state != "IDLE":
            reason = f"BLOCKED_{cycle_state}"
        elif exposure_used >= MAX_EXPOSURE_PER_MILL:
            reason = "BLOCKED_EXPOSURE_LIMIT"

        # Compute allocation size using shared function
        allocated_kwh = _compute_allocation_size(mill, trust_score, adherence, lag_hours) if allowed else Decimal(0)
        expected_revenue = allocated_kwh * mill.revenue_rate_per_kwh if allowed else Decimal(0)

        basis = _build_decision_basis(
            mill_id=mill_id,
            cycle_state=cycle_state,
            elapsed_hours=elapsed,
            trust_score=trust_score,
            adherence=adherence,
            lag_hours=lag_hours,
            capital_at_risk=capital_at_risk,
            time_weighted_risk=time_weighted_risk,
            exposure_used=exposure_used,
            exposure_limit=MAX_EXPOSURE_PER_MILL,
            session=session,
        )

        if not allowed:
            _store_decision_audit(mill_id, False, reason, basis, session)
            return AllocationDecisionResponse(
                allowed=False,
                reason=reason,
                decision_basis=basis,
            )

        # Execute allocation
        try:
            gateway = TokenGateway(session)
            result = gateway.allocate_token(
                mill_id=mill_id,
                allocated_kwh=allocated_kwh,
                expected_revenue=expected_revenue,
            )
        except AllocationError as exc:
            _store_decision_audit(mill_id, False, exc.code, basis, session)
            raise HTTPException(
                status_code=400,
                detail={
                    "allowed": False,
                    "reason": exc.code,
                    "decision_basis": basis.model_dump(),
                },
            )
        except Exception as exc:
            logger.error(f"Unexpected error allocating token for mill {mill_id}: {exc}", exc_info=True)
            _store_decision_audit(mill_id, False, "INTERNAL_ERROR", basis, session)
            raise HTTPException(status_code=500, detail="Internal error during token allocation.")

        # Success – store audit and commit (transaction commits at end of `with` block)
        _store_decision_audit(mill_id, True, None, basis, session, allocation_id=result["allocation_id"])
        
        # Build the response
        response = AllocationDecisionResponse(
            allowed=True,
            reason=None,
            allocation_id=result["allocation_id"],
            allocated_kwh=result["allocated_kwh"],
            expected_revenue=result["expected_revenue"],
            decision_basis=basis,
        )
        
        # Store the idempotency record (valid for 24 hours)
        expires_at = now_utc + timedelta(hours=24)
        record = IdempotencyRecord(
            idempotency_key=idempotency_key,
            mill_id=mill_id,
            response_json=response.model_dump_json(),
            allocation_id=response.allocation_id,
            expires_at=expires_at,
        )
        session.add(record)
        # No explicit commit needed – transaction commits at end of `with` block
        
        return response


@router.get("/decision-feed", response_model=List[DecisionFeedItem])
def get_decision_feed(
    session: Session = Depends(get_session),
    _: str = Depends(verify_api_key),
):
    """
    Actionable feed sorted by hybrid log‑linear economic impact.
    Filters out low‑value noise.
    """
    mills = session.exec(select(Mill)).all()
    feed: List[DecisionFeedItem] = []

    for mill in mills:
        cycle_state, elapsed = _get_cycle_state_and_elapsed(mill.id, session)
        if cycle_state == "IDLE":
            continue

        capital_at_risk, time_weighted_risk = _compute_capital_at_risk(mill.id, cycle_state, session)
        if capital_at_risk < MIN_CAPITAL_AT_RISK_FOR_FEED:
            continue

        elapsed_h = elapsed or 0.0
        if cycle_state == "PENDING":
            remaining = max(0.0, MISSING_CYCLE_TIMEOUT_HOURS - elapsed_h)
            if remaining > MISSING_CYCLE_TIMEOUT_HOURS * 0.5:
                continue
            issue = "PENDING_NEAR_TIMEOUT"
            urgency = "HIGH" if remaining < 12 else "MEDIUM"
            # Hybrid priority: log component + linear component for extreme values
            # Use time_weighted_risk for priority to penalize stale allocations
            log_comp = math.log1p(float(time_weighted_risk))
            linear_comp = float(time_weighted_risk) / 1_000_000.0  # scale extreme values
            priority = (log_comp * 0.7) + (linear_comp * 0.3)
            priority *= SEVERITY_WEIGHTS[issue]
            feed.append(
                DecisionFeedItem(
                    mill_id=mill.id,
                    name=mill.name,
                    issue=issue,
                    detail=f"Cycle open {elapsed_h:.1f}h. Receipt due within {remaining:.1f}h.",
                    urgency=urgency,
                    priority_score=priority,
                    capital_at_risk=capital_at_risk,
                    time_to_action_hours=round(remaining, 2),
                    recommended_action="Contact operator to confirm cash remittance.",
                )
            )
        elif cycle_state == "MISSING":
            remaining_to_lock = max(0.0, LOCKED_CYCLE_HOURS - elapsed_h)
            issue = "MISSING_RECEIPT"
            urgency = "HIGH"
            # Use time_weighted_risk for priority
            log_comp = math.log1p(float(time_weighted_risk))
            linear_comp = float(time_weighted_risk) / 1_000_000.0
            priority = (log_comp * 0.7) + (linear_comp * 0.3)
            priority *= SEVERITY_WEIGHTS[issue]
            feed.append(
                DecisionFeedItem(
                    mill_id=mill.id,
                    name=mill.name,
                    issue=issue,
                    detail=f"No receipt after {elapsed_h:.1f}h. {remaining_to_lock:.1f}h until LOCKED. MK {capital_at_risk:,.0f} at risk.",
                    urgency=urgency,
                    priority_score=priority,
                    capital_at_risk=capital_at_risk,
                    time_to_action_hours=round(remaining_to_lock, 2),
                    recommended_action="Dispatch field agent. Verify cash position.",
                )
            )
        elif cycle_state == "LOCKED":
            issue = "CYCLE_LOCKED"
            urgency = "CRITICAL"
            # Use time_weighted_risk for priority
            log_comp = math.log1p(float(time_weighted_risk))
            linear_comp = float(time_weighted_risk) / 1_000_000.0
            priority = (log_comp * 0.7) + (linear_comp * 0.3)
            priority *= SEVERITY_WEIGHTS[issue]
            feed.append(
                DecisionFeedItem(
                    mill_id=mill.id,
                    name=mill.name,
                    issue=issue,
                    detail=f"Cycle locked after {elapsed_h:.1f}h. MK {capital_at_risk:,.0f} at risk.",
                    urgency=urgency,
                    priority_score=priority,
                    capital_at_risk=capital_at_risk,
                    time_to_action_hours=0.0,
                    recommended_action="Escalate to manager. Resolve dispute before next cycle.",
                )
            )
        elif cycle_state == "DISPUTED":
            remaining_to_lock = max(0.0, LOCKED_CYCLE_HOURS - elapsed_h)
            issue = "DISPUTED_RECEIPT"
            urgency = "MEDIUM"
            log_comp = math.log1p(float(capital_at_risk))
            linear_comp = float(capital_at_risk) / 1_000_000.0
            priority = (log_comp * 0.7) + (linear_comp * 0.3)
            priority *= SEVERITY_WEIGHTS[issue]
            feed.append(
                DecisionFeedItem(
                    mill_id=mill.id,
                    name=mill.name,
                    issue=issue,
                    detail=f"Receipt variance outside tolerance. MK {capital_at_risk:,.0f} variance unresolved.",
                    urgency=urgency,
                    priority_score=priority,
                    capital_at_risk=capital_at_risk,
                    time_to_action_hours=round(remaining_to_lock, 2),
                    recommended_action="Review receipt variance. Confirm or dispute with operator.",
                )
            )

    feed.sort(key=lambda x: -x.priority_score)
    return feed