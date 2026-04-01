# Bounded Imperfection Doctrine – EAR Thresholds

**Status**: ✅ IMPLEMENTED
**Date**: March 29, 2026
**Module**: `backend/ear_thresholds.py`
**Integration**: Capital Controls, API Reports, Trust Scorecard

## Overview

The **Bounded Imperfection Doctrine** replaces the unrealistic "EAR must equal 1.0" requirement with practical, bounded ranges that recognize real-world operational realities:

- **Metering system accuracy**: ±0.5-1% measurement error is normal
- **Physical losses**: Natural leakage, spillage, distribution inefficiencies (1-5%)
- **Operational discrepancies**: Legitimate rounding, timing differences, legitimate accounting adjustments

**Key Principle**: EAR < 1.0 can still be FULLY ACCEPTABLE if within established thresholds.

## Three-Tier EAR Classification

### Tier 1: FULL_CREDIT_UNLOCK (EAR ≥ 95%)
**Interpretation**: Excellent accountability with minimal discrepancies

**Criteria**:
- EAR >= 0.95 (95% or better)
- Indicates metering accuracy and strong operational control
- Minimal measurement error, negligible system losses

**Credit Impact**:
- DCE adjusted with multiplier = 1.0 (no penalty)
- Eligible for TIER_1_INSTITUTIONAL financing
- Favorable interest rate adjustments (-500 to -250 bps)
- Most favorable lending conditions available

**Example**:
```
100 kWh metered, 98 kWh reported
EAR = 98/100 = 0.98 (98%) → FULL_CREDIT_UNLOCK
→ No DCE adjustment
→ Optimal financing terms available
```

### Tier 2: CONDITIONAL_FINANCEABLE (90% ≤ EAR < 95%)
**Interpretation**: Acceptable accountability within normal operational variance

**Criteria**:
- 0.90 <= EAR < 0.95 (90-94.99% accountability)
- Indicates typical metering accuracy with expected system losses
- Within 1-5% normal loss range for energy distribution
- Still provides good credit capacity

**Credit Impact**:
- DCE adjusted with multiplier = 0.95 (5% penalty)
- Eligible for TIER_2_COMMERCIAL financing
- Standard commercial lending terms
- Requires quarterly monitoring

**Example**:
```
100 kWh metered, 92 kWh reported
EAR = 92/100 = 0.92 (92%) → CONDITIONAL_FINANCEABLE
→ DCE reduced by 5%
→ Standard commercial financing available
→ Monthly accountability review recommended
```

### Tier 3: RESTRICTED (EAR < 90%)
**Interpretation**: Material discrepancies requiring investigation

**Criteria**:
- EAR < 0.90 (below 90% accountability)
- Indicates potential measurement issues, excessive losses, or reporting problems
- Warrants elevated scrutiny and corrective action

**Credit Impact**:
- DCE adjusted with multiplier = 0.80 (20% penalty)
- Eligible only for TIER_3_SUBPRIME or TIER_4_RESTRICTED financing
- Restricted lending conditions
- Requires immediate investigation and root cause analysis

**Example**:
```
100 kWh metered, 80 kWh reported
EAR = 80/100 = 0.80 (80%) → RESTRICTED
→ DCE reduced by 20%
→ Subprime or restricted financing only
→ Immediate action required: investigate source of 20% discrepancy
```

## Implementation Details

### Module: backend/ear_thresholds.py

**Key Functions**:

```python
get_ear_tier(ear: float) -> EARTierConfig
    Returns the tier configuration for a given EAR value

get_ear_interpretation(ear: float) -> str
    Returns human-readable tier description with actual EAR value

apply_ear_dce_adjustment(dce: float, ear: float) -> float
    Applies DCE multiplier penalty based on EAR tier

ear_status_summary(ear: float) -> dict
    Returns comprehensive status summary including:
    - Tier name and classification
    - Acceptable/concerning indicator
    - DCE adjustment factor
    - Actionable recommendation
```

### Integration Points

#### 1. Capital Controls (backend/capital_controls.py)
**Before**:
```python
if ear < 0.8:
    reasons.append(f"Low accountability: EAR={ear:.2%}")
elif ear == 1.0:
    reasons.append(f"Perfect accountability: EAR=100%")
```

**After**:
```python
ear_interpretation = get_ear_interpretation(ear)
reasons.append(ear_interpretation)
```

Result: DCE rationale now reflects bounded tiers instead of binary pass/fail.

#### 2. API Reports (backend/api_reports.py)
**New Endpoint**: `GET /api/v1/mills/{mill_id}/accountability/ear`

Returns:
```json
{
  "mill_id": "M001",
  "mill_name": "Mkwinda Mill",
  "current_ear": {
    "ear_value": 0.9200,
    "ear_percentage": 92.00,
    "tier": "CONDITIONAL_FINANCEABLE",
    "tier_description": "Conditional financeable: Acceptable accountability (90% <= EAR < 95%)",
    "credit_classification": "ACCEPTABLE",
    "dce_adjustment_factor": 0.95,
    "acceptable": true,
    "recommendation": "Monitor closely: Within acceptable range but trending downward"
  },
  "history_5_days": [
    {
      "date": "2026-03-24T00:00:00Z",
      "ear": 0.9100,
      "tier": "CONDITIONAL_FINANCEABLE"
    },
    {
      "date": "2026-03-25T00:00:00Z",
      "ear": 0.9200,
      "tier": "CONDITIONAL_FINANCEABLE"
    }
  ],
  "thresholds": {
    "full_credit_unlock": "EAR >= 95%",
    "conditional_financeable": "90% <= EAR < 95%",
    "restricted": "EAR < 90%"
  },
  "note": "Bounded Imperfection Doctrine: EAR below 100% is acceptable if within tier thresholds"
}
```

#### 3. Trust Scorecard (backend/trust_scorecard.py)
**Updated Verdicts**:
- Green/Sovereign: "Minor discrepancies acceptable under bounded imperfection doctrine"
- Yellow/Stable: "EAR below 100% is normal. Monitor trends"
- Orange/Caution: "Verify EAR is above 90% (acceptable threshold)"
- Red/Warning: "EAR likely below 90% (restricted threshold)"

## DCE Impact

The Bounded Imperfection Doctrine applies DCE multipliers based on EAR tier:

```
Base DCE calculation: α × VR × EAR × (1 − RiskPenalty)

With EAR tier adjustment:
- EAR >= 95%: DCE_adjusted = DCE_base × 1.00  (no penalty)
- 90% <= EAR < 95%: DCE_adjusted = DCE_base × 0.95  (5% reduction)
- EAR < 90%: DCE_adjusted = DCE_base × 0.80  (20% reduction)
```

**Example**:
```
Mill data:
- VR (Verified Revenue) = 1,000,000 MK
- EAR = 92%
- RiskPenalty = 0.10 (low, 1 breach in 30 days)
- Alpha = 0.6

Base DCE = 0.6 × 1,000,000 × 0.92 × (1 - 0.10)
         = 0.6 × 1,000,000 × 0.92 × 0.90
         = 496,800 MK

With EAR tier adjustment (Tier 2: CONDITIONAL_FINANCEABLE):
Adjusted DCE = 496,800 × 0.95
             = 471,960 MK

Result: 5% reduction from base DCE due to 92% EAR
```

## Capital Tier Eligibility

The doctrine ensures EAR is considered alongside other factors:

| Tier | Minimum DCE | Minimum EAR | Status | Financing |
|------|-------------|------------|--------|-----------|
| TIER_1_INSTITUTIONAL | 60% of VR | 95% | EXCELLENT | 3.5x leverage, -500 bps |
| TIER_2_COMMERCIAL | 40% of VR | 85% | ACCEPTABLE | 2.5x leverage, -250 bps |
| TIER_3_SUBPRIME | 20% of VR | 70% | CONCERNING | 1.5x leverage, 0 bps |
| TIER_4_RESTRICTED | < 20% of VR | < 70% | POOR | 1.0x leverage, +300 bps |

**Note**: Under Bounded Imperfection, even mills with EAR = 92% (CONDITIONAL_FINANCEABLE) can reach TIER_1_INSTITUTIONAL if they have strong DCE and zero breaches.

## Operational Guidance

### For Operations Teams
1. **Target EAR ≥ 95%**: Aim for Full Credit Unlock tier (no penalties)
2. **Monitor 90-95% range**: If EAR falls into Conditional tier, investigate root cause
3. **Act on < 90%**: Trigger immediate review and corrective action plan

### For Credit Officers
1. **Verify EAR tier** before financing decisions
2. **Apply DCE multipliers** based on tier (not arbitrary penalties)
3. **Consider trend**, not just current value (improving from 85% → 92% is positive)
4. **Look for root causes**: Is it metering error? Physical loss? Accounting issue?

### For Investors
1. **EAR below 100% is expected** - this is normal operational reality
2. **Anything ≥ 90% is acceptable** under bounded imperfection doctrine
3. **Compare to peers** - some industries have 5-8% normal loss rates
4. **Track trend** - improving EAR is more important than absolute value

## Testing & Validation

All three tiers validated with example scenarios:

```python
# Full Credit
ear = 0.98 → FULL_CREDIT_UNLOCK, acceptable=True, multiplier=1.00
# Conditional
ear = 0.92 → CONDITIONAL_FINANCEABLE, acceptable=True, multiplier=0.95
# Restricted
ear = 0.85 → RESTRICTED, acceptable=False, multiplier=0.80
```

## Related Documentation

- See [CAPITAL_CONTROLS_GUIDE.md](CAPITAL_CONTROLS_GUIDE.md) for DCE calculations
- See [DEPLOYMENT_READY.md](DEPLOYMENT_READY.md) for capital tier thresholds
- See [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md) for system architecture

## Future Enhancements

1. **Dynamic thresholds**: Adjust EAR tiers based on industry/region benchmarks
2. **Improvement tracking**: Monitor EAR trend and reward improvements
3. **Remediation path**: Auto-restore credit when EAR crosses back above 90%
4. **Peer comparison**: Show how mill EAR compares to operational peers
5. **Root cause analysis**: Automated investigation to identify EAR drivers (metering vs loss vs accounting)

## Summary

The Bounded Imperfection Doctrine recognizes that perfect energy accountability (EAR = 1.0) is unrealistic. Instead, it establishes three transparent tiers:

- **≥95%**: Excellence - full credit access, no penalties
- **90-94%**: Acceptable - conditional credit access, minor adjustments, close monitoring
- **<90%**: Concerning - restricted credit, investigation required

This approach balances practical realities with financial prudence, enabling sustainable lending while maintaining accountability.
