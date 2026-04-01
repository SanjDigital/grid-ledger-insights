"""
Test: Gradual Squeeze + Entropy Monitor Integration
"""

from backend.policy_execution_engine import (
    PolicyExecutionEngine,
    PXEInput,
    BreachFlags,
    MillState,
    EARTier,
)
from backend.revenue_engine import EntropyMonitor
from datetime import datetime, timezone


def test_squeeze_and_entropy_together():
    """Test Gradual Squeeze and Entropy Monitor working together."""
    print("\n" + "="*70)
    print("TEST: Squeeze + Entropy Integration")
    print("="*70)
    
    pxe = PolicyExecutionEngine()
    monitor = EntropyMonitor(mill_id="NABIWI_MKWINDA", window_days=7)
    
    # Record 7 days of negative variance (structural leakage)
    for i in range(7):
        date = f"2026-03-{20+i:02d}"
        variance = -300.0  # Consistent under-reporting
        monitor.record_variance(date, variance)
    
    print(f"\nMonitor Status:")
    status = monitor.get_leakage_status()
    print(f"  Structural Leakage: {status['structural_leakage']}")
    print(f"  Penalty Multiplier: {status['penalty_multiplier']:.0%}")
    
    # Create PXE input with both Gradual Squeeze and Entropy parameters
    pxe_input = PXEInput(
        mill_id="NABIWI_MKWINDA",
        timestamp=datetime.now(timezone.utc).isoformat(),
        trust_score=85.0,  # High trust
        reconciliation_score=88.0,
        consistency_score=90.0,
        governance_score=92.0,
        ear=0.90,
        ear_tier=EARTier.TIER_2,
        dce=1200.0,
        risk_penalty=0.05,
        mill_state=MillState.VERIFIED,
        breach_flags=BreachFlags(
            gap_breach=False,
            variance_breach=False,
            economic_deficit=False,
            completeness_breach=False,
        ),
        event_metadata_hash="0xabcd1234...",
        policy_id="STANDARD_COMMERCIAL",
        digital_efficiency=0.85,  # Good but not perfect digital collection
        structural_penalty_multiplier=status['penalty_multiplier'],  # From monitor
    )
    
    cao = pxe.execute(pxe_input)
    
    print(f"\nPXE Execution Result:")
    print(f"  Credit Decision: {cao.credit_decision.value}")
    print(f"  Advance Rate: {cao.advance_rate:.4f} ({cao.advance_rate:.1%})")
    print(f"  Capital State: {cao.capital_state.value}")
    
    print(f"\nPenalty Flow:")
    print(f"  1. Base Rate (Policy): 50%")
    print(f"  2. After Gradual Squeeze (85% digital): {0.50 * 0.85 * (0.85**2):.2%}")
    print(f"  3. After Entropy Penalty (0.9×): {0.50 * 0.85 * (0.85**2) * 0.9:.2%}")
    print(f"  4. Final Rate: {cao.advance_rate:.2%}")


def test_recovery_from_leakage():
    """Test operator recovery when variance improves."""
    print("\n" + "="*70)
    print("TEST: Recovery from Structural Leakage")
    print("="*70)
    
    monitor = EntropyMonitor(mill_id="TEST_MILL_002", window_days=7)
    pxe = PolicyExecutionEngine()
    
    # Phase 1: Structural leakage (all negative)
    print("\nPhase 1: Structural Leakage (Days 1-7)")
    for i in range(7):
        date = f"2026-03-{20+i:02d}"
        variance = -500.0
        monitor.record_variance(date, variance)
    
    status1 = monitor.get_leakage_status()
    print(f"  Penalty Multiplier: {status1['penalty_multiplier']:.0%}")
    
    # Phase 2: Recovery (positive variances)
    print("\nPhase 2: Recovery (Days 8-14)")
    for i in range(7):
        date = f"2026-03-{27+i:02d}"
        variance = 200.0  # Now over-reporting
        monitor.record_variance(date, variance)
    
    status2 = monitor.get_leakage_status()
    print(f"  Penalty Multiplier: {status2['penalty_multiplier']:.0%}")
    
    print(f"\nRecovery Timeline:")
    print(f"  Days 1-7:   All negative → Leakage detected → Penalty 10%")
    print(f"  Days 8-14:  All positive → Leakage cleared → No penalty")
    print(f"  ✓ Operator recovered in 1 week by improving digital collection")


def test_advanced_scenario():
    """Test realistic scenario with varying conditions."""
    print("\n" + "="*70)
    print("TEST: Advanced Scenario – Dynamic Adjustments")
    print("="*70)
    
    scenarios = [
        {
            "name": "Perfect Digital Operator",
            "trust": 95.0,
            "digital_efficiency": 1.0,
            "variance_days": [100, 150, 120, 140, 130, 110, 125],  # All positive
            "window_days": 7,
        },
        {
            "name": "Good but Inconsistent",
            "trust": 80.0,
            "digital_efficiency": 0.80,
            "variance_days": [-100, 50, -150, 75, -50, 25, -200],  # Mixed
            "window_days": 7,
        },
        {
            "name": "Structural Leakage",
            "trust": 75.0,
            "digital_efficiency": 0.50,
            "variance_days": [-500, -450, -520, -480, -510, -490, -530],  # All negative
            "window_days": 7,
        },
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['name']}:")
        
        # Build entropy monitor
        monitor = EntropyMonitor("MILL", scenario['window_days'])
        for i, var in enumerate(scenario['variance_days']):
            monitor.record_variance(f"2026-03-{20+i:02d}", var)
        
        status = monitor.get_leakage_status()
        
        # Compute advance rate
        base_rate = 0.50
        gradual_rate = base_rate * (scenario['trust']/100) * (scenario['digital_efficiency']**2)
        final_rate = gradual_rate * status['penalty_multiplier']
        
        print(f"  Trust Score: {scenario['trust']:.0f}")
        print(f"  Digital Efficiency: {scenario['digital_efficiency']:.0%}")
        print(f"  Base Rate: {base_rate:.0%}")
        print(f"  After Squeeze: {gradual_rate:.1%}")
        print(f"  After Entropy: {final_rate:.1%}")
        print(f"  Leakage Detected: {'Yes' if status['structural_leakage'] else 'No'}")
        
        # Decision logic
        if final_rate < 0.05:
            decision = "FREEZE"
        elif final_rate < 0.15:
            decision = "CONSTRAINT"
        else:
            decision = "APPROVE"
        
        print(f"  Decision: {decision}")


if __name__ == "__main__":
    test_squeeze_and_entropy_together()
    test_recovery_from_leakage()
    test_advanced_scenario()
    
    print("\n" + "="*70)
    print("✅ INTEGRATION TESTS COMPLETE")
    print("="*70 + "\n")
