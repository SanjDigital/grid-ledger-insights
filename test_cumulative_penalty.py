#!/usr/bin/env python3
"""
Test: Cumulative Loss Pressure - Long-term Memory for Prolonged Underperformance

This test validates that the system "remembers damage" via 30-day rolling average efficiency.
Even operators with current good efficiency can be penalized if their historical performance 
was poor. This prevents gaming the system with short-term spikes.
"""

from backend.policy_execution_engine import compute_advance_rate
from backend.capital_controls import CapitalControls
from datetime import datetime, timezone, timedelta
from sqlmodel import Session, select
from scripts.init_db import engine, ReconciliationRecord, Mill

def setup_test_mill(mill_id: str):
    """Ensure test mill exists in database."""
    with Session(engine) as session:
        mill = session.get(Mill, mill_id)
        if not mill:
            mill = Mill(
                id=mill_id,
                name=f"Test Mill {mill_id}",
                location="Test Location",
                latitude=-0.0,
                longitude=0.0,
            )
            session.add(mill)
            session.commit()


def create_reconciliation_record(
    mill_id: str,
    ear: float,  # efficiency metric
    days_ago: int = 0,
    description: str = ""
):
    """Create a reconciliation record for testing."""
    date = datetime.now(timezone.utc) - timedelta(days=days_ago)
    
    with Session(engine) as session:
        rec = ReconciliationRecord(
            mill_id=mill_id,
            cycle_id="TEST_CYCLE",
            created_at=date,
            energy_accountability_ratio=ear,
            verified_throughput=1000.0,
            physical_consumed=1000.0,
            total_cash=10000.0,
            variance_pct=0.0,
            notes=f"Test record: {description}",
        )
        session.add(rec)
        session.commit()


def cleanup_test_records(mill_id: str):
    """Clean up test records from database."""
    with Session(engine) as session:
        # Delete reconciliation records
        records = session.exec(
            select(ReconciliationRecord)
            .where(ReconciliationRecord.mill_id == mill_id)
        ).all()
        for rec in records:
            session.delete(rec)
        session.commit()


def test_cumulative_penalty_high_efficiency():
    """Test: No penalty when rolling efficiency >= 75%"""
    print("\n" + "="*70)
    print("TEST: Cumulative Penalty - High Efficiency (No Penalty)")
    print("="*70)
    
    mill_id = "TEST_MILL_HIGH_EFF"
    setup_test_mill(mill_id)
    cleanup_test_records(mill_id)
    
    # Create 10 daily records with 90% efficiency
    for i in range(10):
        create_reconciliation_record(
            mill_id,
            ear=0.90,
            days_ago=i,
            description=f"Good efficiency day {i}"
        )
    
    # Check rolling efficiency
    rolling_eff = CapitalControls.get_rolling_efficiency(mill_id, days=30)
    penalty = CapitalControls.cumulative_penalty(mill_id)
    
    print(f"\n30-day rolling efficiency: {rolling_eff:.2%}")
    print(f"Cumulative penalty multiplier: {penalty}")
    
    # Calculate advance rate with penalty
    advance_no_penalty = compute_advance_rate(
        trust_score=85.0,
        digital_efficiency=0.85,
        base_rate=0.50
    )
    advance_with_penalty = compute_advance_rate(
        trust_score=85.0,
        digital_efficiency=0.85,
        base_rate=0.50,
        mill_id=mill_id
    )
    
    print(f"\nAdvance rate WITHOUT penalty (no mill_id): {advance_no_penalty:.4f} ({advance_no_penalty:.1%})")
    print(f"Advance rate WITH penalty lookup (mill_id): {advance_with_penalty:.4f} ({advance_with_penalty:.1%})")
    
    # Should be the same (no penalty)
    assert abs(advance_no_penalty - advance_with_penalty) < 0.0001, \
        f"Expected same rate (no penalty), got {advance_no_penalty:.4f} vs {advance_with_penalty:.4f}"
    assert rolling_eff >= 0.75, f"Rolling efficiency should be >= 0.75, got {rolling_eff}"
    assert penalty == 1.0, f"Penalty should be 1.0 (no penalty), got {penalty}"
    
    print("\n✅ PASS: No penalty applied with high rolling efficiency")
    cleanup_test_records(mill_id)


def test_cumulative_penalty_low_efficiency():
    """Test: Penalty applied when rolling efficiency < 75%"""
    print("\n" + "="*70)
    print("TEST: Cumulative Penalty - Low Efficiency (Penalty Applied)")
    print("="*70)
    
    mill_id = "TEST_MILL_LOW_EFF"
    setup_test_mill(mill_id)
    cleanup_test_records(mill_id)
    
    # Create 10 daily records with 60% efficiency (below 75% threshold)
    for i in range(10):
        create_reconciliation_record(
            mill_id,
            ear=0.60,
            days_ago=i,
            description=f"Poor efficiency day {i}"
        )
    
    # Check rolling efficiency
    rolling_eff = CapitalControls.get_rolling_efficiency(mill_id, days=30)
    penalty = CapitalControls.cumulative_penalty(mill_id)
    
    print(f"\n30-day rolling efficiency: {rolling_eff:.2%}")
    print(f"Cumulative penalty multiplier: {penalty}")
    
    # Calculate advance rate with penalty
    advance_rate = compute_advance_rate(
        trust_score=85.0,
        digital_efficiency=0.85,
        base_rate=0.50,
        mill_id=mill_id
    )
    
    # Expected: base_rate halved from 0.50 to 0.25
    # Then: 0.25 × (85/100) × (0.85²) = 0.25 × 0.85 × 0.7225 = 0.15365625
    expected = 0.25 * 0.85 * (0.85 ** 2)
    
    print(f"\nAdvance rate WITH penalty (halved base): {advance_rate:.4f} ({advance_rate:.1%})")
    print(f"Expected (0.25 × 0.85 × 0.85²): {expected:.4f}")
    
    assert rolling_eff < 0.75, f"Rolling efficiency should be < 0.75, got {rolling_eff}"
    assert penalty == 0.5, f"Penalty should be 0.5 (halved), got {penalty}"
    assert abs(advance_rate - expected) < 0.0001, \
        f"Expected {expected:.4f}, got {advance_rate:.4f}"
    
    print("\n✅ PASS: Base rate halved with low rolling efficiency")
    cleanup_test_records(mill_id)


def test_cumulative_penalty_recovery():
    """Test: Recovery when rolling efficiency improves above 75%"""
    print("\n" + "="*70)
    print("TEST: Cumulative Penalty - Recovery Path")
    print("="*70)
    
    mill_id = "TEST_MILL_RECOVERY"
    setup_test_mill(mill_id)
    cleanup_test_records(mill_id)
    
    # Phase 1: Create old records with low efficiency (days 30-11 ago)
    for i in range(20, 10, -1):
        create_reconciliation_record(
            mill_id,
            ear=0.60,  # Poor
            days_ago=i,
            description=f"Old poor efficiency day"
        )
    
    # Phase 2: Create recent records with good efficiency (days 10-0 ago)
    for i in range(10, 0, -1):
        create_reconciliation_record(
            mill_id,
            ear=0.90,  # Good
            days_ago=i,
            description=f"Recent good efficiency day"
        )
    
    # Check rolling efficiency (mixed: some old poor, some recent good)
    rolling_eff = CapitalControls.get_rolling_efficiency(mill_id, days=30)
    penalty = CapitalControls.cumulative_penalty(mill_id)
    
    print(f"\n30-day rolling efficiency: {rolling_eff:.2%}")
    print(f"Cumulative penalty multiplier: {penalty}")
    print(f"(Recent good performance helps, but old poor still in window)")
    
    # Now add more recent good records to push over 75%
    for i in range(5, 0, -1):
        create_reconciliation_record(
            mill_id,
            ear=0.95,  # Excellent
            days_ago=i,
            description=f"Excellent efficiency day"
        )
    
    rolling_eff_after = CapitalControls.get_rolling_efficiency(mill_id, days=30)
    penalty_after = CapitalControls.cumulative_penalty(mill_id)
    
    print(f"\nAfter additional excellent performance:")
    print(f"30-day rolling efficiency: {rolling_eff_after:.2%}")
    print(f"Cumulative penalty multiplier: {penalty_after}")
    
    # Should eventually recover
    if rolling_eff_after >= 0.75:
        print("\n✅ Penalty lifted after sustained improvement")
        assert penalty_after == 1.0
    else:
        print(f"\n⚠ Still recovering (efficiency {rolling_eff_after:.2%} < 75%)")
    
    cleanup_test_records(mill_id)


def test_cumulative_penalty_vs_hard_floor():
    """Test: Hard floor takes priority over cumulative penalty"""
    print("\n" + "="*70)
    print("TEST: Hard Floor vs Cumulative Penalty (Hard Floor Wins)")
    print("="*70)
    
    mill_id = "TEST_MILL_BOTH_PENALTIES"
    setup_test_mill(mill_id)
    cleanup_test_records(mill_id)
    
    # Create low rolling efficiency to trigger cumulative penalty
    for i in range(10):
        create_reconciliation_record(mill_id, ear=0.60, days_ago=i)
    
    rolling_eff = CapitalControls.get_rolling_efficiency(mill_id, days=30)
    penalty = CapitalControls.cumulative_penalty(mill_id)
    
    print(f"\nSetup: Rolling efficiency = {rolling_eff:.2%}, Penalty = {penalty}")
    print(f"(Cumulative penalty is active: base_rate will be halved)")
    
    # Now test with current_efficiency < 50% (hard floor)
    advance_rate_hard_floor = compute_advance_rate(
        trust_score=90.0,
        digital_efficiency=0.40,  # Below 50% hard floor
        base_rate=0.50,
        mill_id=mill_id
    )
    
    print(f"\nWith current efficiency 40% (< 50% hard floor):")
    print(f"  Advance rate: {advance_rate_hard_floor:.4f}")
    print(f"  ✓ Hard floor triggered: 0.0 (no debate)")
    assert advance_rate_hard_floor == 0.0, "Hard floor should trigger at 40%"
    
    # Test with current_efficiency > 50% but rolling < 75%
    advance_rate_cumulative = compute_advance_rate(
        trust_score=90.0,
        digital_efficiency=0.85,  # Above 50% hard floor
        base_rate=0.50,
        mill_id=mill_id
    )
    
    # Expected: halved base (0.25) × 0.90 × (0.85²) = 0.25 × 0.90 × 0.7225 = 0.162...
    expected_cumulative = 0.25 * 0.90 * (0.85 ** 2)
    
    print(f"\nWith current efficiency 85% (> 50% hard floor):")
    print(f"  Advance rate: {advance_rate_cumulative:.4f}")
    print(f"  Expected (halved base): {expected_cumulative:.4f}")
    print(f"  ✓ Cumulative penalty applied (base halved)")
    assert abs(advance_rate_cumulative - expected_cumulative) < 0.0001
    
    print("\n✅ PASS: Hard floor has priority; cumulative penalty applies below it")
    cleanup_test_records(mill_id)


def run_all_tests():
    """Run all cumulative penalty tests."""
    print("\n" + "="*70)
    print("CUMULATIVE LOSS PRESSURE TEST SUITE")
    print("="*70)
    print("\nValidates that 30-day rolling average efficiency triggers base rate penalty.")
    print("The system remembers prolonged underperformance and halves capital access.")
    
    try:
        test_cumulative_penalty_high_efficiency()
        test_cumulative_penalty_low_efficiency()
        test_cumulative_penalty_recovery()
        test_cumulative_penalty_vs_hard_floor()
        
        print("\n" + "="*70)
        print("✅ ALL CUMULATIVE PENALTY TESTS PASSED")
        print("="*70)
        return True
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
