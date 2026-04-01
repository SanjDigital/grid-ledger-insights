#!/usr/bin/env python3
"""Validate Capital Impact Layer implementation."""

from backend.trust_scorecard import TrustScorecardGenerator

gen = TrustScorecardGenerator('MILL01')

print("=" * 70)
print("CAPITAL IMPACT LAYER - QUICK VALIDATION")
print("=" * 70)

# Scenario 1: Sovereign
capital = gen.calculate_capital_impact(95.0, 0.8)
print("\n✓ SCENARIO 1: Sovereign (95.0 score, 0.8% variance)")
print(f"  - Rate Adjustment: {capital['financing_rate_adjustment_pct']}% ({capital['financing_rate_adjustment_bps']} bps)")
print(f"  - Risk Classification: {capital['risk_classification']}")
print(f"  - Capital Tier: {capital['capital_tier']}")
print(f"  - Max Leverage: {capital['max_leverage_ratio']}x")
print(f"  - Payback Acceleration: {capital['payback_acceleration']}")
print(f"  - Annual Savings: {capital['estimated_annual_savings_bps']} bps")
assert capital['financing_rate_adjustment_pct'] == -5.0
assert capital['risk_classification'] == 'INSTITUTIONAL GRADE'

# Scenario 2: Commercial
capital = gen.calculate_capital_impact(80.0, 1.5)
print("\n✓ SCENARIO 2: Commercial (80.0 score, 1.5% variance)")
print(f"  - Rate Adjustment: {capital['financing_rate_adjustment_pct']}% ({capital['financing_rate_adjustment_bps']} bps)")
print(f"  - Risk Classification: {capital['risk_classification']}")
print(f"  - Max Leverage: {capital['max_leverage_ratio']}x")
print(f"  - Payback Acceleration: {capital['payback_acceleration']}")
assert capital['financing_rate_adjustment_pct'] == -2.5
assert capital['risk_classification'] == 'COMMERCIAL'
assert capital['months_faster_recovery'] == 2

# Scenario 3: Subprime
capital = gen.calculate_capital_impact(65.0, 3.0)
print("\n✓ SCENARIO 3: Subprime (65.0 score, 3.0% variance)")
print(f"  - Rate Adjustment: {capital['financing_rate_adjustment_pct']}% ({capital['financing_rate_adjustment_bps']} bps)")
print(f"  - Risk Classification: {capital['risk_classification']}")
print(f"  - Max Leverage: {capital['max_leverage_ratio']}x")
assert capital['risk_classification'] == 'SUBPRIME'
assert capital['capital_tier'] == 'Tier 3'

# Scenario 4: High Risk
capital = gen.calculate_capital_impact(40.0, 5.0)
print("\n✓ SCENARIO 4: High Risk (40.0 score, 5.0% variance)")
print(f"  - Rate Adjustment: {capital['financing_rate_adjustment_pct']}% ({capital['financing_rate_adjustment_bps']} bps) [PREMIUM]")
print(f"  - Risk Classification: {capital['risk_classification']}")
print(f"  - Max Leverage: {capital['max_leverage_ratio']}x")
print(f"  - Recommendation: {capital['recommendation']}")
assert capital['financing_rate_adjustment_pct'] == 0.5
assert capital['risk_classification'] == 'HIGH RISK'
assert 'DECLINE' in capital['recommendation']

print("\n" + "=" * 70)
print("✅ CAPITAL IMPACT LAYER VERIFIED - All scenarios working correctly")
print("=" * 70)
