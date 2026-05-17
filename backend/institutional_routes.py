"""
Institutional Governance Routes – GL-1 Mandate Logging & Audit Trail API
GridLedger Protocol GL-1 implementation

Endpoints for:
- Mandate submission & acknowledgment
- Friction analytics recording
- Discrepancy report submission
- Enforcement action logging
- Audit trail retrieval
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlmodel import Session, select
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel
import os
import logging

# Import get_session from owner_routes (centralized session management)
# This avoids circular imports and reuses existing DB configuration
from sqlmodel import Session as SQLModelSession
from scripts.init_db import engine

from backend.institutional_models import (
    MandateSubmission,
    FrictionAnalytics,
    DiscrepancyReport,
    EnforcementAction,
)

# Define get_session locally using the engine from init_db
def get_session():
    with SQLModelSession(engine) as session:
        yield session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/institutional", tags=["institutional"])

API_KEY = os.getenv('GRIDLEDGER_API_KEY')
if not API_KEY:
    raise RuntimeError('GRIDLEDGER_API_KEY environment variable is required. See .env.example.')

def verify_api_key(x_api_key: Optional[str] = Header(None)) -> bool:
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail='Invalid API Key')
    return True


# ============================================================================
# Pydantic Models (Request/Response)
# ============================================================================

class MandateSubmissionCreate(BaseModel):
    mandate_id: str
    submitted_by: str
    role: str
    mandate_version_hash: str
    acknowledgment_type: str
    session_id: str
    # GL-1 INSTITUTIONAL ACCOUNTABILITY FIELDS (6-field requirement)
    institution_name: str  # NBM, RBM, SPARC, etc.
    authorisation_level: str  # OPERATOR, MANAGER, DIRECTOR, EXECUTIVE
    capital_range: str  # TIER_A, TIER_B, TIER_C, EXEMPT
    mode_viewed: str  # INTERACTIVE, DEMO, REVIEW_ONLY, OFFLINE


class MandateSubmissionResponse(BaseModel):
    mandate_id: str
    status: str
    timestamp: datetime


class FrictionAnalyticsCreate(BaseModel):
    session_id: str
    mandate_id: str
    scroll_depth_pct: float
    time_on_statement_ms: int
    interaction_count: int
    bypass_attempted: bool = False


class DiscrepancyReportCreate(BaseModel):
    event_id: str
    mill_id: str
    reported_by: str
    reason: str
    details: Optional[str] = None


class DiscrepancyReportResponse(BaseModel):
    id: int
    event_id: str
    mill_id: str
    status: str
    created_at: datetime


class EnforcementActionCreate(BaseModel):
    mill_id: str
    cycle_id: Optional[int] = None
    action_type: str
    initiated_by: str
    reason: str


class EnforcementActionResponse(BaseModel):
    id: int
    mill_id: str
    action_type: str
    timestamp: datetime


# ============================================================================
# Mandate Submission Endpoints
# ============================================================================

@router.post("/mandate-submission", response_model=MandateSubmissionResponse)
def create_mandate_submission(
    payload: MandateSubmissionCreate,
    session: Session = Depends(get_session),
    _: bool = Depends(verify_api_key)
):
    """
    Record an institutional mandate submission.
    
    Idempotent: if mandate_id already exists, returns existing record.
    """
    statement = select(MandateSubmission).where(
        MandateSubmission.mandate_id == payload.mandate_id
    )
    existing = session.exec(statement).first()
    
    if existing:
        return MandateSubmissionResponse(
            mandate_id=existing.mandate_id,
            status=existing.status,
            timestamp=existing.timestamp
        )
    
    submission = MandateSubmission(
        mandate_id=payload.mandate_id,
        submitted_by=payload.submitted_by,
        role=payload.role,
        mandate_version_hash=payload.mandate_version_hash,
        acknowledgment_type=payload.acknowledgment_type,
        session_id=payload.session_id,
        institution_name=payload.institution_name,
        authorisation_level=payload.authorisation_level,
        capital_range=payload.capital_range,
        mode_viewed=payload.mode_viewed,
        status="ACKNOWLEDGED",
        acknowledged_at=datetime.now(timezone.utc)
    )
    session.add(submission)
    session.commit()
    session.refresh(submission)
    
    logger.info(f"Mandate {payload.mandate_id} submitted by {payload.submitted_by} (role: {payload.role})")
    
    return MandateSubmissionResponse(
        mandate_id=submission.mandate_id,
        status=submission.status,
        timestamp=submission.timestamp
    )


# ============================================================================
# Friction Analytics Endpoints
# ============================================================================

@router.post("/friction-analytics")
def record_friction_analytics(
    payload: FrictionAnalyticsCreate,
    session: Session = Depends(get_session),
    _: bool = Depends(verify_api_key)
):
    """
    Record friction moment engagement metrics.
    
    Immutable record. Multiple records per session_id are allowed.
    """
    analytics = FrictionAnalytics(**payload.dict())
    session.add(analytics)
    session.commit()
    
    bypass_flag = "BYPASS_ATTEMPTED" if payload.bypass_attempted else "NORMAL_FLOW"
    logger.info(
        f"Friction recorded for mandate {payload.mandate_id}: "
        f"scroll={payload.scroll_depth_pct:.0f}%, time={payload.time_on_statement_ms}ms, "
        f"interactions={payload.interaction_count}, {bypass_flag}"
    )
    
    return {"status": "recorded"}


# ============================================================================
# Discrepancy Report Endpoints
# ============================================================================

@router.post("/discrepancy-reports", response_model=DiscrepancyReportResponse)
def create_discrepancy_report(
    payload: DiscrepancyReportCreate,
    session: Session = Depends(get_session),
    _: bool = Depends(verify_api_key)
):
    """
    Submit a discrepancy report linking an event to an anomaly.
    
    Triggers reconciliation workflow. Status: PENDING → REVIEWED → RESOLVED
    """
    report = DiscrepancyReport(**payload.dict())
    session.add(report)
    session.commit()
    session.refresh(report)
    
    logger.warning(
        f"Discrepancy report created: event={payload.event_id}, "
        f"mill={payload.mill_id}, reason={payload.reason}"
    )
    
    return DiscrepancyReportResponse(
        id=report.id,
        event_id=report.event_id,
        mill_id=report.mill_id,
        status=report.status,
        created_at=report.created_at
    )


@router.get("/discrepancy-reports")
def get_discrepancy_reports(
    mill_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
    _: bool = Depends(verify_api_key)
):
    """
    Retrieve discrepancy reports with optional filtering.
    """
    query = select(DiscrepancyReport)
    
    if mill_id:
        query = query.where(DiscrepancyReport.mill_id == mill_id)
    if status:
        query = query.where(DiscrepancyReport.status == status)
    
    reports = session.exec(
        query.order_by(DiscrepancyReport.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    
    return reports


# ============================================================================
# Enforcement Action Endpoints
# ============================================================================

@router.post("/enforcement-actions", response_model=EnforcementActionResponse)
def create_enforcement_action(
    payload: EnforcementActionCreate,
    session: Session = Depends(get_session),
    _: bool = Depends(verify_api_key)
):
    """
    Log an enforcement action (TOKEN_BLOCKED, MANUAL_OVERRIDE, etc.)
    
    Immutable audit trail of all enforcement decisions.
    """
    action = EnforcementAction(**payload.dict())
    session.add(action)
    session.commit()
    session.refresh(action)
    
    logger.warning(
        f"Enforcement action: {payload.action_type} on mill {payload.mill_id}, "
        f"initiated by {payload.initiated_by}, reason: {payload.reason}"
    )
    
    return EnforcementActionResponse(
        id=action.id,
        mill_id=action.mill_id,
        action_type=action.action_type,
        timestamp=action.timestamp
    )


@router.get("/enforcement-actions")
def get_enforcement_actions(
    mill_id: Optional[str] = None,
    action_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
    _: bool = Depends(verify_api_key)
):
    """
    Retrieve enforcement actions with optional filtering.
    """
    query = select(EnforcementAction)
    
    if mill_id:
        query = query.where(EnforcementAction.mill_id == mill_id)
    if action_type:
        query = query.where(EnforcementAction.action_type == action_type)
    
    actions = session.exec(
        query.order_by(EnforcementAction.timestamp.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    
    return actions


# ============================================================================
# Audit Trail Endpoints
# ============================================================================

@router.get("/audit-trail/mill/{mill_id}")
def get_mill_audit_trail(
    mill_id: str,
    event_type: Optional[str] = None,  # mandate, friction, discrepancy, enforcement
    limit: int = 100,
    offset: int = 0,
    session: Session = Depends(get_session),
    _: bool = Depends(verify_api_key)
):
    """
    Comprehensive audit trail for a mill combining:
    - Mandate submissions
    - Discrepancy reports
    - Enforcement actions
    
    Sorted by timestamp (most recent first).
    
    event_type filter:
      - "mandate" → MandateSubmission records
      - "discrepancy" → DiscrepancyReport records
      - "enforcement" → EnforcementAction records
      - None → all records mixed
    """
    
    # Build result set with timestamps
    audit_records = []
    
    if event_type in (None, "mandate"):
        mandates = session.exec(
            select(MandateSubmission)
            .where(MandateSubmission.submitted_by == mill_id)
            .order_by(MandateSubmission.timestamp.desc())
        ).all()
        audit_records.extend([
            {
                "type": "mandate_submission",
                "timestamp": m.timestamp,
                "data": m
            }
            for m in mandates
        ])
    
    if event_type in (None, "discrepancy"):
        discrepancies = session.exec(
            select(DiscrepancyReport)
            .where(DiscrepancyReport.mill_id == mill_id)
            .order_by(DiscrepancyReport.created_at.desc())
        ).all()
        audit_records.extend([
            {
                "type": "discrepancy_report",
                "timestamp": d.created_at,
                "data": d
            }
            for d in discrepancies
        ])
    
    if event_type in (None, "enforcement"):
        enforcement = session.exec(
            select(EnforcementAction)
            .where(EnforcementAction.mill_id == mill_id)
            .order_by(EnforcementAction.timestamp.desc())
        ).all()
        audit_records.extend([
            {
                "type": "enforcement_action",
                "timestamp": a.timestamp,
                "data": a
            }
            for a in enforcement
        ])
    
    # Sort all by timestamp descending
    audit_records.sort(key=lambda x: x["timestamp"], reverse=True)
    
    # Apply pagination
    paginated = audit_records[offset:offset + limit]
    
    return {
        "mill_id": mill_id,
        "total_count": len(audit_records),
        "records": paginated
    }


@router.get("/audit-trail/full")
def get_full_audit_trail(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
    session: Session = Depends(get_session),
    _: bool = Depends(verify_api_key)
):
    """
    System-wide audit trail (all mills).
    
    Useful for regulatory reporting and institutional oversight.
    """
    
    # Get all records with optional date filtering
    mandates = session.exec(select(MandateSubmission)).all()
    discrepancies = session.exec(select(DiscrepancyReport)).all()
    enforcement = session.exec(select(EnforcementAction)).all()
    
    records = []
    for m in mandates:
        records.append({"type": "mandate_submission", "timestamp": m.timestamp, "data": m})
    for d in discrepancies:
        records.append({"type": "discrepancy_report", "timestamp": d.created_at, "data": d})
    for a in enforcement:
        records.append({"type": "enforcement_action", "timestamp": a.timestamp, "data": a})
    
    # Sort by timestamp descending
    records.sort(key=lambda x: x["timestamp"], reverse=True)
    
    # Apply pagination
    paginated = records[offset:offset + limit]
    
    return {
        "total_records": len(records),
        "returned_count": len(paginated),
        "audit_trail": paginated
    }
