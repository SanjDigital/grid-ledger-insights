"""
Institutional Governance Models – GL-1 Mandate Logging & Audit Trail
GridLedger Protocol GL-1 implementation

Immutable, append-only records for:
- Mandate submissions with friction analytics
- Discrepancy reports
- Enforcement actions

All records timestamped (UTC), indexed for efficient querying.
"""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone


class MandateSubmission(SQLModel, table=True):
    """
    Immutable record of institutional mandate acceptance.
    
    Represents an operator's explicit acknowledgment of GridLedger operational terms.
    Cannot be modified after creation (only status updates via new records).
    
    GL-1 Institutional Accountability Fields (6-field requirement):
    - submission_id (id): Unique record identifier
    - timestamp_utc (timestamp): UTC timestamp of submission
    - institution_name: Name of submitting institution (NBM, RBM, SPARC, etc.)
    - authorisation_level: Authority level of submitter (OPERATOR, MANAGER, DIRECTOR)
    - capital_range: Capital commitment tier (TIER_A, TIER_B, TIER_C)
    - mode_viewed: How statement was reviewed (INTERACTIVE, DEMO, OFFLINE)
    
    "Any deployment outside this standard becomes a recorded deviation."
    """
    __tablename__ = "mandate_submissions"

    id: Optional[int] = Field(default=None, primary_key=True)
    mandate_id: str = Field(unique=True, index=True)
    submitted_by: str = Field(index=True)  # operator_id or role identifier
    role: str  # e.g., "operator", "owner", "auditor"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    mandate_version_hash: str  # SHA256 of mandate statement (proof of which version was accepted)
    acknowledgment_type: str  # e.g., "full_acceptance", "conditional", "deviation"
    session_id: str = Field(index=True)  # browser/API session identifier
    status: str = Field(default="PENDING")  # PENDING, ACKNOWLEDGED, DEVIATION_RECORDED
    
    # GL-1 INSTITUTIONAL ACCOUNTABILITY FIELDS (6-field requirement)
    institution_name: str  # Name of submitting institution (NBM, RBM, SPARC, etc.)
    authorisation_level: str  # Authority level: OPERATOR, MANAGER, DIRECTOR, EXECUTIVE
    capital_range: str  # Capital commitment tier: TIER_A, TIER_B, TIER_C, EXEMPT
    mode_viewed: str  # How statement was reviewed: INTERACTIVE, DEMO, REVIEW_ONLY, OFFLINE
    
    # Audit trail
    acknowledged_at: Optional[datetime] = None
    deviation_reason: Optional[str] = None


class FrictionAnalytics(SQLModel, table=True):
    """
    Immutable record of friction moment engagement.
    
    Tracks how users interact with mandatory operational statements:
    - Scroll depth (% of statement read)
    - Time spent (ms)
    - Interaction count (clicks, confirmations)
    - Bypass attempts (proof of deliberate engagement, not accidental skip)
    
    Used to demonstrate institutional friction is non-byppassable.
    """
    __tablename__ = "friction_analytics"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    mandate_id: str = Field(foreign_key="mandate_submissions.mandate_id")
    scroll_depth_pct: float  # 0–100%
    time_on_statement_ms: int  # milliseconds
    interaction_count: int  # number of clicks/scrolls/confirmations
    bypass_attempted: bool = Field(default=False)  # True if user tried to skip friction gate
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DiscrepancyReport(SQLModel, table=True):
    """
    Institutional discrepancy report linking events to anomalies.
    
    Created when forensic engine flags an inconsistency between:
    - Reported energy vs. metered energy
    - Operator claim vs. ESCOM registry
    - Trust score vs. recent performance
    
    Status lifecycle: PENDING → REVIEWED → RESOLVED
    """
    __tablename__ = "discrepancy_reports"

    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: str = Field(index=True)  # Reference to event (stored as string, no hard FK)
    mill_id: str = Field(foreign_key="mill.id", index=True)
    reported_by: str  # operator_id, auditor_id, or system
    reason: str  # machine-readable reason code
    details: Optional[str] = None  # human-readable explanation
    status: str = Field(default="PENDING")  # PENDING, REVIEWED, RESOLVED, DISMISSED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None


class EnforcementAction(SQLModel, table=True):
    """
    Institutional enforcement action log.
    
    Every decision that affects mill tokenization is recorded:
    - TOKEN_BLOCKED – next token issuance suspended
    - MANUAL_OVERRIDE – auditor override of automation decision
    - REVIEW_REQUESTED – cycle flagged for human inspection
    - STRESS_FLAG_ACTIVATED – 3+ interruptions detected, bridging offered
    - INVESTIGATION_INITIATED – local fault claim under investigation
    
    Immutable record for regulatory audit trail.
    """
    __tablename__ = "enforcement_actions"

    id: Optional[int] = Field(default=None, primary_key=True)
    mill_id: str = Field(foreign_key="mill.id", index=True)
    cycle_id: Optional[int] = None  # Reference to cycle (no hard FK)
    action_type: str  # TOKEN_BLOCKED, MANUAL_OVERRIDE, REVIEW_REQUESTED, STRESS_FLAG_ACTIVATED, etc.
    initiated_by: str  # system, auditor_id, or automation rule
    reason: str  # explanation of why action was taken
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None  # outcome of the action
