#!/usr/bin/env python3
"""Quick verification of Capital Impact Layer calculations."""

from backend.trust_scorecard import TrustScorecardGenerator

def test_capital_impact_scenarios():
    gen = TrustScorecardGenerator('MILL01')

    # Test sovereign scenario
    print('=' * 60)
    print('SCENARIO 1: SOVEREIGN (Trust Score 95.0, Variance 0.8%)')
    print('=' * 60)
    capital = gen.calculate_capital_impact(95.0, 0.8)
    print(f'✓ Rate Adjustment: {capital["financing_rate_adjustment_pct"]}% ({capital["financing_rate_adjustment_bps"]} bps)')
    print(f'✓ Risk Classification: {capital["risk_classification"]}')
    print(f'✓ Capital Tier: {capital["capital_tier"]}')
    print(f'✓ Max Leverage: {capital["max_leverage_ratio"]}x')
    print(f'✓ Payback Acceleration: {capital["payback_acceleration"]}')
    print(f'✓ Audit Efficiency: {capital["audit_efficiency"]}')
    print(f'✓ Estimated Annual Savings: {capital["estimated_annual_savings_bps"]} bps')
    print(f'✓ Recommendation: {capital["recommendation"]}')
    
    assert capital['financing_rate_adjustment_pct'] == -5.0, "Should get -5% rate reduction"
    assert capital['risk_classification'] == 'INSTITUTIONAL GRADE', "Should be institutional grade"
    print('✅ All assertions passed!\n')

    # Test commercial scenario
    print('=' * 60)
    print('SCENARIO 2: COMMERCIAL (Trust Score 80.0, Variance 1.5%)')
    print('=' * 60)
    capital = gen.calculate_capital_impact(80.0, 1.5)
    print(f'✓ Rate Adjustment: {capital["financing_rate_adjustment_pct"]}% ({capital["financing_rate_adjustment_bps"]} bps)')
    print(f'✓ Risk Classification: {capital["risk_classification"]}')
    print(f'✓ Capital Tier: {capital["capital_tier"]}')
    print(f'✓ Max Leverage: {capital["max_leverage_ratio"]}x')
    print(f'✓ Payback Acceleration: {capital["payback_acceleration"]}')
    
    assert capital['financing_rate_adjustment_pct'] == -2.5, "Should get -2.5% rate reduction"
    assert capital['risk_classification'] == 'COMMERCIAL', "Should be commercial"
    assert capital['months_faster_recovery'] == 2, "Should have 2 month payback acceleration"
    print('✅ All assertions passed!\n')

    # Test subprime scenario
    print('=' * 60)
    print('SCENARIO 3: SUBPRIME (Trust Score 65.0, Variance 3.0%)')
    print('=' * 60)
    capital = gen.calculate_capital_impact(65.0, 3.0)
    print(f'✓ Rate Adjustment: {capital["financing_rate_adjustment_pct"]}% ({capital["financing_rate_adjustment_bps"]} bps)')
    print(f'✓ Risk Classification: {capital["risk_classification"]}')
    print(f'✓ Capital Tier: {capital["capital_tier"]}')
    print(f'✓ Max Leverage: {capital["max_leverage_ratio"]}x')
    print(f'✓ Recommendation: {capital["recommendation"]}')
    
    assert capital['risk_classification'] == 'SUBPRIME', "Should be subprime"
    assert 'CONDITIONAL' in capital['recommendation'], "Should have conditional recommendation"
    print('✅ All assertions passed!\n')

    # Test high-risk scenario
    print('=' * 60)
    print('SCENARIO 4: HIGH RISK (Trust Score 40.0, Variance 5.0%)')
    print('=' * 60)
    capital = gen.calculate_capital_impact(40.0, 5.0)
    print(f'✓ Rate Adjustment: {capital["financing_rate_adjustment_pct"]}% ({capital["financing_rate_adjustment_bps"]} bps) [RATE PREMIUM]')
    print(f'✓ Risk Classification: {capital["risk_classification"]}')
    print(f'✓ Capital Tier: {capital["capital_tier"]}')
    print(f'✓ Max Leverage: {capital["max_leverage_ratio"]}x')
    print(f'✓ Recommendation: {capital["recommendation"]}')
    
    assert capital['financing_rate_adjustment_pct'] == 0.5, "High risk should get rate premium"
    assert capital['risk_classification'] == 'HIGH RISK', "Should be high risk"
    assert 'DECLINE' in capital['recommendation'], "Should recommend decline"
    print('✅ All assertions passed!\n')

    print('=' * 60)
    print('CAPITAL IMPACT LAYER: ALL TESTS PASSED ✅')
    print('=' * 60)

if __name__ == '__main__':
    test_capital_impact_scenarios()
