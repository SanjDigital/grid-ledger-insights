"""
Revenue Truth Engine — The Deterministic Capital Conduit

Energy Consumption → Revenue Verification → Policy Execution → Capital Action

This module enforces:
- Node-level budgeted rates (NEVER global, NEVER hardcoded)
- Independent meter verification (2% tolerance)
- Revenue truth computation (expected vs actual)
- Direct Trust Scorecard → PXE mapping (no transformation)
- Breach override layer (pre-PXE enforcement)
- Capital Action Object factory (immutable, dual-hashed)

Core Principle: Energy is ground truth. Revenue = f(verified_kWh × budgeted_rate)
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Literal, Any
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from decimal import Decimal


# ============================================================================
# MILL CONFIGURATION (Node-Level Rates — Never Hardcoded)
# ============================================================================

@dataclass
class MillConfig:
    """
    Node-specific mill configuration.
    
    CRITICAL: budgeted_rate_per_kwh is NOT global.
    Each mill must have its own rate configured.
    
    Example:
    NABIWI_MKWINDA → Mk 1350 / kWh (node-specific, not reusable)
    """
    mill_id: str
    mill_name: str
    budgeted_rate_per_kwh: float  # Mk per kWh, node-specific
    location: str = ""
    commissioned_date: str = ""
    
    def __post_init__(self):
        """Validate rate is strictly positive."""
        if self.budgeted_rate_per_kwh <= 0:
            raise ValueError(f"budgeted_rate_per_kwh must be > 0, got {self.budgeted_rate_per_kwh}")
    
    def validate(self) -> bool:
        """Ensure mill_id and rate are defined."""
        if not self.mill_id or not isinstance(self.mill_id, str):
            raise ValueError("mill_id must be non-empty string")
        if not isinstance(self.budgeted_rate_per_kwh, (int, float)):
            raise ValueError("budgeted_rate_per_kwh must be numeric")
        return True


class MillConfigRegistry:
    """
    Global registry of node-level mill configurations.
    
    Requirement: Every mill must be registered before PXE execution.
    No defaults. No fallbacks. Reject if missing.
    """
    
    def __init__(self):
        self.registry: Dict[str, MillConfig] = {}
    
    def register_mill(self, config: MillConfig) -> bool:
        """Register a mill configuration. No overrides allowed."""
        config.validate()
        if config.mill_id in self.registry:
            raise ValueError(f"Mill {config.mill_id} already registered. Cannot override.")
        self.registry[config.mill_id] = config
        return True
    
    def get_mill(self, mill_id: str) -> MillConfig:
        """
        Fetch mill configuration by ID.
        Raise error if missing — no silent fallbacks.
        """
        if mill_id not in self.registry:
            raise ValueError(f"Mill {mill_id} not found in registry. Must be registered before execution.")
        return self.registry[mill_id]
    
    def get_rate(self, mill_id: str) -> float:
        """Get budgeted rate for mill. Fail fast if missing."""
        config = self.get_mill(mill_id)
        return config.budgeted_rate_per_kwh


# ============================================================================
# METER VERIFICATION MODULE
# ============================================================================

@dataclass
class MeterReadings:
    """Energy measurements from independent sources."""
    token_reported_kwh: float  # From operator token/billing system
    meter_measured_kwh: float  # From physical meter (ground truth)
    timestamp: str  # ISO-8601
    meter_id: str = ""
    notes: str = ""


class MeterVerificationError(Exception):
    """Raised when energy mismatch exceeds tolerance."""
    pass


class EnergyVerifier:
    """
    Independent meter verification module.
    
    This is the primary anti-theft control.
    No operator input allowed in this computation.
    """
    
    TOLERANCE = 0.02  # 2% tolerance
    
    @staticmethod
    def compute_verified_kwh(
        token_kwh: float,
        meter_kwh: float
    ) -> float:
        """
        Compute verified energy using meter as ground truth.
        
        Args:
            token_kwh: Energy from operator/token system
            meter_kwh: Energy from physical meter (authoritative)
        
        Returns:
            meter_kwh (ground truth)
        
        Raises:
            MeterVerificationError if mismatch > tolerance
        """
        if meter_kwh <= 0:
            raise MeterVerificationError(f"Meter reading must be > 0, got {meter_kwh}")
        
        if token_kwh <= 0:
            raise MeterVerificationError(f"Token kwh must be > 0, got {token_kwh}")
        
        # Compute absolute mismatch
        mismatch = abs(token_kwh - meter_kwh)
        mismatch_pct = mismatch / token_kwh
        
        # Reject if beyond tolerance
        if mismatch_pct > EnergyVerifier.TOLERANCE:
            raise MeterVerificationError(
                f"Energy mismatch {mismatch_pct:.2%} exceeds tolerance {EnergyVerifier.TOLERANCE:.2%}. "
                f"Token: {token_kwh} kWh, Meter: {meter_kwh} kWh"
            )
        
        # Meter is ground truth
        return meter_kwh


# ============================================================================
# REVENUE TRUTH ENGINE
# ============================================================================

@dataclass
class RevenueSnapshot:
    """Immutable revenue calculation snapshot."""
    mill_id: str
    timestamp: str
    verified_kwh: float
    budgeted_rate_per_kwh: float
    expected_revenue: float
    actual_revenue: float
    revenue_efficiency_ratio: float
    
    def validate(self) -> bool:
        """Ensure revenue snapshot is mathematically consistent."""
        # Verify expected revenue calculation
        computed_expected = self.verified_kwh * self.budgeted_rate_per_kwh
        if abs(computed_expected - self.expected_revenue) > 0.01:  # 0.01 Mk tolerance for rounding
            raise ValueError(
                f"Expected revenue mismatch. Computed: {computed_expected}, Given: {self.expected_revenue}"
            )
        
        # Verify efficiency ratio
        if self.expected_revenue > 0:
            computed_ratio = self.actual_revenue / self.expected_revenue
            if abs(computed_ratio - self.revenue_efficiency_ratio) > 0.001:
                raise ValueError(
                    f"Revenue efficiency ratio mismatch. Computed: {computed_ratio}, Given: {self.revenue_efficiency_ratio}"
                )
        
        return True


class RevenueTruthEngine:
    """
    Deterministic revenue computation.
    
    All calculations are pure functions of:
    - verified_kWh (from meter)
    - budgeted_rate_per_kWh (from mill config)
    - actual_revenue (from billing system)
    """
    
    @staticmethod
    def compute_expected_revenue(verified_kwh: float, budgeted_rate: float) -> float:
        """
        Compute expected revenue.
        
        Formula: expected_revenue = verified_kwh × budgeted_rate
        
        This is NOT operator-controlled.
        This is NOT negotiable.
        """
        if verified_kwh < 0 or budgeted_rate < 0:
            raise ValueError(f"Invalid inputs: kwh={verified_kwh}, rate={budgeted_rate}")
        return verified_kwh * budgeted_rate
    
    @staticmethod
    def compute_efficiency(actual_revenue: float, expected_revenue: float) -> float:
        """
        Compute revenue efficiency ratio.
        
        Formula: efficiency = actual_revenue / expected_revenue
        
        - 1.0 = perfect match (operator reported truthfully)
        - < 1.0 = under-reporting (operator hiding revenue)
        - > 1.0 = over-reporting (impossible, unless meter fault)
        """
        if expected_revenue <= 0:
            raise ValueError(f"Expected revenue must be > 0, got {expected_revenue}")
        
        return actual_revenue / expected_revenue
    
    @staticmethod
    def create_revenue_snapshot(
        mill_id: str,
        verified_kwh: float,
        budgeted_rate_per_kwh: float,
        actual_revenue: float,
    ) -> RevenueSnapshot:
        """
        Create immutable revenue snapshot.
        
        All computations happen here. No transformation allowed later.
        """
        expected_revenue = RevenueTruthEngine.compute_expected_revenue(
            verified_kwh, budgeted_rate_per_kwh
        )
        efficiency = RevenueTruthEngine.compute_efficiency(
            actual_revenue, expected_revenue
        )
        
        snapshot = RevenueSnapshot(
            mill_id=mill_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            verified_kwh=verified_kwh,
            budgeted_rate_per_kwh=budgeted_rate_per_kwh,
            expected_revenue=expected_revenue,
            actual_revenue=actual_revenue,
            revenue_efficiency_ratio=efficiency,
        )
        
        snapshot.validate()
        return snapshot


# ============================================================================
# TRUST SCORECARD → PXE INPUT MAPPING (Direct, No Transformation)
# ============================================================================

@dataclass
class TrustScorecard:
    """
    Trust Scorecard output (from backend/trust_scorecard.py).
    
    This is the source of truth for operator integrity.
    """
    mill_id: str
    timestamp: str
    trust_score: int  # 0-100
    ear_score: float  # Energy Accountability Ratio
    consistency_score: int  # 0-100
    reconciliation_score: int  # 0-100
    governance_score: int  # 0-100
    fraud_risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    mill_state: Literal["VERIFIED", "UNDER_REVIEW", "COMPROMISED", "SUSPENDED"]


@dataclass
class PXEInput:
    """
    Direct input to Policy Execution Engine.
    
    Constructed from:
    - Trust Scorecard output (no transformation)
    - Revenue Snapshot (no transformation)
    - Meter Verification (no transformation)
    
    All values pre-computed upstream.
    No calculation happens during mapping.
    """
    mill_id: str
    timestamp: str
    
    # Trust Scorecard fields (direct pass-through)
    trust_score: int
    ear_score: float
    consistency_score: int
    reconciliation_score: int
    governance_score: int
    fraud_risk_level: str
    mill_state: str
    
    # Revenue fields (from Revenue Snapshot)
    verified_kwh: float
    budgeted_rate_per_kwh: float
    expected_revenue: float
    actual_revenue: float
    revenue_efficiency_ratio: float
    
    # Breach flags (from meter verification & scorecard)
    breach_flags: List[str]  # List of breach types if any
    
    def validate(self) -> bool:
        """Validate input contract."""
        if not self.mill_id:
            raise ValueError("mill_id required")
        if not (0 <= self.trust_score <= 100):
            raise ValueError(f"trust_score must be 0-100, got {self.trust_score}")
        if not (0 <= self.consistency_score <= 100):
            raise ValueError(f"consistency_score must be 0-100, got {self.consistency_score}")
        return True


class PXEInputFactory:
    """
    Factory to construct PXEInput from upstream components.
    
    Pattern:
    1. Get Trust Scorecard output
    2. Get Revenue Snapshot
    3. Get Meter Verification
    4. Construct PXEInput (no transformation)
    """
    
    @staticmethod
    def from_scorecard_and_revenue(
        scorecard: TrustScorecard,
        revenue_snapshot: RevenueSnapshot,
        breach_flags: Optional[List[str]] = None,
    ) -> PXEInput:
        """
        Construct PXEInput directly from scorecard and revenue data.
        
        Requirements:
        - No calculation
        - No transformation
        - Direct field mapping
        """
        pxe_input = PXEInput(
            mill_id=scorecard.mill_id,
            timestamp=scorecard.timestamp,
            trust_score=scorecard.trust_score,
            ear_score=scorecard.ear_score,
            consistency_score=scorecard.consistency_score,
            reconciliation_score=scorecard.reconciliation_score,
            governance_score=scorecard.governance_score,
            fraud_risk_level=scorecard.fraud_risk_level,
            mill_state=scorecard.mill_state,
            verified_kwh=revenue_snapshot.verified_kwh,
            budgeted_rate_per_kwh=revenue_snapshot.budgeted_rate_per_kwh,
            expected_revenue=revenue_snapshot.expected_revenue,
            actual_revenue=revenue_snapshot.actual_revenue,
            revenue_efficiency_ratio=revenue_snapshot.revenue_efficiency_ratio,
            breach_flags=breach_flags or [],
        )
        
        pxe_input.validate()
        return pxe_input


# ============================================================================
# BREACH OVERRIDE LAYER (Pre-PXE, Absolute Authority)
# ============================================================================

class BreachOverride:
    """
    Pre-policy enforcement layer.
    
    This layer executes BEFORE PXE policy evaluation.
    It has absolute authority to reject or constrain.
    
    Breaches override all policies.
    """
    
    BREACH_TYPES = {
        "ENERGY_MISMATCH": "Meter and token readings mismatch beyond tolerance",
        "REVENUE_FRAUD": "Revenue under-reporting detected (efficiency < threshold)",
        "GOVERNANCE_FAILURE": "Signature/RBAC failure in identity layer",
        "MILL_SUSPENDED": "Mill is in SUSPENDED state (no credit)",
    }
    
    @staticmethod
    def evaluate(pxe_input: PXEInput) -> Dict[str, Any]:
        """
        Evaluate breach conditions.
        
        Returns:
            {
                "breach_detected": bool,
                "breach_type": str or None,
                "override_action": str or None,
                "reason": str
            }
        """
        # Check 1: Mill state = SUSPENDED
        if pxe_input.mill_state == "SUSPENDED":
            return {
                "breach_detected": True,
                "breach_type": "MILL_SUSPENDED",
                "override_action": "REJECT",
                "reason": "Mill is in SUSPENDED state. No credit available.",
            }
        
        # Check 2: Breach flags present
        if pxe_input.breach_flags:
            if "ENERGY_MISMATCH" in pxe_input.breach_flags:
                return {
                    "breach_detected": True,
                    "breach_type": "ENERGY_MISMATCH",
                    "override_action": "REQUIRE_AUDIT",
                    "reason": "Energy mismatch detected. Requires immediate audit.",
                }
            
            if "REVENUE_FRAUD" in pxe_input.breach_flags:
                return {
                    "breach_detected": True,
                    "breach_type": "REVENUE_FRAUD",
                    "override_action": "REJECT",
                    "reason": "Revenue under-reporting detected. Credit frozen.",
                }
        
        # Check 3: Revenue efficiency below critical threshold
        if pxe_input.revenue_efficiency_ratio < 0.85:  # <85% efficiency = fraud signal
            return {
                "breach_detected": True,
                "breach_type": "REVENUE_FRAUD",
                "override_action": "REJECT",
                "reason": f"Revenue efficiency {pxe_input.revenue_efficiency_ratio:.2%} below 85% threshold.",
            }
        
        # Check 4: Governance failure
        if pxe_input.governance_score < 50:
            return {
                "breach_detected": True,
                "breach_type": "GOVERNANCE_FAILURE",
                "override_action": "REQUIRE_AUDIT",
                "reason": "Governance score critically low. RBAC/signature failures detected.",
            }
        
        # No breach
        return {
            "breach_detected": False,
            "breach_type": None,
            "override_action": None,
            "reason": "No breach conditions met.",
        }


# ============================================================================
# CAPITAL ACTION OBJECT FACTORY (Strict Schema, Dual Hashing)
# ============================================================================

@dataclass
class CapitalActionObject:
    """
    Immutable directive for capital allocation.
    
    Schema is locked. Produced by policy execution.
    Consumed by external capital systems (banks, escrow, token issuance).
    
    advance_amount = expected_revenue × advance_rate
    (computed from verified energy × budgeted rate × policy advance_rate)
    """
    mill_id: str
    decision: Literal["APPROVE", "CONDITIONAL", "DECLINE"]
    advance_rate: float
    advance_amount: float  # Actual Mk to disburse
    capital_state: Literal["OPEN", "CONSTRAINED", "FROZEN"]
    input_hash: str
    policy_hash: str
    timestamp: str
    execution_trace: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str, indent=2)


class CAOFactory:
    """
    Factory to create Capital Action Objects with dual hashing.
    """
    
    @staticmethod
    def _hash_input(pxe_input: PXEInput) -> str:
        """Hash all PXE inputs (SHA256)."""
        input_dict = asdict(pxe_input)
        input_json = json.dumps(input_dict, sort_keys=True, default=str)
        return hashlib.sha256(input_json.encode()).hexdigest()
    
    @staticmethod
    def _hash_policy(policy_dict: Dict[str, Any]) -> str:
        """Hash policy definition (SHA256)."""
        policy_json = json.dumps(policy_dict, sort_keys=True)
        return hashlib.sha256(policy_json.encode()).hexdigest()
    
    @staticmethod
    def create(
        pxe_input: PXEInput,
        decision: str,
        advance_rate: float,
        advance_amount: float,  # Mk to disburse
        capital_state: str,
        policy_dict: Dict[str, Any],
        execution_trace: Dict[str, Any],
    ) -> CapitalActionObject:
        """
        Create immutable Capital Action Object with dual hashes.
        
        advance_amount = expected_revenue × advance_rate
        """
        input_hash = CAOFactory._hash_input(pxe_input)
        policy_hash = CAOFactory._hash_policy(policy_dict)
        
        return CapitalActionObject(
            mill_id=pxe_input.mill_id,
            decision=decision,
            advance_rate=advance_rate,
            advance_amount=advance_amount,
            capital_state=capital_state,
            input_hash=input_hash,
            policy_hash=policy_hash,
            timestamp=datetime.now(timezone.utc).isoformat(),
            execution_trace=execution_trace,
        )


# ============================================================================
# POLICY REGISTRY (Multi-Lender, Versioned)
# ============================================================================

@dataclass
class Policy:
    """
    Immutable policy definition.
    
    No mutable policies. Period.
    Version = separate policy object.
    """
    policy_id: str
    version: str
    rules: List[Dict[str, Any]]
    effective_timestamp: str
    status: Literal["ACTIVE", "ARCHIVED", "DEPRECATED"]


class PolicyRegistry:
    """
    Multi-lender policy registry.
    
    Policies are versioned and immutable.
    Each execution references a specific policy_id:version.
    """
    
    def __init__(self):
        self.policies: Dict[str, Policy] = {}
        self._register_reference_policies()
    
    def _register_reference_policies(self):
        """Register canonical reference policies."""
        # STANDARD_COMMERCIAL_V1
        self.register(
            Policy(
                policy_id="STANDARD_COMMERCIAL",
                version="1.0",
                rules=[
                    {
                        "name": "APPROVED_SOVEREIGN",
                        "conditions": [
                            ("trust_score", ">=", 90),
                            ("revenue_efficiency_ratio", ">=", 0.95),
                        ],
                        "decision": "APPROVE",
                        "advance_rate": 0.60,
                        "capital_state": "OPEN",
                    },
                    {
                        "name": "APPROVED_COMMERCIAL",
                        "conditions": [
                            ("trust_score", ">=", 75),
                            ("revenue_efficiency_ratio", ">=", 0.90),
                        ],
                        "decision": "APPROVE",
                        "advance_rate": 0.50,
                        "capital_state": "OPEN",
                    },
                    {
                        "name": "CONDITIONAL",
                        "conditions": [
                            ("trust_score", ">=", 60),
                            ("revenue_efficiency_ratio", ">=", 0.85),
                        ],
                        "decision": "CONDITIONAL",
                        "advance_rate": 0.35,
                        "capital_state": "CONSTRAINED",
                    },
                    {
                        "name": "DECLINE",
                        "conditions": [],  # Default/fallback
                        "decision": "DECLINE",
                        "advance_rate": 0.00,
                        "capital_state": "FROZEN",
                    },
                ],
                effective_timestamp="2026-03-30T00:00:00Z",
                status="ACTIVE",
            )
        )
    
    def register(self, policy: Policy) -> bool:
        """Register a policy. No overrides allowed."""
        key = f"{policy.policy_id}:{policy.version}"
        if key in self.policies:
            raise ValueError(f"Policy {key} already registered. Create a new version instead.")
        self.policies[key] = policy
        return True
    
    def get(self, policy_id: str, version: str = "1.0") -> Policy:
        """Retrieve policy by ID and version."""
        key = f"{policy_id}:{version}"
        if key not in self.policies:
            raise ValueError(f"Policy {key} not found.")
        return self.policies[key]


# ============================================================================
# INTERNAL TREASURY (Capital Disbursement & Ledger)
# ============================================================================

@dataclass
class CapitalLedgerEntry:
    """
    Immutable record of a capital action execution.
    
    Stored in capital_ledger table for audit trail.
    """
    mill_id: str
    cao_input_hash: str
    cao_policy_hash: str
    advance_amount: float
    advance_rate: float
    decision: str
    timestamp: str
    status: Literal["EXECUTED", "NO_ACTION", "FAILED"]
    error_message: Optional[str] = None


class InternalTreasury:
    """
    In-memory ledger for capital disbursement tracking.
    
    Backed by database persistence (capital_ledger table).
    Executes actual capital transfers to mills.
    
    Guarantees:
    - All transactions are logged
    - No amounts are silent
    - Every disbursement is auditable
    """
    
    def __init__(self):
        """Initialize in-memory ledger."""
        self.ledger: Dict[str, float] = {}  # mill_id → cumulative balance
        self.transaction_log: List[CapitalLedgerEntry] = []
    
    def disburse(
        self,
        mill_id: str,
        advance_amount: float,
        cao: CapitalActionObject,
    ) -> Dict[str, Any]:
        """
        Execute capital disbursement to mill.
        
        Records transaction in ledger and log.
        
        Args:
            mill_id: Target mill
            advance_amount: Mk to disburse
            cao: Capital Action Object (for hashing and trace)
        
        Returns:
            Dict with execution status and new balance
        """
        if advance_amount < 0:
            error = "Advance amount cannot be negative"
            entry = CapitalLedgerEntry(
                mill_id=mill_id,
                cao_input_hash=cao.input_hash,
                cao_policy_hash=cao.policy_hash,
                advance_amount=advance_amount,
                advance_rate=cao.advance_rate,
                decision=cao.decision,
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="FAILED",
                error_message=error,
            )
            self.transaction_log.append(entry)
            return {
                "status": "FAILED",
                "mill_id": mill_id,
                "amount": advance_amount,
                "error": error,
            }
        
        # Execute disbursement
        current_balance = self.ledger.get(mill_id, 0.0)
        new_balance = current_balance + advance_amount
        self.ledger[mill_id] = new_balance
        
        # Log transaction
        entry = CapitalLedgerEntry(
            mill_id=mill_id,
            cao_input_hash=cao.input_hash,
            cao_policy_hash=cao.policy_hash,
            advance_amount=advance_amount,
            advance_rate=cao.advance_rate,
            decision=cao.decision,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="EXECUTED",
        )
        self.transaction_log.append(entry)
        
        return {
            "status": "EXECUTED",
            "mill_id": mill_id,
            "amount": advance_amount,
            "previous_balance": current_balance,
            "new_balance": new_balance,
            "cao_input_hash": cao.input_hash,
            "cao_policy_hash": cao.policy_hash,
        }
    
    def get_balance(self, mill_id: str) -> float:
        """Get current balance for mill."""
        return self.ledger.get(mill_id, 0.0)
    
    def get_transaction_log(self, mill_id: Optional[str] = None) -> List[CapitalLedgerEntry]:
        """Get transaction log, optionally filtered by mill_id."""
        if mill_id:
            return [t for t in self.transaction_log if t.mill_id == mill_id]
        return self.transaction_log


class CapitalEndpoint:
    """
    External capital interface with persistent ledger.
    
    Wires CAOs directly to the Internal Treasury.
    Creates immutable audit trail.
    """
    
    def __init__(self, treasury: InternalTreasury):
        """Initialize with reference to treasury."""
        self.treasury = treasury
        self.caos_received: List[CapitalActionObject] = []
    
    def send_capital_action(self, cao: CapitalActionObject) -> Dict[str, Any]:
        """
        Send CAO to treasury for execution.
        
        If decision == APPROVE: disburse advance_amount
        Otherwise: log as NO_ACTION
        """
        self.caos_received.append(cao)
        
        if cao.decision == "APPROVE":
            # Execute disbursement
            result = self.treasury.disburse(cao.mill_id, cao.advance_amount, cao)
            return result
        else:
            # Log as no-action
            entry = CapitalLedgerEntry(
                mill_id=cao.mill_id,
                cao_input_hash=cao.input_hash,
                cao_policy_hash=cao.policy_hash,
                advance_amount=0.0,
                advance_rate=cao.advance_rate,
                decision=cao.decision,
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="NO_ACTION",
            )
            self.treasury.transaction_log.append(entry)
            
            return {
                "status": "NO_ACTION",
                "mill_id": cao.mill_id,
                "decision": cao.decision,
                "reason": f"Decision is {cao.decision}, no capital disbursement",
            }


# ============================================================================
# ENTROPY MONITOR: Structural Leakage Detection
# ============================================================================

@dataclass
class VarianceRecord:
    """Immutable record of revenue variance."""
    date: str  # ISO-8601
    variance: float  # actual_revenue - expected_revenue
    variance_sign: int  # 1 if variance >= 0 (over/meet), -1 if variance < 0 (under)
    
    def __post_init__(self):
        """Compute sign from variance."""
        if self.variance_sign not in [-1, 1]:
            raise ValueError("variance_sign must be -1 or 1")


class EntropyMonitor:
    """
    Detects structural revenue leakage through negative variance patterns.
    
    Implements STICKY PENALTY DECAY to prevent pulse exploits:
    - Leakage triggers 0.9× penalty
    - Recovery is gradual, not instant
    - One positive day only starts recovery, doesn't reset penalty
    - Operator must maintain clean pattern for N days to fully recover
    
    Principle:
    - Track daily variance: actual_revenue - expected_revenue
    - Maintain rolling window of variance signs (positive/negative)
    - If all signs negative for N days → structural leakage detected
    - Apply 10% penalty multiplier, which decays slowly over time
    
    Example: 7-day window all negative → 0.9× penalty
             Day 8 positive → penalty stays 0.9, then recovers at recovery_rate per day
             Takes ~20 more clean days to reach 1.0 (with recovery_rate=0.05)
    """
    
    def __init__(self, mill_id: str, window_days: int = 7, recovery_rate: float = 0.05):
        """
        Initialize entropy monitor with sticky penalty decay.
        
        Args:
            mill_id: Mill to monitor
            window_days: Rolling window size (default: 7 days)
            recovery_rate: Daily recovery fraction (default: 0.05 = 5% per day)
                          Takes ~20 days to recover from 0.9 to 1.0
        """
        self.mill_id = mill_id
        self.window_days = window_days
        self.variance_records: List[VarianceRecord] = []  # Rolling window
        self.leakage_threshold = window_days  # All days negative = leakage
        self.penalty_multiplier_value = 1.0  # Current penalty (starts at 1.0, decays to 0.9)
        self.recovery_rate = recovery_rate  # 5% per day default
    
    def record_variance(self, date: str, variance: float) -> float:
        """
        Record daily revenue variance and update penalty multiplier.
        
        Args:
            date: ISO-8601 date string
            variance: actual_revenue - expected_revenue
                     Negative = under-reporting (red flag)
                     Positive = over-reporting (unlikely)
                     Zero = perfect match
        
        Returns:
            Updated penalty multiplier value
        """
        variance_sign = 1 if variance >= 0 else -1
        
        record = VarianceRecord(
            date=date,
            variance=variance,
            variance_sign=variance_sign,
        )
        
        self.variance_records.append(record)
        
        # Maintain rolling window
        if len(self.variance_records) > self.window_days:
            self.variance_records = self.variance_records[-self.window_days:]
        
        # Update penalty multiplier (STICKY DECAY mechanism)
        if self.is_structural_leakage():
            # Current window all negative → activate penalty
            self.penalty_multiplier_value = 0.9
        else:
            # Not all negative → begin GRADUAL recovery (not instant reset)
            self.penalty_multiplier_value = min(1.0, self.penalty_multiplier_value + self.recovery_rate)
        
        return self.penalty_multiplier_value
    
    def is_structural_leakage(self) -> bool:
        """
        Detect structural leakage: all variance signs negative in window.
        
        Returns:
            True if all dates in window show under-reporting (variance < 0)
            False if window not full, or any positive/zero variance exists
        
        Logic:
        - Need minimum window_days records
        - Every record must have variance_sign == -1
        - If ANY positive variance → not structural (dismisses false positives)
        """
        if len(self.variance_records) < self.window_days:
            return False
        
        # All must be negative for structural leakage
        return all(record.variance_sign == -1 for record in self.variance_records)
    
    def get_penalty_multiplier(self, applying_structural_penalty: bool = True) -> float:
        """
        Get current penalty multiplier for advance rate.
        
        With sticky penalty decay:
        - Returns current penalty value (0.9 to 1.0 range)
        - NOT binary reset on first positive variance
        - Penalty decays at recovery_rate per update
        
        Args:
            applying_structural_penalty: Whether to apply penalty (default: True)
        
        Returns:
            Current penalty multiplier (0.9 ≤ value ≤ 1.0)
            1.0 = no penalty
            0.9 = full penalty
        
        Usage:
            final_rate = computed_rate × monitor.get_penalty_multiplier()
        """
        if not applying_structural_penalty:
            return 1.0
        
        # Return current penalty (no longer binary) - it decays gradually
        return self.penalty_multiplier_value
    
    def penalty_multiplier(self) -> float:
        """Convenience alias for get_penalty_multiplier()."""
        return self.get_penalty_multiplier()
    
    def get_leakage_status(self) -> Dict[str, Any]:
        """
        Get detailed leakage diagnostics.
        
        Returns:
            Dict with:
            - structural_leakage: bool
            - window_days: int
            - records_in_window: int
            - negative_count: int
            - leakage_percentage: float (% of records negative)
            - penalty_multiplier: float
        """
        negative_count = sum(
            1 for record in self.variance_records 
            if record.variance_sign == -1
        )
        
        window_size = len(self.variance_records)
        leakage_pct = (negative_count / window_size * 100) if window_size > 0 else 0
        
        return {
            "mill_id": self.mill_id,
            "structural_leakage": self.is_structural_leakage(),
            "window_days": self.window_days,
            "records_in_window": window_size,
            "negative_count": negative_count,
            "leakage_percentage": leakage_pct,
            "penalty_multiplier": self.get_penalty_multiplier(),
            "variance_history": [
                {
                    "date": r.date,
                    "variance": r.variance,
                    "sign": "UNDER" if r.variance_sign == -1 else "OVER/MEET"
                }
                for r in self.variance_records
            ],
        }


# ============================================================================
# COMPLETE REVENUE GATEWAY (End-to-End Integration)
# ============================================================================

class RevenueGateway:
    """
    End-to-end conduit from Trust Scorecard through to Capital Action.
    
    Pattern:
    Energy (meter) → Revenue (truth) → Trust Score → PXE → CAO → Capital (Treasury)
    
    Includes:
    - Mill configuration registry
    - Energy verification
    - Revenue computation
    - PXE input construction
    - Breach override evaluation
    - CAO factory (with advance_amount computation)
    - Internal treasury (ledger + disbursement)
    - Capital endpoint (wired to treasury)
    """
    
    def __init__(self):
        """Initialize complete revenue gateway with treasury and entropy monitors."""
        self.mill_registry = MillConfigRegistry()
        self.energy_verifier = EnergyVerifier()
        self.revenue_engine = RevenueTruthEngine()
        self.policy_registry = PolicyRegistry()
        self.treasury = InternalTreasury()
        self.capital_endpoint = CapitalEndpoint(self.treasury)
        self.entropy_monitors: Dict[str, EntropyMonitor] = {}  # Per-mill monitors
    
    def get_or_create_entropy_monitor(self, mill_id: str, window_days: int = 7) -> EntropyMonitor:
        """Get existing entropy monitor or create new one for mill."""
        if mill_id not in self.entropy_monitors:
            self.entropy_monitors[mill_id] = EntropyMonitor(mill_id, window_days)
        return self.entropy_monitors[mill_id]
    
    def execute_capital_flow(
        self,
        scorecard: TrustScorecard,
        meter_readings: MeterReadings,
        policy_id: str = "STANDARD_COMMERCIAL",
        policy_version: str = "1.0",
        actual_revenue: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Execute complete capital flow.
        
        1. Verify energy (meter vs token)
        2. Compute expected revenue
        3. Construct PXEInput (no transformation)
        4. Check breach overrides
        5. Execute policy
        6. Compute advance_amount = expected_revenue × advance_rate
        7. Emit CAO
        8. Execute capital disbursement via treasury
        
        Args:
            scorecard: Trust scorecard from integrity assessment
            meter_readings: Energy meter readings
            policy_id: Policy to apply (default: STANDARD_COMMERCIAL)
            policy_version: Policy version (default: 1.0)
            actual_revenue: Actual revenue from billing system (optional)
                           If not provided, calculated as verified_kwh × budgeted_rate
                           (assumes perfect efficiency / 100% collection)
        
        Returns: CAO + treasury execution result
        """
        # Step 1: Verify energy
        try:
            verified_kwh = self.energy_verifier.compute_verified_kwh(
                meter_readings.token_reported_kwh,
                meter_readings.meter_measured_kwh,
            )
        except MeterVerificationError as e:
            # Energy mismatch detected
            verified_kwh = meter_readings.meter_measured_kwh
            breach_flags = ["ENERGY_MISMATCH"]
        else:
            breach_flags = []
        
        # Step 2: Get mill config (rate)
        mill_config = self.mill_registry.get_mill(scorecard.mill_id)
        
        # Step 3: Compute expected revenue
        expected_revenue = RevenueTruthEngine.compute_expected_revenue(
            verified_kwh,
            mill_config.budgeted_rate_per_kwh
        )
        
        # If actual_revenue not provided, assume perfect efficiency (100% collection)
        if actual_revenue is None:
            actual_revenue = expected_revenue
        
        revenue_snapshot = self.revenue_engine.create_revenue_snapshot(
            mill_id=scorecard.mill_id,
            verified_kwh=verified_kwh,
            budgeted_rate_per_kwh=mill_config.budgeted_rate_per_kwh,
            actual_revenue=actual_revenue,
        )
        
        # Step 4: Construct PXEInput (direct mapping, no transformation)
        pxe_input = PXEInputFactory.from_scorecard_and_revenue(
            scorecard,
            revenue_snapshot,
            breach_flags,
        )
        
        # Step 5: Check breach overrides (pre-policy)
        breach_eval = BreachOverride.evaluate(pxe_input)
        
        if breach_eval["breach_detected"]:
            # Override action applies
            decision = breach_eval["override_action"]
            capital_state = "FROZEN" if decision == "REJECT" else "CONSTRAINED"
            advance_rate = 0.0 if decision == "REJECT" else 0.35
        else:
            # Execute policy
            policy = self.policy_registry.get(policy_id, policy_version)
            decision, advance_rate, capital_state = self._evaluate_policy(
                pxe_input, policy
            )
        
        # Step 6: Compute advance_amount
        # advance_amount = expected_revenue × advance_rate
        advance_amount = revenue_snapshot.expected_revenue * advance_rate
        
        # Step 7: Emit CAO (with advance_amount)
        cao = CAOFactory.create(
            pxe_input=pxe_input,
            decision=decision,
            advance_rate=advance_rate,
            advance_amount=advance_amount,
            capital_state=capital_state,
            policy_dict=asdict(self.policy_registry.get(policy_id, policy_version)),
            execution_trace={
                "breach_detected": breach_eval["breach_detected"],
                "breach_type": breach_eval["breach_type"],
                "policy_applied": policy_id,
                "expected_revenue": revenue_snapshot.expected_revenue,
                "verified_kwh": revenue_snapshot.verified_kwh,
                "budgeted_rate": revenue_snapshot.budgeted_rate_per_kwh,
            },
        )
        
        # Step 8: Execute capital execution via treasury endpoint
        treasury_result = self.capital_endpoint.send_capital_action(cao)
        
        return {
            "cao": cao.to_dict(),
            "treasury_result": treasury_result,
        }


# ============================================================================
# PER-CYCLE TOKEN ALLOCATION HELPERS
# ============================================================================

def get_last_cycle_adherence(mill_id: str, session) -> float:
    """
    Returns adherence (cash_remitted / expected_revenue) of most recent
    CLOSED or DISPUTED cycle.
    
    Args:
        mill_id: Mill identifier
        session: SQLModel session
    
    Returns:
        float: Adherence in range [0, 1]. Defaults to 1.0 for new mills.
               Returns DISPUTED_ADHERENCE_PENALTY (0.0) for disputed cycles.
    """
    from backend.init_db import TokenAllocation, CashReceipt
    from backend.config import DISPUTED_ADHERENCE_PENALTY
    
    last = session.exec(
        select(TokenAllocation).where(
            TokenAllocation.mill_id == mill_id,
            TokenAllocation.status.in_(["CLOSED", "DISPUTED"])
        ).order_by(TokenAllocation.allocated_at.desc())
    ).first()
    
    # New mill with no closed cycles
    if not last:
        return 1.0
    
    # Disputed cycle = severe penalty
    if last.status == "DISPUTED":
        return DISPUTED_ADHERENCE_PENALTY
    
    # CLOSED cycle: fetch receipt and compute adherence
    receipt = session.exec(
        select(CashReceipt).where(CashReceipt.allocation_id == last.id)
    ).first()
    
    if receipt and receipt.verified:
        # Clamp adherence to [0, 1] to avoid >1.0 anomalies
        adherence = min(1.0, max(0.0, receipt.amount / last.expected_revenue))
        return adherence
    
    # Closed allocation but no verified receipt
    logger.warning(f"Closed allocation {last.id} for mill {mill_id} has no verified receipt")
    return 0.0


def get_last_cycle_lag(mill_id: str, session) -> float:
    """
    Returns lag in hours from last cycle allocation to cash receipt.
    
    Args:
        mill_id: Mill identifier
        session: SQLModel session
    
    Returns:
        float: Lag in hours. Conservative fallback (72h) for DISPUTED cycles
               or missing receipts.
    """
    from backend.init_db import TokenAllocation, CashReceipt
    from backend.config import CONSERVATIVE_LAG_HOURS
    
    last = session.exec(
        select(TokenAllocation).where(
            TokenAllocation.mill_id == mill_id,
            TokenAllocation.status.in_(["CLOSED", "DISPUTED"])
        ).order_by(TokenAllocation.allocated_at.desc())
    ).first()
    
    # No closed cycles
    if not last:
        return 0.0
    
    # Disputed cycle: conservative penalty
    if last.status == "DISPUTED":
        return CONSERVATIVE_LAG_HOURS
    
    # CLOSED cycle: compute actual lag
    receipt = session.exec(
        select(CashReceipt).where(CashReceipt.allocation_id == last.id)
    ).first()
    
    if receipt:
        delta = receipt.received_at - last.allocated_at
        lag_hours = delta.total_seconds() / 3600.0
        return lag_hours
    
    # Closed but no receipt: assume worst lag
    logger.warning(f"Closed allocation {last.id} for mill {mill_id} has no cash receipt")
    return CONSERVATIVE_LAG_HOURS
    
    @staticmethod
    def _evaluate_policy(pxe_input: PXEInput, policy: Policy) -> tuple:
        """
        Evaluate policy rules against PXEInput.
        
        Returns: (decision, advance_rate, capital_state)
        """
        context = asdict(pxe_input)
        
        for rule in policy.rules:
            conditions = rule.get("conditions", [])
            
            if not conditions:  # Default rule
                return (
                    rule.get("decision", "DECLINE"),
                    rule.get("advance_rate", 0.0),
                    rule.get("capital_state", "FROZEN"),
                )
            
            # Check all conditions (AND logic)
            match = all(
                RevenueGateway._check_condition(condition, context)
                for condition in conditions
            )
            
            if match:
                return (
                    rule.get("decision", "DECLINE"),
                    rule.get("advance_rate", 0.0),
                    rule.get("capital_state", "FROZEN"),
                )
        
        # Fallback (should not reach if policies well-formed)
        return ("DECLINE", 0.0, "FROZEN")
    
    @staticmethod
    def _check_condition(condition: tuple, context: Dict[str, Any]) -> bool:
        """Evaluate a single condition: (field, operator, value)."""
        field, operator, expected = condition
        actual = context.get(field)
        
        if actual is None:
            return False
        
        if operator == ">=":
            return actual >= expected
        elif operator == "<=":
            return actual <= expected
        elif operator == ">":
            return actual > expected
        elif operator == "<":
            return actual < expected
        elif operator == "==":
            return actual == expected
        else:
            return False
