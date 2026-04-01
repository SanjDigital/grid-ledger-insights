"""
Bounded Imperfection Doctrine – EAR Threshold Configuration.

This module defines the EAR (Energy Accountability Ratio) thresholds that recognize
realistic accounting practices under operational constraints. Rather than requiring
perfect 100% accountability, we establish bounded ranges that reflect:

1. Metering system measurement error margins (±0.5-1% typical)
2. Real-world leakage, spillage, and system losses
3. Legitimate operational discrepancies in energy distribution

The doctrine: EAR < 1.0 can still be ACCEPTABLE if within threshold ranges.
This prevents the overly-strict "all-or-nothing" penalty for minor discrepancies.
"""

from enum import Enum
from dataclasses import dataclass


@dataclass
class EARTierConfig:
    """Configuration for a single EAR tier."""
    name: str                          # "FULL_CREDIT", "CONDITIONAL", "RESTRICTED"
    min_ear: float                     # Minimum EAR for this tier
    max_ear: float                     # Maximum EAR for this tier (exclusive if not final)
    description: str                   # Human-readable description
    dce_multiplier: float              # Impact on DCE calculation (1.0 = no penalty)
    credit_classification: str         # For classification in reports


class EARTier(Enum):
    """Energy Accountability Ratio tier classification."""
    
    # Tier 1: Full Credit Unlock
    # EAR >= 95% indicates excellent metering accuracy and accountability.
    # Minimal measurement error, no significant losses, strong operational control.
    FULL_CREDIT = EARTierConfig(
        name="FULL_CREDIT_UNLOCK",
        min_ear=0.95,
        max_ear=1.01,  # Allows for rounding > 1.0
        description="Full credit unlock: Perfect accountability (EAR >= 95%)",
        dce_multiplier=1.0,
        credit_classification="EXCELLENT"
    )
    
    # Tier 2: Conditional Financeable
    # 90% <= EAR < 95% indicates acceptable accounting with minor discrepancies.
    # Typical measurement error or small system losses (1-5% normal in distribution).
    # Still provides good credit capacity but with monitoring.
    CONDITIONAL = EARTierConfig(
        name="CONDITIONAL_FINANCEABLE",
        min_ear=0.90,
        max_ear=0.95,
        description="Conditional financeable: Acceptable accountability (90% <= EAR < 95%)",
        dce_multiplier=0.95,
        credit_classification="ACCEPTABLE"
    )
    
    # Tier 3: Restricted
    # EAR < 90% indicates material discrepancies that warrant caution.
    # Could indicate measurement issues, policy leakage, or reporting problems.
    # Triggers credit restrictions and elevated monitoring.
    RESTRICTED = EARTierConfig(
        name="RESTRICTED",
        min_ear=0.0,
        max_ear=0.90,
        description="Restricted: Low accountability (EAR < 90%) - energy loss/discrepancy",
        dce_multiplier=0.80,
        credit_classification="CONCERNING"
    )


def get_ear_tier(ear: float) -> EARTierConfig:
    """
    Determine EAR tier based on ratio value.
    
    Args:
        ear: Energy Accountability Ratio (0.0 to 1.0+)
    
    Returns:
        EARTierConfig for the tier this EAR falls into
    """
    ear = min(1.0, max(0.0, ear))  # Normalize to [0, 1]
    
    for tier in [EARTier.FULL_CREDIT, EARTier.CONDITIONAL, EARTier.RESTRICTED]:
        config = tier.value
        if config.min_ear <= ear < config.max_ear:
            return config
    
    # Default to RESTRICTED if no match (shouldn't happen)
    return EARTier.RESTRICTED.value


def get_ear_interpretation(ear: float) -> str:
    """
    Get human-readable interpretation of EAR value.
    
    Args:
        ear: Energy Accountability Ratio
    
    Returns:
        Interpretation string for reporting
    """
    tier = get_ear_tier(ear)
    
    if ear >= 0.95:
        return f"{tier.description} (actual: {ear:.2%})"
    elif ear >= 0.90:
        return f"{tier.description} (actual: {ear:.2%})"
    else:
        return f"{tier.description} (actual: {ear:.2%})"


def apply_ear_dce_adjustment(dce: float, ear: float) -> float:
    """
    Apply EAR-based adjustment to DCE calculation.
    
    Under Bounded Imperfection Doctrine, EAR below 1.0 still allows credit
    but with a multiplier penalty based on the tier.
    
    Args:
        dce: Base DCE value
        ear: Energy Accountability Ratio
    
    Returns:
        Adjusted DCE value
    """
    tier = get_ear_tier(ear)
    adjusted_dce = dce * tier.dce_multiplier
    
    return adjusted_dce


# Capital tier thresholds (unchanged - these already use bounded ranges)
CAPITAL_TIER_THRESHOLDS = {
    "TIER_1_INSTITUTIONAL": {
        "dce_pct_min": 0.60,
        "ear_min": 0.95,
        "breach_count_max": 0,
        "description": "Excellent accountability and track record"
    },
    "TIER_2_COMMERCIAL": {
        "dce_pct_min": 0.40,
        "ear_min": 0.85,
        "breach_count_max": None,
        "description": "Stable performance with acceptable variance"
    },
    "TIER_3_SUBPRIME": {
        "dce_pct_min": 0.20,
        "ear_min": 0.70,
        "breach_count_max": None,
        "description": "Acceptable but with elevated monitoring"
    },
    "TIER_4_RESTRICTED": {
        "dce_pct_min": 0.0,
        "ear_min": 0.0,
        "breach_count_max": None,
        "description": "Restricted lending due to weak DCE or accountability"
    }
}


def validate_ear(ear: float, min_threshold: float = 0.0, max_threshold: float = 1.0) -> bool:
    """
    Validate EAR is within acceptable range.
    
    Args:
        ear: Energy Accountability Ratio to validate
        min_threshold: Minimum acceptable value (default 0.0)
        max_threshold: Maximum acceptable value (default 1.0)
    
    Returns:
        True if EAR is valid, False otherwise
    """
    return min_threshold <= ear <= max_threshold


def ear_status_summary(ear: float) -> dict:
    """
    Generate comprehensive status summary for an EAR value.
    
    Args:
        ear: Energy Accountability Ratio
    
    Returns:
        Dict with tier, interpretation, adjustment factor, and recommendation
    """
    tier = get_ear_tier(ear)
    
    return {
        "ear_value": round(ear, 4),
        "ear_percentage": round(ear * 100, 2),
        "tier": tier.name,
        "tier_description": tier.description,
        "credit_classification": tier.credit_classification,
        "dce_adjustment_factor": tier.dce_multiplier,
        "acceptable": ear >= 0.90,  # Anything >= 90% is acceptable
        "recommendation": (
            "Optimal performance: No action needed"
            if ear >= 0.95
            else "Monitor closely: Within acceptable range but trending downward"
            if ear >= 0.90
            else "Action required: Investigate source of discrepancy"
        ),
    }
