"""
Policy Execution Engine (PXE) — Layer 4: Deterministic Capital Governance

Converts verified system state (Layers 1-3) into irreversible financial actions.

No human interpretation.
No manual override.
Identical inputs → Identical capital outcomes.

PXE is the constitution.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Literal, Any
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from copy import deepcopy


# ============================================================================
# CAPITAL ACTION OBJECT (CAO) — Locked Schema
# ============================================================================

class CreditDecision(str, Enum):
    APPROVE = "APPROVE"
    CONDITIONAL = "CONDITIONAL"
    DECLINE = "DECLINE"


class CapitalState(str, Enum):
    OPEN = "OPEN"
    CONSTRAINED = "CONSTRAINED"
    FROZEN = "FROZEN"


class AuditFrequency(str, Enum):
    NONE = "NONE"
    QUARTERLY = "QUARTERLY"
    MONTHLY = "MONTHLY"
    IMMEDIATE = "IMMEDIATE"


class CollateralRequirement(str, Enum):
    STANDARD = "STANDARD"
    ELEVATED = "ELEVATED"
    FULL = "FULL"


class EARTier(str, Enum):
    TIER_1 = "TIER_1"
    TIER_2 = "TIER_2"
    TIER_3 = "TIER_3"


class MillState(str, Enum):
    VERIFIED = "VERIFIED"
    UNDER_REVIEW = "UNDER_REVIEW"
    COMPROMISED = "COMPROMISED"
    SUSPENDED = "SUSPENDED"


@dataclass
class BreachFlags:
    """Immutable breach status, non-negotiable overrides."""
    gap_breach: bool = False
    variance_breach: bool = False
    economic_deficit: bool = False
    completeness_breach: bool = False

    def any_breach(self) -> bool:
        return any(
            [
                self.gap_breach,
                self.variance_breach,
                self.economic_deficit,
                self.completeness_breach,
            ]
        )


@dataclass
class AutoAdjustmentConfig:
    """Stateful auto-adjustment engine configuration."""
    step_up_enabled: bool = True
    step_down_enabled: bool = True
    review_cycle_days: int = 7
    stability_threshold_cycles: int = 2


@dataclass
class ExecutionTrace:
    """Audit trail of policy execution decisions."""
    breach_overrides_applied: bool = False
    policy_rules_applied: str = ""
    auto_adjustment_triggered: bool = False
    final_state: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CapitalActionObject:
    """
    Immutable directive for capital allocation.
    This object is final. External systems consume as-is.
    """

    # Identification
    mill_id: str
    timestamp: str
    policy_id: str
    policy_version: str
    policy_hash: str
    input_hash: str

    # Credit Decision
    credit_decision: CreditDecision
    approved_credit_limit: float
    advance_rate: float
    tenor_days: int
    escrow_ratio: float
    collateral_requirement: CollateralRequirement

    # Operational Controls
    audit_frequency: AuditFrequency
    capital_state: CapitalState

    # Auto-Adjustment State
    auto_adjustment: AutoAdjustmentConfig

    # Enforcement Actions
    enforcement_actions: List[str]

    # Execution Trace
    execution_trace: ExecutionTrace

    # Capital Metrics
    advance_amount: float = 0.0  # advance_rate × approved_credit_limit (Mk)
    structural_leakage_flag: bool = False  # True if entropy monitor detected leakage

    def to_dict(self) -> Dict[str, Any]:
        """Convert CAO to JSON-serializable dict."""
        data = asdict(self)
        # Convert enums to strings
        for key in [
            "credit_decision",
            "collateral_requirement",
            "audit_frequency",
            "capital_state",
        ]:
            if isinstance(data[key], Enum):
                data[key] = data[key].value
        return data

    def to_json(self) -> str:
        """Serialize CAO to JSON."""
        return json.dumps(self.to_dict(), default=str, indent=2)


# ============================================================================
# INPUT CONTRACT
# ============================================================================

@dataclass
class PXEInput:
    """Immutable input contract for PXE execution."""

    # Identity
    mill_id: str
    timestamp: str  # ISO-8601

    # Trust Scorecard Inputs
    trust_score: float  # 0-100
    reconciliation_score: float  # 0-100
    consistency_score: float  # 0-100
    governance_score: float  # 0-100

    # Revenue & Efficiency Inputs
    ear: float  # 0-1, ratio (Energy Auditable Revenue)
    ear_tier: EARTier
    dce: float  # numeric
    risk_penalty: float  # 0-1

    # State
    mill_state: MillState
    breach_flags: BreachFlags

    # Audit Reference
    event_metadata_hash: str  # Merkle root reference

    # Policy Selection
    policy_id: str
    
    # Gradual Squeeze Input (default: perfect efficiency)
    digital_efficiency: float = 1.0  # verified_deposit / expected_revenue (0-2.0)
    
    # Entropy Monitor Input (default: no penalty)
    structural_penalty_multiplier: float = 1.0  # From EntropyMonitor (0.9 if leakage detected)
    structural_leakage_flag: bool = False  # True if structural leakage detected (all-negative variance pattern)

    def validate(self) -> bool:
        """Validate input constraints."""
        errors = []

        if not self.mill_id or not isinstance(self.mill_id, str):
            errors.append("mill_id must be non-empty string")

        if not (0 <= self.trust_score <= 100):
            errors.append("trust_score must be 0-100")

        if not (0 <= self.ear <= 2.0):  # Allow >1.0 for over-reporting
            errors.append("ear must be 0-2.0")

        if not (0 <= self.risk_penalty <= 1.0):
            errors.append("risk_penalty must be 0-1.0")

        if not (0 <= self.digital_efficiency <= 2.0):
            errors.append("digital_efficiency must be 0-2.0 (verified_deposit / expected_revenue)")

        if not (0.0 < self.structural_penalty_multiplier <= 1.0):
            errors.append("structural_penalty_multiplier must be 0.0 < x <= 1.0")

        if not isinstance(self.structural_leakage_flag, bool):
            errors.append("structural_leakage_flag must be boolean")

        if not self.event_metadata_hash or not isinstance(
            self.event_metadata_hash, str
        ):
            errors.append("event_metadata_hash must be non-empty string")

        if errors:
            raise ValueError(f"PXEInput validation failed: {'; '.join(errors)}")

        return True


# ============================================================================
# GRADUAL SQUEEZE: Dynamic Advance Rate Computation
# ============================================================================

def compute_advance_rate(
    trust_score: float,
    digital_efficiency: float,
    base_rate: float = 0.5,
    mill_id: Optional[str] = None
) -> float:
    """
    Compute advance rate with squared digital efficiency penalty, starvation zone, and cumulative loss pressure.
    
    Implements "Kill the Floor Surfers" mechanism with three efficiency zones:
    
    ZONE 1: DEATH ZONE (< 50%)
        Capital flow STOPS. Operator is either stealing or operationally broken.
        No exceptions, no partial credit, no recovery until efficiency > 50%.
        Result: advance rate = 0.0
    
    ZONE 2: STARVATION ZONE (50–65%)
        Operator receives only 25% of normal calculated advance rate.
        This creates severe economic pressure: costs of operation exceed revenue,
        forcing operator to either:
        - Invest in fixing operational issues, OR
        - Voluntarily exit the system (avoiding costly bankruptcy)
        Economic purpose: Prevent comfortable "mediocrity plateau"
    
    ZONE 3: NORMAL OPERATION (≥ 65%)
        Full advance rate calculation applies. Operator has demonstrated
        sufficient efficiency to warrant normal commercial terms.
        Cumulative loss & suspicion penalties still apply in this zone.
    
    Additional Layers:
    - HARD FLOOR: Absolute circuit breaker at < 50%
    - STARVATION MULTIPLIER: 25% reduction for 50–65% efficiency range
    - CUMULATIVE LOSS PRESSURE: 30-day rolling average efficiency < 75%
    - SUSPICION SCORE: Behavioral pattern penalties (separate, stacked multiplicatively)
    
    Formula:
        1. If digital_efficiency < 0.5: return 0.0 (death zone)
        
        2. If 0.5 ≤ digital_efficiency < 0.65: 
           starvation_mult = 0.25 (severe penalty)
           Else: starvation_mult = 1.0 (normal)
        
        3. Apply cumulative loss pressure (if mill_id):
           effective_base_rate = base_rate × cumulative_penalty()
           
        4. Calculate advance rate:
           advance_rate = effective_base_rate × (trust_score / 100.0) × (efficiency²) × starvation_mult
    
    Args:
        trust_score: Operator integrity score (0-100)
        digital_efficiency: Current operational efficiency (0.0 - 2.0)
        base_rate: Maximum achievable advance rate (default: 0.5 = 50%)
        mill_id: Mill identifier for cumulative penalty lookup (optional)
    
    Returns:
        Advance rate (0.0 – base_rate with all penalties applied)
    
    Examples:
        # Death zone: below 50%
        compute_advance_rate(95.0, 0.45, 0.50, "MILL_001") 
        → 0.0 (blocked, no matter how high trust)
        
        # Starvation zone: 50–65%
        compute_advance_rate(95.0, 0.60, 0.50, "MILL_001") 
        → ~0.045 (0.50 × 0.95 × 0.36 × 0.25) [25% of normal rate]
        
        # Lower bound of starvation zone
        compute_advance_rate(95.0, 0.50, 0.50, "MILL_001") 
        → ~0.018 (barely viable, strong incentive to improve)
        
        # Normal zone: >= 65%
        compute_advance_rate(95.0, 0.65, 0.50, "MILL_001") 
        WHERE no cumulative loss
        → ~0.158 (0.50 × 0.95 × 0.4225 × 1.0) [full rate]
        
        # Normal zone with cumulative loss penalty
        compute_advance_rate(95.0, 0.85, 0.50, "MILL_001") 
        WHERE rolling avg = 70% (< 75%)
        → ~0.160 (0.25 × 0.95 × 0.7225 × 1.0) [halved from cumulative]
    """
    # ZONE 1: DEATH ZONE - Absolute circuit breaker at < 50%
    if digital_efficiency < 0.5:
        return 0.0  # No capital, no exceptions, no recovery path except fixing operations
    
    if digital_efficiency <= 0.0:
        return 0.0
    
    # ZONE 2 & 3: STARVATION vs NORMAL OPERATION
    # Determine which zone operator is in based on current efficiency
    if 0.5 <= digital_efficiency < 0.65:
        starvation_mult = 0.25  # Starvation zone: only 25% of normal rate
    else:
        starvation_mult = 1.0   # Normal zone: full rate calculation
    
    # CUMULATIVE LOSS PRESSURE: Apply rolling avg efficiency penalty to base rate
    effective_base_rate = base_rate
    if mill_id is not None:
        try:
            from backend.capital_controls import CapitalControls
            cumulative_mult = CapitalControls.cumulative_penalty(mill_id)
            effective_base_rate = base_rate * cumulative_mult
        except Exception as e:
            # If cumulative penalty lookup fails, proceed with full base rate
            # (e.g., mill not found in database, connection issues)
            # Log the error but don't block capital decision
            print(f"WARNING: cumulative_penalty lookup failed for {mill_id}: {e}")
            effective_base_rate = base_rate
    
    # Squared penalty on efficiency: drops fast at low efficiency
    efficiency_factor = digital_efficiency ** 2
    
    # Scale by trust score, apply effective base rate, and apply starvation multiplier
    effective_rate = effective_base_rate * (trust_score / 100.0) * efficiency_factor * starvation_mult
    
    # Clamp to valid range [0.0, effective_base_rate]
    return min(effective_base_rate, max(0.0, effective_rate))


# ============================================================================
# PER-CYCLE TOKEN ALLOCATION ADVANCE RATE COMPUTATION
# ============================================================================

def latency_penalty(lag_hours: float) -> float:
    """
    Returns penalty multiplier based on step function for remittance latency.
    
    Step boundaries (upper bound exclusive):
    - lag < 24h   → 1.00 (no penalty, on-time remittance)
    - 24 ≤ lag < 48h  → 0.95 (5% penalty)
    - 48 ≤ lag < 72h  → 0.90 (10% penalty)
    - lag ≥ 72h   → 0.85 (15% penalty, severe)
    
    Args:
        lag_hours: Time in hours from cycle allocation to cash receipt
    
    Returns:
        float: Penalty multiplier [0.85, 1.00]
    """
    from backend.config import LATENCY_BOUNDARIES
    
    for threshold, penalty in LATENCY_BOUNDARIES:
        if threshold is None or lag_hours < threshold:
            return penalty
    
    # Defensive fallback (should not reach due to None threshold)
    return 0.85


def compute_per_cycle_advance_rate(
    trust_score: float,
    adherence: float,
    lag_hours: float,
    base_rate: float = 0.5
) -> float:
    """
    Compute advance rate for NEXT cycle based on previous cycle performance.
    
    Formula:
        effective_rate = base_rate 
                       × (trust_score / 100) 
                       × (adherence²) 
                       × latency_penalty(lag_hours)
    
    Where:
    - trust_score: Operator integrity score (0-100)
    - adherence: Cash remitted / expected revenue (0.0-∞, typically 0.8-1.2)
    - lag_hours: Hours from cycle allocation to cash receipt
    - base_rate: Starting point before penalties (default 0.5 = 50%)
    
    Example scenarios:
    - Perfect adherence (1.0), on-time (<24h), high trust (95)
      → 0.5 × 0.95 × 1.0 × 1.0 = 0.4750 (unchanged)
    
    - Good adherence (0.95), medium latency (36h), medium trust (80)
      → 0.5 × 0.80 × 0.9025 × 0.95 = 0.3438 (-31% from base)
    
    - Fair adherence (0.90), slow latency (60h), low trust (60)
      → 0.5 × 0.60 × 0.81 × 0.90 = 0.2187 (-56% from base)
    
    - Poor adherence (0.70), very slow (96h), low trust (50)
      → 0.5 × 0.50 × 0.49 × 0.85 = 0.1041 (-79% from base)
      >> Operator sees dramatic reduction, strong incentive to improve
    
    Args:
        trust_score: Operator integrity score (0-100)
        adherence: Cash remitted / expected_revenue for last cycle
        lag_hours: Time in hours from allocation to cash receipt
        base_rate: Maximum achievable advance rate (clamped upper bound)
    
    Returns:
        float: Effective advance rate (0.0 to base_rate)
    """
    # Clamp adherence to [0, 1] to prevent >100% anomalies
    clamped_adherence = max(0.0, min(1.0, adherence))
    
    # Compute factors
    factor_trust = trust_score / 100.0
    factor_adherence = clamped_adherence ** 2  # Quadratic penalty drives behavior change
    factor_latency = latency_penalty(lag_hours)
    
    # Compute final rate
    effective_rate = base_rate * factor_trust * factor_adherence * factor_latency
    
    # Clamp to [0.0, base_rate] to ensure penalties never exceed base
    return max(0.0, min(base_rate, effective_rate))


# ============================================================================
# POLICY EXECUTION ENGINE (PURE FUNCTION)
# ============================================================================

class PolicyExecutionEngine:
    """
    Deterministic capital governance engine.
    
    Execution order:
    1. Validate inputs
    2. Apply breach overrides (sovereign)
    3. Apply policy rules
    4. Apply auto-adjustment (stateful)
    5. Emit CAO
    """

    def __init__(self):
        """Initialize PXE with default policy registry."""
        self.policies: Dict[str, Dict[str, Any]] = {}
        self._register_standard_commercial()
        self.mill_profiles: Dict[str, Dict[str, Any]] = {}  # Auto-adjustment state

    def _register_standard_commercial(self):
        """Register the canonical STANDARD_COMMERCIAL reference policy."""
        policy = {
            "policy_id": "STANDARD_COMMERCIAL",
            "version": "1.0",
            "effective_timestamp": "2026-03-29T00:00:00Z",
            "status": "ACTIVE",
            "rules": [
                {
                    "name": "SOVEREIGN_UNLOCK",
                    "priority": 1,
                    "conditions": [
                        ("trust_score", ">=", 90),
                        ("mill_state", "==", MillState.VERIFIED),
                    ],
                    "actions": {
                        "credit_decision": CreditDecision.APPROVE,
                        "advance_rate": 0.60,
                        "tenor_days": 45,
                        "escrow_ratio": 0.10,
                        "collateral_requirement": CollateralRequirement.STANDARD,
                        "audit_frequency": AuditFrequency.NONE,
                        "capital_state": CapitalState.OPEN,
                    },
                },
                {
                    "name": "COMMERCIAL_APPROVE",
                    "priority": 2,
                    "conditions": [
                        ("trust_score", ">=", 75),
                        ("trust_score", "<", 90),
                    ],
                    "actions": {
                        "credit_decision": CreditDecision.APPROVE,
                        "advance_rate": 0.50,
                        "tenor_days": 30,
                        "escrow_ratio": 0.15,
                        "collateral_requirement": CollateralRequirement.STANDARD,
                        "audit_frequency": AuditFrequency.QUARTERLY,
                        "capital_state": CapitalState.OPEN,
                    },
                },
                {
                    "name": "CONDITIONAL_CONTROL",
                    "priority": 3,
                    "conditions": [
                        ("trust_score", ">=", 60),
                        ("trust_score", "<", 75),
                    ],
                    "actions": {
                        "credit_decision": CreditDecision.CONDITIONAL,
                        "advance_rate": 0.45,
                        "tenor_days": 21,
                        "escrow_ratio": 0.25,
                        "collateral_requirement": CollateralRequirement.ELEVATED,
                        "audit_frequency": AuditFrequency.MONTHLY,
                        "capital_state": CapitalState.CONSTRAINED,
                    },
                },
                {
                    "name": "DECLINE",
                    "priority": 99,
                    "conditions": [
                        ("trust_score", "<", 60),
                    ],
                    "actions": {
                        "credit_decision": CreditDecision.DECLINE,
                        "advance_rate": 0.00,
                        "tenor_days": 0,
                        "escrow_ratio": 1.00,
                        "collateral_requirement": CollateralRequirement.FULL,
                        "audit_frequency": AuditFrequency.IMMEDIATE,
                        "capital_state": CapitalState.FROZEN,
                    },
                },
            ],
        }
        self.policies["STANDARD_COMMERCIAL"] = policy

    def register_policy(self, policy_dict: Dict[str, Any]) -> bool:
        """
        Register a new policy to the registry.
        No mutable policies — version is immutable once registered.
        """
        policy_id = policy_dict.get("policy_id")
        version = policy_dict.get("version")

        if not policy_id or not version:
            raise ValueError("Policy must have policy_id and version")

        key = f"{policy_id}:{version}"
        if key in self.policies:
            raise ValueError(
                f"Policy {key} already registered. Create a new version instead."
            )

        self.policies[key] = policy_dict
        return True

    def _hash_inputs(self, pxe_input: PXEInput) -> str:
        """Generate SHA256 hash of all PXE inputs."""
        input_dict = {
            "mill_id": pxe_input.mill_id,
            "timestamp": pxe_input.timestamp,
            "trust_score": pxe_input.trust_score,
            "reconciliation_score": pxe_input.reconciliation_score,
            "consistency_score": pxe_input.consistency_score,
            "governance_score": pxe_input.governance_score,
            "ear": pxe_input.ear,
            "ear_tier": pxe_input.ear_tier.value,
            "dce": pxe_input.dce,
            "risk_penalty": pxe_input.risk_penalty,
            "digital_efficiency": pxe_input.digital_efficiency,
            "structural_penalty_multiplier": pxe_input.structural_penalty_multiplier,
            "structural_leakage_flag": pxe_input.structural_leakage_flag,
            "mill_state": pxe_input.mill_state.value,
            "breach_flags": asdict(pxe_input.breach_flags),
            "event_metadata_hash": pxe_input.event_metadata_hash,
            "policy_id": pxe_input.policy_id,
        }
        input_json = json.dumps(input_dict, sort_keys=True)
        return hashlib.sha256(input_json.encode()).hexdigest()

    def _hash_policy(self, policy_dict: Dict[str, Any]) -> str:
        """Generate SHA256 hash of full policy definition."""
        policy_json = json.dumps(
            {
                "policy_id": policy_dict.get("policy_id"),
                "version": policy_dict.get("version"),
                "rules": policy_dict.get("rules"),
            },
            sort_keys=True,
        )
        return hashlib.sha256(policy_json.encode()).hexdigest()

    def _evaluate_condition(
        self, condition: tuple, context: Dict[str, Any]
    ) -> bool:
        """Evaluate a single condition: (field, operator, value)."""
        field_name, operator, expected_value = condition

        if field_name not in context:
            raise ValueError(f"Field {field_name} not in evaluation context")

        actual_value = context[field_name]

        # Type conversion for enum comparisons
        if isinstance(expected_value, (MillState, EARTier)):
            expected_value = expected_value

        if operator == "==":
            return actual_value == expected_value
        elif operator == "!=":
            return actual_value != expected_value
        elif operator == "<":
            return actual_value < expected_value
        elif operator == ">":
            return actual_value > expected_value
        elif operator == "<=":
            return actual_value <= expected_value
        elif operator == ">=":
            return actual_value >= expected_value
        elif operator == "IN":
            return actual_value in expected_value
        else:
            raise ValueError(f"Unknown operator: {operator}")

    def _apply_breach_overrides(
        self, pxe_input: PXEInput, actions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply breach override logic (sovereign authority).
        Breaches override all policies.
        """
        overrides_applied = False
        actions = deepcopy(actions)

        # Economic deficit: FROZEN
        if pxe_input.breach_flags.economic_deficit:
            actions["capital_state"] = CapitalState.FROZEN
            actions["advance_rate"] = 0.00
            actions["enforcement_actions"] = list(
                set(
                    actions.get("enforcement_actions", [])
                    + ["FREEZE_CREDIT", "REQUIRE_AUDIT"]
                )
            )
            overrides_applied = True

        # Gap breach: IMMEDIATE audit
        if pxe_input.breach_flags.gap_breach:
            actions["audit_frequency"] = AuditFrequency.IMMEDIATE
            actions["enforcement_actions"] = list(
                set(
                    actions.get("enforcement_actions", []) + ["REQUIRE_AUDIT"]
                )
            )
            overrides_applied = True

        # Variance breach: CONSTRAINED
        if pxe_input.breach_flags.variance_breach:
            if actions.get("capital_state") != CapitalState.FROZEN:
                actions["capital_state"] = CapitalState.CONSTRAINED
            overrides_applied = True

        return actions, overrides_applied

    def _apply_policy_rules(
        self, pxe_input: PXEInput, policy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply policy rules in priority order (second authority).
        Returns first matching rule's actions.
        """
        context = {
            "trust_score": pxe_input.trust_score,
            "reconciliation_score": pxe_input.reconciliation_score,
            "consistency_score": pxe_input.consistency_score,
            "governance_score": pxe_input.governance_score,
            "ear": pxe_input.ear,
            "ear_tier": pxe_input.ear_tier,
            "dce": pxe_input.dce,
            "risk_penalty": pxe_input.risk_penalty,
            "mill_state": pxe_input.mill_state,
        }

        rules = sorted(policy.get("rules", []), key=lambda r: r.get("priority", 99))

        for rule in rules:
            conditions = rule.get("conditions", [])
            rule_name = rule.get("name", "UNNAMED")

            # Evaluate all conditions (AND logic)
            all_match = True
            for condition in conditions:
                if not self._evaluate_condition(condition, context):
                    all_match = False
                    break

            if all_match:
                return deepcopy(rule.get("actions", {})), rule_name

        # No rule matched—should not happen with well-formed policies
        raise ValueError(
            f"No policy rule matched for mill {pxe_input.mill_id}. Policy: {policy['policy_id']}"
        )

    def _apply_auto_adjustment(
        self, mill_id: str, current_actions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply stateful auto-adjustment logic (third authority).
        This is the only stateful component of PXE.
        """
        if mill_id not in self.mill_profiles:
            self.mill_profiles[mill_id] = {
                "last_n_scores": [],
                "stability_counter": 0,
                "last_adjustment": None,
                "auto_adjustment_state": "DORMANT",
            }

        profile = self.mill_profiles[mill_id]
        actions = deepcopy(current_actions)

        # Step-down logic: immediate if trust_score dropped or breach
        # (This is handled via breach overrides, already applied)

        # Step-up logic: requires stability
        auto_adj = current_actions.get("auto_adjustment", {})
        if auto_adj.get("step_up_enabled", False):
            # Track score history
            profile["last_n_scores"].append(current_actions.get("trust_score", 0))
            profile["last_n_scores"] = profile["last_n_scores"][
                -5:
            ]  # Keep last 5

            stability_threshold = auto_adj.get("stability_threshold_cycles", 2)
            if (
                len(profile["last_n_scores"]) >= stability_threshold
                and all(s >= 90 for s in profile["last_n_scores"])
            ):
                if profile["auto_adjustment_state"] == "DORMANT":
                    profile["auto_adjustment_state"] = "QUEUED"
                    profile["stability_counter"] += 1

                if profile["stability_counter"] >= stability_threshold:
                    # Apply step-up
                    delta = 0.05
                    new_advance_rate = min(
                        actions.get("advance_rate", 0.60) + delta, 0.65
                    )
                    actions["advance_rate"] = new_advance_rate
                    profile["last_adjustment"] = datetime.now(timezone.utc).isoformat()
                    profile["auto_adjustment_state"] = "ACTIVE"
                    profile["stability_counter"] = 0

        return actions

    def execute(self, pxe_input: PXEInput) -> CapitalActionObject:
        """
        Execute PXE deterministically with dynamic advance rate computation.
        
        Execution sequence:
        1. Validate inputs
        2. Apply breach overrides
        3. Apply policy rules
        4. Apply Gradual Squeeze (dynamic advance rate)
        5. Apply auto-adjustment
        6. Emit CAO
        """

        # Step 1: Validate Inputs
        pxe_input.validate()

        # Step 2: Apply Breach Overrides (Sovereign Authority)
        initial_actions = {
            "credit_decision": CreditDecision.APPROVE,
            "advance_rate": 0.50,
            "tenor_days": 30,
            "escrow_ratio": 0.15,
            "collateral_requirement": CollateralRequirement.STANDARD,
            "audit_frequency": AuditFrequency.QUARTERLY,
            "capital_state": CapitalState.OPEN,
            "enforcement_actions": [],
            "trust_score": pxe_input.trust_score,
        }

        breach_actions, breach_overrides_applied = self._apply_breach_overrides(
            pxe_input, initial_actions
        )

        # Step 3: Apply Policy Rules (Second Authority)
        policy = self.policies.get(pxe_input.policy_id)
        if not policy:
            raise ValueError(f"Policy {pxe_input.policy_id} not found")

        policy_actions, applied_rule = self._apply_policy_rules(pxe_input, policy)

        # Merge: breach overrides take precedence
        if breach_overrides_applied:
            merged_actions = deepcopy(policy_actions)
            merged_actions.update(breach_actions)
        else:
            merged_actions = policy_actions

        # Step 4: Apply Gradual Squeeze (Dynamic Advance Rate)
        # Override policy base_rate with compute_advance_rate using digital_efficiency
        policy_base_rate = merged_actions.get("advance_rate", 0.50)
        
        # If decision is APPROVE or CONDITIONAL, apply Gradual Squeeze
        if merged_actions.get("credit_decision") in [
            CreditDecision.APPROVE,
            CreditDecision.CONDITIONAL,
        ]:
            computed_rate = compute_advance_rate(
                trust_score=pxe_input.trust_score,
                digital_efficiency=pxe_input.digital_efficiency,
                base_rate=policy_base_rate,
                mill_id=pxe_input.mill_id,
            )
            merged_actions["advance_rate"] = computed_rate

        # Step 4b: Apply Structural Penalty (Entropy Monitor)
        # Detects consistent under-reporting pattern via negative variance
        if merged_actions.get("credit_decision") in [
            CreditDecision.APPROVE,
            CreditDecision.CONDITIONAL,
        ]:
            current_rate = merged_actions.get("advance_rate", 0.0)
            penalty_multiplier = pxe_input.structural_penalty_multiplier
            penalized_rate = current_rate * penalty_multiplier
            merged_actions["advance_rate"] = penalized_rate

        # Step 5: Apply Auto-Adjustment (Third Authority, Stateful)
        final_actions = self._apply_auto_adjustment(pxe_input.mill_id, merged_actions)

        # Step 6: Emit CAO
        input_hash = self._hash_inputs(pxe_input)
        policy_hash = self._hash_policy(policy)

        execution_trace = ExecutionTrace(
            breach_overrides_applied=breach_overrides_applied,
            policy_rules_applied=applied_rule,
            auto_adjustment_triggered=False,  # TODO: detect from state change
            final_state=final_actions,
        )

        # Calculate advance_amount: advance_rate × approved_credit_limit
        approved_limit = final_actions.get("approved_credit_limit", 0.0)
        final_advance_rate = final_actions.get("advance_rate", 0.0)
        advance_amount = approved_limit * final_advance_rate

        cao = CapitalActionObject(
            mill_id=pxe_input.mill_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            policy_id=pxe_input.policy_id,
            policy_version=policy.get("version", "1.0"),
            policy_hash=policy_hash,
            input_hash=input_hash,
            credit_decision=final_actions.get(
                "credit_decision", CreditDecision.DECLINE
            ),
            approved_credit_limit=approved_limit,
            advance_rate=final_advance_rate,
            advance_amount=advance_amount,
            tenor_days=final_actions.get("tenor_days", 0),
            escrow_ratio=final_actions.get("escrow_ratio", 0.0),
            collateral_requirement=final_actions.get(
                "collateral_requirement", CollateralRequirement.FULL
            ),
            audit_frequency=final_actions.get(
                "audit_frequency", AuditFrequency.IMMEDIATE
            ),
            capital_state=final_actions.get("capital_state", CapitalState.FROZEN),
            structural_leakage_flag=pxe_input.structural_leakage_flag,
            auto_adjustment=AutoAdjustmentConfig(),
            enforcement_actions=final_actions.get("enforcement_actions", []),
            execution_trace=execution_trace,
        )

        return cao


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Initialize engine
    pxe = PolicyExecutionEngine()

    # Example 1: Perfect efficiency (100% digital conversion)
    # Expected advance rate: 0.50 × (89/100) × (1.0²) = 0.445
    print("="*60)
    print("Example 1: Perfect Digital Efficiency (100%)")
    print("="*60)
    example_perfect = PXEInput(
        mill_id="NABIWI_MKWINDA",
        timestamp=datetime.now(timezone.utc).isoformat(),
        trust_score=89.0,
        reconciliation_score=88.0,
        consistency_score=100.0,
        governance_score=95.0,
        ear=0.88,
        ear_tier=EARTier.TIER_3,
        dce=1250.0,
        risk_penalty=0.1,
        mill_state=MillState.VERIFIED,
        breach_flags=BreachFlags(
            gap_breach=False,
            variance_breach=False,
            economic_deficit=False,
            completeness_breach=False,
        ),
        event_metadata_hash="0xabc123def456...",
        policy_id="STANDARD_COMMERCIAL",
        digital_efficiency=1.0,  # 100% verified deposit / expected revenue
    )
    cao_perfect = pxe.execute(example_perfect)
    print(f"Digital Efficiency: 1.0 (100%)")
    print(f"Advance Rate: {cao_perfect.advance_rate:.4f}")
    print(f"Credit Decision: {cao_perfect.credit_decision.value}\n")

    # Example 2: 80% efficiency → squared penalty kicks in
    # Expected advance rate: 0.50 × (89/100) × (0.8²) = 0.2848
    print("="*60)
    print("Example 2: Good Digital Efficiency (80%)")
    print("="*60)
    example_good = PXEInput(
        mill_id="NABIWI_MKWINDA",
        timestamp=datetime.now(timezone.utc).isoformat(),
        trust_score=89.0,
        reconciliation_score=88.0,
        consistency_score=100.0,
        governance_score=95.0,
        ear=0.80,
        ear_tier=EARTier.TIER_3,
        dce=1250.0,
        risk_penalty=0.1,
        mill_state=MillState.VERIFIED,
        breach_flags=BreachFlags(
            gap_breach=False,
            variance_breach=False,
            economic_deficit=False,
            completeness_breach=False,
        ),
        event_metadata_hash="0xdef456ghi789...",
        policy_id="STANDARD_COMMERCIAL",
        digital_efficiency=0.80,  # 80% verified deposits
    )
    cao_good = pxe.execute(example_good)
    print(f"Digital Efficiency: 0.8 (80%)")
    print(f"Advance Rate: {cao_good.advance_rate:.4f}")
    print(f"Credit Decision: {cao_good.credit_decision.value}\n")

    # Example 3: 50% efficiency → significant penalty
    # Expected advance rate: 0.50 × (89/100) × (0.5²) = 0.11125
    print("="*60)
    print("Example 3: Poor Digital Efficiency (50%)")
    print("="*60)
    example_poor = PXEInput(
        mill_id="NABIWI_MKWINDA",
        timestamp=datetime.now(timezone.utc).isoformat(),
        trust_score=89.0,
        reconciliation_score=88.0,
        consistency_score=100.0,
        governance_score=95.0,
        ear=0.50,
        ear_tier=EARTier.TIER_3,
        dce=1250.0,
        risk_penalty=0.2,
        mill_state=MillState.VERIFIED,
        breach_flags=BreachFlags(
            gap_breach=False,
            variance_breach=False,
            economic_deficit=False,
            completeness_breach=False,
        ),
        event_metadata_hash="0xghi789jkl012...",
        policy_id="STANDARD_COMMERCIAL",
        digital_efficiency=0.50,  # 50% verified deposits
    )
    cao_poor = pxe.execute(example_poor)
    print(f"Digital Efficiency: 0.5 (50%)")
    print(f"Advance Rate: {cao_poor.advance_rate:.4f}")
    print(f"Credit Decision: {cao_poor.credit_decision.value}\n")

    # Example 4: Zero efficiency → immediate freeze
    # Expected advance rate: 0.50 × (89/100) × (0.0²) = 0.0
    print("="*60)
    print("Example 4: Zero Digital Efficiency (0%)")
    print("="*60)
    example_zero = PXEInput(
        mill_id="NABIWI_MKWINDA",
        timestamp=datetime.now(timezone.utc).isoformat(),
        trust_score=89.0,
        reconciliation_score=88.0,
        consistency_score=100.0,
        governance_score=95.0,
        ear=0.0,
        ear_tier=EARTier.TIER_3,
        dce=0.0,
        risk_penalty=1.0,
        mill_state=MillState.VERIFIED,
        breach_flags=BreachFlags(
            gap_breach=False,
            variance_breach=False,
            economic_deficit=False,
            completeness_breach=False,
        ),
        event_metadata_hash="0xjkl012mno345...",
        policy_id="STANDARD_COMMERCIAL",
        digital_efficiency=0.0,  # 0% verified deposits
    )
    cao_zero = pxe.execute(example_zero)
    print(f"Digital Efficiency: 0.0 (0%)")
    print(f"Advance Rate: {cao_zero.advance_rate:.4f}")
    print(f"Credit Decision: {cao_zero.credit_decision.value}\n")

    print("="*60)
    print("Gradual Squeeze Summary:")
    print("="*60)
    print(f"100% efficiency → {cao_perfect.advance_rate:.1%} advance rate")
    print(f"80% efficiency  → {cao_good.advance_rate:.1%} advance rate (squared penalty)")
    print(f"50% efficiency  → {cao_poor.advance_rate:.1%} advance rate (rapid drop)")
    print(f"0% efficiency   → {cao_zero.advance_rate:.1%} advance rate (frozen)")

