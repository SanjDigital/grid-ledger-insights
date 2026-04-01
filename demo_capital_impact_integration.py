#!/usr/bin/env python3
"""
Capital Impact Layer Integration Example
Shows how capital impact flows through the trust scorecard to investor reports
"""

from backend.trust_scorecard import TrustScorecardGenerator
from datetime import datetime, timezone

print("=" * 80)
print("CAPITAL IMPACT LAYER - Integration Demonstration")
print("=" * 80)

# Generate capital impact directly
generator = TrustScorecardGenerator("MILL_CAPITAL_DEMO")

# For demo purposes, we'll simulate a high-trust scenario
print("SCENARIO: North Region Solar Array - Daily Reconciliation Report")
print(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

# Calculate capital impact directly
capital = generator.calculate_capital_impact(trust_score=94.0, variance_pct=0.8)

print("TECHNICAL METRICS:")
print(f"  • Trust Integrity Score: 94.0/100 (A+ Grade)")
print(f"  • Reconciliation Variance: 0.8%")
print(f"  • Physical-to-Digital Alignment: SOVEREIGN")

print("\n" + "=" * 80)
print("CAPITAL IMPACT ANALYSIS - Investor-Facing Financial Implications")
print("=" * 80)

print("\n📊 FINANCING TERMS")
print(f"  • Interest Rate Adjustment: {capital['financing_rate_adjustment_pct']}%")
print(f"  • Basis Points Reduction: {capital['financing_rate_adjustment_bps']} bps")
print(f"  • Annual Savings (on 2M MWK facility): ~{abs(capital['financing_rate_adjustment_bps']) * 200:,} MWK")

print("\n🏛️ RISK CLASSIFICATION")
print(f"  • Classification: {capital['risk_classification']}")
print(f"  • Capital Tier: {capital['capital_tier']}")
print(f"  • Maximum Leverage Ratio: {capital['max_leverage_ratio']}x")

print("\n⚙️ OPERATIONAL EFFICIENCY")
print(f"  • Audit Cost Reduction: {capital['audit_efficiency']}")
print(f"  • Annual Audit Visit Reduction: {capital['audit_visit_cost_reduction_pct']}%")
print(f"  • Payback Acceleration: {capital['payback_acceleration']}")
print(f"  • Months Faster Recovery: {capital['months_faster_recovery']}")

print("\n💰 FINANCIAL IMPACT SUMMARY")
print(f"  • Estimated Annual Savings: {capital['estimated_annual_savings_bps']} bps")
print(f"  • On 2M MWK financed amount: ~{abs(capital['estimated_annual_savings_bps']) * 200:,} MWK total savings")

print("\n📋 INVESTMENT RECOMMENDATION")
print(f"  ✅ {capital['recommendation']}")
print("\n" + "=" * 80)

print("\nKEY INSIGHTS FOR LENDER:")
print("""
The combination of:
  • SOVEREIGN trust score (94.0/100)
  • Minimal variance (0.8% - within spec)
  • Tier 1 capital classification
  
...justifies:
  • 500 basis points rate reduction (standard offer for institutional-grade assets)
  • 60% reduction in audit costs (move from monthly to quarterly verification)
  • 4-month acceleration of capital payback cycle
  • Maximum leverage authority at 3.5x equity

This asset is a prime candidate for preferred lending rate and accelerated 
funding. Lock in terms while SOVEREIGN status holds.
""")

print("=" * 80)
print("INTEGRATION: Capital Impact flows automatically from trust scorecard")
print("             into investor markdown reports for decision-making.")
print("=" * 80)
