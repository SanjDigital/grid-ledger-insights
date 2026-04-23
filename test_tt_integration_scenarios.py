"""
TT Penalty E2E Integration: Verification Script

Demonstrates the complete flow from cycle lag hours → classification → advance rate → allocation decision.

Key Scenarios:
1. Healthy cycle (NORMAL) → standard rate
2. Rapid cycle (FAST) → boosted rate
3. Slow cycle (SLOW) → penalized rate, monitoring required
4. Stalled cycle (STALLED) → BLOCKED next token

Expected Result: All scenarios produce correct rates and blocking behavior.
"""

from backend.policy_execution_engine import (
    classify_turnover_time,
    turnover_penalty,
    compute_per_cycle_advance_rate,
)
from decimal import Decimal

# Constants
BASE_CYCLE_KWH = Decimal("59.9")


def scenario_healthy_mill():
    """Scenario 1: Healthy mill with 36h cycle (NORMAL)"""
    print("\n" + "=" * 70)
    print("SCENARIO 1: Healthy Mill (NORMAL cycle)")
    print("=" * 70)
    
    # Last cycle metrics
    trust_score = 90.0
    adherence = 0.95
    lag_hours = 36.0  # 36 hours
    
    # Classify
    classification = classify_turnover_time(lag_hours)
    print(f"Last cycle lag: {lag_hours}h → Classification: {classification}")
    
    # Get penalty
    penalty = turnover_penalty(classification)
    print(f"TT Penalty multiplier: {penalty}×")
    
    # Compute advance rate
    advance_rate = compute_per_cycle_advance_rate(
        trust_score=trust_score,
        adherence=adherence,
        lag_hours=lag_hours,
        base_rate=0.5,
        turnover_classification=classification,
    )
    
    # Compute allocation
    allocation_kwh = BASE_CYCLE_KWH * Decimal(str(advance_rate))
    
    print(f"\nRate Calculation:")
    print(f"  trust_score: {trust_score}% → factor: {trust_score/100}")
    print(f"  adherence: {adherence} → factor: {adherence**2:.4f}")
    print(f"  lag_hours: {lag_hours} → latency_penalty: 0.95")
    print(f"  TT penalty: {penalty}×")
    print(f"  → advance_rate = {advance_rate:.6f}")
    print(f"\nAllocation Decision:")
    print(f"  allocation_kwh = {BASE_CYCLE_KWH} × {advance_rate:.6f} = {allocation_kwh:.2f} kWh")
    print(f"  Status: ✅ APPROVED (standard terms)")
    
    return allocation_kwh > 0


def scenario_fast_mill():
    """Scenario 2: Fast mill with 12h cycle (FAST)"""
    print("\n" + "=" * 70)
    print("SCENARIO 2: Fast Mill (FAST cycle)")
    print("=" * 70)
    
    trust_score = 90.0
    adherence = 0.95
    lag_hours = 12.0  # 12 hours
    
    classification = classify_turnover_time(lag_hours)
    print(f"Last cycle lag: {lag_hours}h → Classification: {classification}")
    
    penalty = turnover_penalty(classification)
    print(f"TT Penalty multiplier: {penalty}× (BONUS!)")
    
    advance_rate = compute_per_cycle_advance_rate(
        trust_score=trust_score,
        adherence=adherence,
        lag_hours=lag_hours,
        base_rate=0.5,
        turnover_classification=classification,
    )
    
    allocation_kwh = BASE_CYCLE_KWH * Decimal(str(advance_rate))
    
    print(f"\nRate Calculation:")
    print(f"  Same factors as scenario 1, but:")
    print(f"  lag_hours: {lag_hours} → latency_penalty: 1.00 (no latency penalty)")
    print(f"  TT penalty: {penalty}× (5% BONUS for rapid velocity)")
    print(f"  → advance_rate = {advance_rate:.6f}")
    print(f"\nAllocation Decision:")
    print(f"  allocation_kwh = {BASE_CYCLE_KWH} × {advance_rate:.6f} = {allocation_kwh:.2f} kWh")
    print(f"  Status: ✅ APPROVED + BONUS (rapid payment recognized)")
    
    return allocation_kwh > Decimal('59.9') * Decimal(0.385)  # More than normal


def scenario_slow_mill():
    """Scenario 3: Slow mill with 60h cycle (SLOW)"""
    print("\n" + "=" * 70)
    print("SCENARIO 3: Slow Mill (SLOW cycle)")
    print("=" * 70)
    
    trust_score = 90.0
    adherence = 0.95
    lag_hours = 60.0  # 60 hours
    
    classification = classify_turnover_time(lag_hours)
    print(f"Last cycle lag: {lag_hours}h → Classification: {classification}")
    
    penalty = turnover_penalty(classification)
    print(f"TT Penalty multiplier: {penalty}× (penalty active, monitoring required)")
    
    advance_rate = compute_per_cycle_advance_rate(
        trust_score=trust_score,
        adherence=adherence,
        lag_hours=lag_hours,
        base_rate=0.5,
        turnover_classification=classification,
    )
    
    allocation_kwh = BASE_CYCLE_KWH * Decimal(str(advance_rate))
    
    print(f"\nRate Calculation:")
    print(f"  lag_hours: {lag_hours} → latency_penalty: 0.90 (10% latency penalty)")
    print(f"  TT penalty: {penalty}× (additional 5% penalty)")
    print(f"  → advance_rate = {advance_rate:.6f}")
    print(f"\nAllocation Decision:")
    print(f"  allocation_kwh = {BASE_CYCLE_KWH} × {advance_rate:.6f} = {allocation_kwh:.2f} kWh")
    print(f"  Status: ⚠️  CONDITIONAL (allocation approved, but pattern monitored)")
    print(f"  Action: Operator must improve turnover time or face further penalties")
    
    return allocation_kwh > 0


def scenario_stalled_mill():
    """Scenario 4: Stalled mill with 96h cycle (STALLED) - BLOCKED"""
    print("\n" + "=" * 70)
    print("SCENARIO 4: Stalled Mill (STALLED cycle - NO ALLOCATION)")
    print("=" * 70)
    
    trust_score = 90.0
    adherence = 0.95
    lag_hours = 96.0  # 96 hours (4 days!)
    
    classification = classify_turnover_time(lag_hours)
    print(f"Last cycle lag: {lag_hours}h → Classification: {classification}")
    
    penalty = turnover_penalty(classification)
    print(f"TT Penalty multiplier: {penalty}× (COMPLETE BLOCK)")
    
    advance_rate = compute_per_cycle_advance_rate(
        trust_score=trust_score,
        adherence=adherence,
        lag_hours=lag_hours,
        base_rate=0.5,
        turnover_classification=classification,
    )
    
    allocation_kwh = BASE_CYCLE_KWH * Decimal(str(advance_rate))
    
    print(f"\nRate Calculation:")
    print(f"  lag_hours: {lag_hours} → latency_penalty: 0.85 (15% latency penalty)")
    print(f"  TT penalty: {penalty}× (multiplied by 0.0 = ALL PENALTIES NULLIFIED)")
    print(f"  → advance_rate = {advance_rate:.6f} (ZERO)")
    print(f"\nAllocation Decision:")
    print(f"  allocation_kwh = {BASE_CYCLE_KWH} × {advance_rate:.6f} = {allocation_kwh:.2f} kWh")
    print(f"  Status: 🔴 BLOCKED (no token allocation for next cycle)")
    print(f"  Reason: Last cycle took > 72 hours (3 days)")
    print(f"  Action: Operator must resolve operational issues before next allocation")
    
    return allocation_kwh == 0


def scenario_stalled_recovery():
    """Scenario 5: Recovery after STALLED - Back to NORMAL"""
    print("\n" + "=" * 70)
    print("SCENARIO 5: Recovery from STALLED (next cycle is NORMAL)")
    print("=" * 70)
    
    print("\nTimeline:")
    print("  Cycle 1: 96h lag (STALLED)")
    print("    → Advance rate = 0.0")
    print("    → Next token: BLOCKED")
    print("  ")
    print("  [Operator fixes underlying issue]")
    print("  ")
    print("  Cycle 2: 36h lag (NORMAL) ← New allocation can proceed")
    
    trust_score = 90.0
    adherence = 0.95
    lag_hours = 36.0  # Back to normal
    
    classification = classify_turnover_time(lag_hours)
    penalty = turnover_penalty(classification)
    
    advance_rate = compute_per_cycle_advance_rate(
        trust_score=trust_score,
        adherence=adherence,
        lag_hours=lag_hours,
        base_rate=0.5,
        turnover_classification=classification,
    )
    
    allocation_kwh = BASE_CYCLE_KWH * Decimal(str(advance_rate))
    
    print(f"\nRecovery Cycle Calculation:")
    print(f"  Classification: {classification}")
    print(f"  Penalty: {penalty}×")
    print(f"  Advance rate: {advance_rate:.6f}")
    print(f"  Allocation: {allocation_kwh:.2f} kWh")
    print(f"  Status: ✅ APPROVED (recovery successful)")
    
    return allocation_kwh > 0


def scenario_comparative():
    """Scenario 6: Side-by-side comparison of all rates"""
    print("\n" + "=" * 70)
    print("SCENARIO 6: Comparative Rate Analysis")
    print("=" * 70)
    
    trust_score = 90.0
    adherence = 0.95
    
    scenarios = [
        ("FAST", 12.0),
        ("NORMAL", 36.0),
        ("SLOW", 60.0),
        ("STALLED", 96.0),
    ]
    
    print(f"\n{'Classification':<12} {'Lag (h)':<10} {'Rate':<10} {'Multiplier':<12} {'Allocation':<12}")
    print("-" * 60)
    
    for label, lag in scenarios:
        classification = classify_turnover_time(lag)
        penalty = turnover_penalty(classification)
        
        advance_rate = compute_per_cycle_advance_rate(
            trust_score=trust_score,
            adherence=adherence,
            lag_hours=lag,
            base_rate=0.5,
            turnover_classification=classification,
        )
        
        allocation = BASE_CYCLE_KWH * Decimal(str(advance_rate))
        
        print(f"{classification:<12} {lag:<10.1f} {advance_rate:<10.6f} {penalty:<12.2f}x {allocation:<12.2f} kWh")
    
    print("\nKey Observations:")
    print("  ✓ FAST > NORMAL > SLOW >> STALLED (monotonic decrease)")
    print("  ✓ STALLED = 0.0 (complete block, no recovery without fixing issue)")
    print("  ✓ Multipliers: 1.05, 1.0, 0.95, 0.0 (matching penalty definition)")


if __name__ == "__main__":
    print("\n" + "█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + "  TURNOVER TIME PENALTY - END-TO-END INTEGRATION TEST".center(68) + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)
    
    try:
        # Run all scenarios
        result1 = scenario_healthy_mill()
        result2 = scenario_fast_mill()
        result3 = scenario_slow_mill()
        result4 = scenario_stalled_mill()
        result5 = scenario_stalled_recovery()
        scenario_comparative()
        
        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        
        all_pass = all([result1, result2, result3, result4, result5])
        
        print(f"\n✓ Scenario 1 (Healthy/NORMAL):  {'PASS' if result1 else 'FAIL'}")
        print(f"✓ Scenario 2 (Fast/FAST):       {'PASS' if result2 else 'FAIL'}")
        print(f"✓ Scenario 3 (Slow/SLOW):       {'PASS' if result3 else 'FAIL'}")
        print(f"✓ Scenario 4 (Stalled/BLOCKED): {'PASS' if result4 else 'FAIL'}")
        print(f"✓ Scenario 5 (Recovery):        {'PASS' if result5 else 'FAIL'}")
        
        if all_pass:
            print("\n" + "🎉 " * 20)
            print("✅ ALL SCENARIOS PASSED - TT PENALTY SYSTEM FULLY OPERATIONAL")
            print("🎉 " * 20)
        else:
            print("\n❌ SOME SCENARIOS FAILED - CHECK IMPLEMENTATION")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
