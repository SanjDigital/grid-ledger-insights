try:
    from sqlmodel import SQLModel, Field, create_engine, Session, Relationship
except ModuleNotFoundError as e:
    raise SystemExit(
        "Missing dependency: run `pip install sqlmodel` (and any other required packages) to continue."
    ) from e

from sqlalchemy import CheckConstraint, Index, event
from typing import Optional
from datetime import datetime, timezone
from pathlib import Path

# 1. Define the Mill Table (The Assets)
class Mill(SQLModel, table=True):
    id: str = Field(primary_key=True)  # e.g., "NABIWI_01"
    name: str
    location: str
    meter_type: str  # Inhemeter, Clou, or Chint
    efficiency_baseline: float  # MK per kWh (e.g., 1000.0)
    revenue_rate_per_kwh: Optional[float] = None  # MK per kWh for revenue calculation

    public_key: Optional[str] = None
    device_id: Optional[str] = None
    last_nonce: Optional[str] = None
    last_event_hash: Optional[str] = None
    glass_box_certified: bool = Field(default=False)

# 2. Define the Token Ledger (The Fuel)
class TokenPurchase(SQLModel, table=True):
    token_id: str = Field(primary_key=True)
    mill_id: str = Field(foreign_key="mill.id")
    units_kwh: float
    cost_mwk: float
    revenue_wallet_id: str = Field(foreign_key="wallet.id")
    opex_wallet_id: str = Field(foreign_key="wallet.id")
    purchase_date: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            'revenue_wallet_id != opex_wallet_id',
            name='check_wallet_separation',
        ),
    )

# 3. Define the operator registry (People)
class Role(SQLModel, table=True):
    role_id: str = Field(primary_key=True)
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RolePermission(SQLModel, table=True):
    permission_id: Optional[int] = Field(default=None, primary_key=True)
    role_id: str = Field(foreign_key="role.role_id")
    action: str
    permitted: bool = Field(default=True)


class SitePhysicsConstraint(SQLModel, table=True):
    site_id: str = Field(primary_key=True)  # e.g., mill_id
    max_yield_per_kwh: Optional[float] = Field(default=2500.0)
    min_yield_per_kwh: Optional[float] = Field(default=800.0)
    max_opex_percentage: Optional[float] = Field(default=0.20)
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OperatorProfile(SQLModel, table=True):
    operator_id: str = Field(foreign_key="operator.operator_id", primary_key=True)
    n_reports: int = Field(default=0)
    mean_yield: float = Field(default=0.0)
    m2_yield: float = Field(default=0.0)
    mean_opex: float = Field(default=0.0)
    m2_opex: float = Field(default=0.0)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConstraintManifest(SQLModel, table=True):
    manifest_id: Optional[int] = Field(default=None, primary_key=True)
    role_id: str = Field(foreign_key="role.role_id")
    constraint_type: str
    constraint_definition: str  # JSON string describing payload-specific constraints
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Operator(SQLModel, table=True):
    operator_id: str = Field(primary_key=True)
    name: str
    phone: str
    mill_id: str = Field(foreign_key="mill.id")
    role_id: Optional[str] = Field(default=None, foreign_key="role.role_id")

    public_key: Optional[str] = None
    device_id: Optional[str] = None
    last_nonce: Optional[str] = None
    last_event_hash: Optional[str] = None


# 3.5 Define wallet reference table for audit trail
class Wallet(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    description: Optional[str] = None
    wallet_type: Optional[str] = None  # e.g. 'revenue' or 'opex'


# 3.6 Define chain-of-custody lineage via immutable events
class WalletLineage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    cycle_id: Optional[int] = Field(default=None, foreign_key="cycle.id")
    token_id: Optional[str] = Field(default=None, foreign_key="tokenpurchase.token_id")
    from_wallet_id: str = Field(foreign_key="wallet.id")
    to_wallet_id: str = Field(foreign_key="wallet.id")
    integrity_score: Optional[float] = Field(default=None)
    reason: str
    created_by_reconcile: bool = Field(default=True, nullable=False)
    event_time: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("created_by_reconcile = 1", name="check_walletlineage_reconcile_only"),
    )


# 3.7 Define append-only forensic EventLog (source of truth)
class EventLog(SQLModel, table=True):
    sequence_id: Optional[int] = Field(default=None, primary_key=True)
    mill_id: str = Field(foreign_key="mill.id")
    operator_id: str = Field(foreign_key="operator.operator_id")
    payload_json: str
    payload_hash: str
    signature: str
    prev_hash: str
    status: str
    event_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 4. Define the Daily Reports (The Telemetry)
class DailyReport(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mill_id: str = Field(foreign_key="mill.id")
    operator_id: Optional[str] = Field(default=None, foreign_key="operator.operator_id")
    opening_kwh: float
    closing_kwh: float
    actual_cash: float
    report_date: datetime = Field(default_factory=datetime.utcnow)


class Cycle(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mill_id: str = Field(foreign_key="mill.id")
    token_id: Optional[str] = Field(default=None, foreign_key="tokenpurchase.token_id")
    revenue_wallet_id: str = Field(foreign_key="wallet.id")
    opex_wallet_id: str = Field(foreign_key="wallet.id")
    integrity_score: Optional[float] = Field(default=None)
    cycle_start: datetime
    cycle_end: datetime
    total_usage_kwh: float
    total_actual_cash: float
    expected_revenue: float
    variance: float
    status: str
    audit_summary: str
    gap_breach_detected: bool = Field(default=False)
    gap_breach_details: Optional[str] = None
    reconciled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cycle_number: Optional[int] = Field(default=None, index=True)  # Sequential cycle identifier
    previous_seal: Optional[str] = Field(default=None)  # Previous cycle's seal for chain integrity
    cycle_seal: Optional[str] = Field(default=None)  # This cycle's SHA256 seal
    anchor_status: str = Field(default="PENDING")  # PENDING, ANCHORED, FAILED
    anchor_retries: int = Field(default=0)  # Retry counter for failed anchor attempts


class ReconciliationRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mill_id: str = Field(foreign_key="mill.id")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    start_time: datetime
    end_time: datetime
    physical_reading: float
    physical_consumed: float
    reported_kwh: float
    variance_pct: float
    status: str  # SOVEREIGN or UNDER_REVIEW
    event_count: int
    total_cash: float
    root_hash: str  # hash of last EventLog entry in window
    energy_accountability_ratio: float = Field(default=0.0)  # EAR = reported_kwh / metered_kwh, clipped to [0,1]
    verified_throughput: float = Field(default=0.0)  # VT = metered_kwh * EAR
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("root_hash != ''", name="check_root_hash_not_empty"),
        Index("ix_recon_mill_timestamp", "mill_id", "created_at"),  # For 30-day rolling queries
    )


# 5. Enforcement state (institution-facing control surface)
class MillIntegrityState(SQLModel, table=True):
    """
    Persisted mill/node enforcement state.

    This table is the control surface that downstream financing / audit policy
    engines can use to apply consequences (token gating, collateral, audits).
    """
    mill_id: str = Field(primary_key=True, foreign_key="mill.id")
    state: str = Field(default="VERIFIED")  # VERIFIED | UNDER_REVIEW | COMPROMISED | SUSPENDED
    severity_level: int = Field(default=1)  # 1..4 (informational..critical)
    last_trigger: Optional[str] = None      # GAP_BREACH | VARIANCE_BREACH | ECONOMIC_DEFICIT | ...
    last_reason: Optional[str] = None
    suspicion_score: float = Field(default=0.0)  # Cumulative suspicion (0-10), decays daily
    suspicion_updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 6. Credit Metrics (Dynamic Credit Envelope calculation)
class CreditMetrics(SQLModel, table=True):
    """
    Stores Dynamic Credit Envelope (DCE) calculations and financial metrics per mill.
    
    DCE = α × VR × EAR × (1 − RiskPenalty)
    Where:
    - α = advance rate (configurable per mill, default 0.6)
    - VR = Verified Revenue = VT × ERR
    - EAR = Energy Accountability Ratio
    - RiskPenalty = penalty based on breach frequency and volatility
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    mill_id: str = Field(foreign_key="mill.id")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Input parameters
    advance_rate: float = Field(default=0.6)  # α: configurable per mill
    effective_revenue_rate: float = Field(default=0.0)  # ERR = total_cash / metered_kwh
    energy_accountability_ratio: float = Field(default=0.0)  # EAR
    verified_throughput: float = Field(default=0.0)  # VT in kWh
    verified_revenue: float = Field(default=0.0)  # VR = VT × ERR
    
    # Risk assessment
    breach_count_30d: int = Field(default=0)  # Breaches in last 30 days
    volatility_score: float = Field(default=0.0)  # Historical variance metric (0-1)
    risk_penalty: float = Field(default=0.0)  # Combined penalty (0-0.5 cap)
    
    # DCE Result
    dynamic_credit_envelope: float = Field(default=0.0)  # Final DCE value
    
    # Metadata
    reconciliation_record_id: Optional[int] = Field(default=None, foreign_key="reconciliationrecord.id")
    status: str = Field(default="CALCULATED")  # CALCULATED, APPLIED, SUSPENDED
    
    __table_args__ = (
        CheckConstraint("advance_rate >= 0 AND advance_rate <= 1", name="check_advance_rate"),
        CheckConstraint("energy_accountability_ratio >= 0 AND energy_accountability_ratio <= 1", name="check_ear_range"),
        CheckConstraint("risk_penalty >= 0 AND risk_penalty <= 0.5", name="check_risk_penalty_cap"),
    )


# 7. Capital Event Log (Capital at Risk Handling)
class CreditEvent(SQLModel, table=True):
    """
    Records capital control actions triggered by mill integrity state transitions.
    
    Actions include:
    - CASH_SWEEP: Redirect incoming revenue to reduce exposure
    - CREDIT_COMPRESSION: Set remaining credit to zero
    - PRICING_ESCALATION: Apply penalty rate to outstanding balance
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    mill_id: str = Field(foreign_key="mill.id")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Action details
    action_type: str  # CASH_SWEEP, CREDIT_COMPRESSION, PRICING_ESCALATION
    trigger_state: str  # State that triggered action (BREACH, COMPROMISED, SUSPENDED)
    trigger_reason: str  # Breach type or reason for state transition
    
    # Financials
    outstanding_balance: float = Field(default=0.0)  # Balance before action (currency)
    action_amount: float = Field(default=0.0)  # Amount swept/compressed (currency)
    penalty_rate_bps: int = Field(default=0)  # Basis points applied (e.g., 500 for +5%)
    
    # Status
    action_status: str = Field(default="LOGGED")  # LOGGED, INITIATED, COMPLETED, FAILED
    execution_timestamp: Optional[datetime] = Field(default=None)  # When action was executed
    notes: Optional[str] = None  # Additional details or error messages
    
    # Reference
    mill_integrity_state_id: Optional[int] = Field(default=None)  # Reference to triggering state change
    credit_metric_id: Optional[int] = Field(default=None, foreign_key="creditmetrics.id")
    
    __table_args__ = (
        CheckConstraint("penalty_rate_bps >= 0 AND penalty_rate_bps <= 1000", name="check_penalty_rate_bps"),
    )


# 8. Per-Cycle Token Allocation Control
class TokenAllocation(SQLModel, table=True):
    """
    Per-cycle token allocation and tracking.
    
    One token = 59.9 kWh = one production cycle.
    Tracks expected revenue, cash receipt, and cycle status.
    """
    __tablename__ = "token_allocations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    mill_id: str = Field(foreign_key="mill.id", index=True)
    allocated_kwh: float = Field(default=59.9)
    expected_revenue: float
    allocated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = Field(default="PENDING")  # PENDING, CLOSED, MISSING, DISPUTED
    
    # Resolution tracking (for disputed cycles)
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    
    # Cycle seal tracking (for external anchor verification)
    cycle_number: Optional[int] = Field(default=None)  # Sequential cycle identifier
    cycle_seal: Optional[str] = Field(default=None)  # SHA256 seal computed at cycle closure
    
    # Relationships
    cash_receipts: list["CashReceipt"] = Relationship(back_populates="allocation")
    
    __table_args__ = (
        CheckConstraint("status IN ('PENDING', 'CLOSED', 'MISSING', 'DISPUTED')", name="check_token_allocation_status"),
    )


# Partial unique index: only one PENDING allocation per mill (race condition prevention)
Index(
    "ix_one_pending_per_mill",
    TokenAllocation.mill_id,
    unique=True,
    postgresql_where=(TokenAllocation.status == "PENDING"),
    sqlite_where=(TokenAllocation.status == "PENDING"),
    info={"persisted": True, "comment": "Prevents dual PENDING allocation race condition"}
)


class CashReceipt(SQLModel, table=True):
    """
    Cash receipt for a completed cycle.
    
    One receipt per allocation (unique constraint on allocation_id).
    Tracks amount received and verification status.
    """
    __tablename__ = "cash_receipts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    allocation_id: int = Field(foreign_key="token_allocations.id", unique=True)
    amount: float
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    verified: bool = Field(default=False)
    notes: Optional[str] = None
    
    # Relationships
    allocation: TokenAllocation = Relationship(back_populates="cash_receipts")


# 9. Decision Audit Log (Allocation Decision Tracking)
class DecisionAudit(SQLModel, table=True):
    """
    Audit trail for all allocation decisions (allowed or blocked).
    Stores decision basis and reasoning for compliance and debugging.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    mill_id: str = Field(foreign_key="mill.id", index=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    allowed: bool
    reason: Optional[str]
    decision_basis_json: str
    allocation_id: Optional[int] = Field(default=None, foreign_key="token_allocations.id")


class IdempotencyRecord(SQLModel, table=True):
    """
    Idempotency cache for allocation requests.
    Prevents double-allocation on retries using Idempotency-Key header.
    24-hour TTL for replay safety.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    idempotency_key: str = Field(index=True, unique=True)
    mill_id: str = Field(foreign_key="mill.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    response_json: str  # JSON serialized AllocationDecisionResponse
    allocation_id: Optional[int] = Field(default=None, foreign_key="token_allocations.id")
    expires_at: datetime  # TTL (24h)


# 10. Per-Mill Observation Configuration (Phase 1)
class MillObservationConfig(SQLModel, table=True):
    """
    Stores per-mill observation bands and enforcement status.
    
    Enables progressive enforcement: observe first (5-10 cycles), then lock
    a mill-specific band for effective_rate_per_kwh anomaly detection.
    
    Workflow:
    1. Deploy with enforcement_status="OBSERVING"
    2. Collect 5-10 baseline cycles
    3. Calculate band: median ± 2 std deviations
    4. Lock in this table and set enforcement_status="ACTIVE"
    5. From next cycle: out-of-band → decision_basis.reason="EFFECTIVE_RATE_ANOMALY"
    """
    __tablename__ = "mill_observation_configs"
    
    mill_id: str = Field(primary_key=True, foreign_key="mill.id")
    
    # Observation phase metadata
    observation_start_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cycles_observed: int = Field(default=0)  # Count of cycles in observation window
    
    # Enforcement band (locked after observation phase)
    effective_rate_band_low: Optional[float] = None   # e.g., 1,340 for Nabiwi
    effective_rate_band_high: Optional[float] = None  # e.g., 1,360 for Nabiwi
    band_median: Optional[float] = None
    band_stddev: Optional[float] = None
    
    # Status and metadata
    enforcement_status: str = Field(default="OBSERVING")  # OBSERVING | ACTIVE | SUSPENDED
    last_rate_observed: Optional[float] = None
    last_rate_timestamp: Optional[datetime] = None
    forensic_film_date: Optional[datetime] = None  # When manual validation occurred
    forensic_film_notes: Optional[str] = None
    
    # Audit trail
    band_locked_at: Optional[datetime] = None
    locked_by: Optional[str] = None  # Admin or system identifier
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        CheckConstraint(
            "enforcement_status IN ('OBSERVING', 'ACTIVE', 'SUSPENDED')",
            name="check_observation_status"
        ),
        Index("ix_mill_obs_status", "enforcement_status"),  # Fast query for active mills
    )


# 11. Tariff Rate History (Cost Accounting)
class TariffRate(SQLModel, table=True):
    """
    Immutable append-only ledger of historical owner energy costs.
    
    Tracks MERA tariff rate changes for owner P&L analysis and cost accounting.
    NOT used in enforcement (enforcement uses Mill.revenue_rate_per_kwh instead).
    
    Example: MERA ET7 tariff change on 2026-01-19 from 253.70 to 284.15 MK/kWh.
    
    Enables queries like:
    - Historical cost basis per quarter
    - Profit margin analysis (revenue_rate - energy_cost) × kWh
    - MERA rate volatility tracking
    """
    __tablename__ = "tariff_rates"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    mill_id: str = Field(foreign_key="mill.id", index=True)
    
    # Rate information
    rate_mk_per_kwh: float  # e.g., 284.15 for MERA ET7 Jan 2026
    effective_date: datetime  # When this rate becomes active
    
    # Metadata
    set_by: str  # e.g., "MERA_ADMIN", "SYSTEM", operator identifier
    notes: Optional[str] = None  # e.g., "MERA Jan 2026 adjustment: +12.0%"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index("ix_tariff_rate_mill_date", "mill_id", "effective_date"),  # For time-series queries
        CheckConstraint("rate_mk_per_kwh > 0", name="check_rate_positive"),
    )


# 12. Portfolio Anomaly Log (Phase 2)
class PortfolioAnomalyLog(SQLModel, table=True):
    """
    Logs multi-meter anomalies detected at portfolio level.
    
    Surfaces patterns that cannot be detected by single-meter analysis:
    - Coordinated blackouts across multiple meters (e.g., 6-meter sync Jun 2025)
    - Correlated variance spikes
    - Operator-level patterns (same person operating multiple mills)
    
    Implementation: backend/portfolio_engine.py (Phase 2)
    
    Example: 2025-06-15 four Nabiwi meters lost power simultaneously, flagged
    as portfolio anomaly (not noise, not coincidence).
    """
    __tablename__ = "portfolio_anomaly_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Anomaly metadata
    anomaly_type: str  # e.g., "SYNC_BLACKOUT", "CORRELATED_VARIANCE", "OPERATOR_PATTERN"
    severity_level: int = Field(default=1)  # 1 (low) to 4 (critical)
    
    # Correlation data
    operator_id: Optional[str] = Field(default=None, index=True)  # If operator-related
    mill_ids: str  # CSV or JSON list of affected mill IDs
    correlation_score: float  # 0.0 to 1.0 (confidence in anomaly)
    
    # Event details
    event_window_start: datetime  # When anomaly window began
    event_window_end: datetime    # When anomaly window ended
    event_description: str        # Human-readable summary
    
    # Verification
    escom_outage_match: Optional[str] = None  # Known ESCOM outage ID, if matched
    false_positive_flag: bool = Field(default=False)  # Manually marked as false positive
    
    # Audit trail
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    notes: Optional[str] = None
    
    __table_args__ = (
        Index("ix_anomaly_type_date", "anomaly_type", "detected_at"),
        Index("ix_anomaly_operator", "operator_id"),
        CheckConstraint(
            "severity_level >= 1 AND severity_level <= 4",
            name="check_severity_level"
        ),
        CheckConstraint(
            "correlation_score >= 0.0 AND correlation_score <= 1.0",
            name="check_correlation_score"
        ),
    )


# Database Setup
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

sqlite_url = f"sqlite:///{DATA_DIR / 'gridledger.db'}"
engine = create_engine(sqlite_url)


def create_db_and_tables() -> None:
    """Create the database and all tables.

    WARNING: this drops existing schema, intended for controlled test/dev environment.
    """
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    print("✅ GridLedger Database Initialized.")


@event.listens_for(WalletLineage, "before_update")
def prevent_walletlineage_update(mapper, connection, target):
    raise ValueError("WalletLineage events are immutable and cannot be updated.")


@event.listens_for(EventLog, "before_update")
def prevent_eventlog_update(mapper, connection, target):
    raise ValueError("EventLog is append-only and cannot be updated.")


@event.listens_for(EventLog, "before_delete")
def prevent_eventlog_delete(mapper, connection, target):
    raise ValueError("EventLog is append-only and cannot be deleted.")


if __name__ == "__main__":
    create_db_and_tables()
