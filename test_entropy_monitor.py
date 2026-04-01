"""
Test: Entropy Monitor – Structural Leakage Detection
"""

from backend.revenue_engine import EntropyMonitor, VarianceRecord
from datetime import datetime, timedelta
import json


def test_entropy_monitor_basics():
    """Test basic entropy monitor functionality."""
    print("\n" + "="*70)
    print("TEST 1: EntropyMonitor Basics")
    print("="*70)
    
    monitor = EntropyMonitor(mill_id="TEST_MILL_001", window_days=7)
    
    print(f"\nInitial state:")
    print(f"  Mill ID: {monitor.mill_id}")
    print(f"  Window Days: {monitor.window_days}")
    print(f"  Records in window: {len(monitor.variance_records)}")
    print(f"  Structural leakage: {monitor.is_structural_leakage()}")
    print(f"  Penalty multiplier: {monitor.get_penalty_multiplier():.2f}")
    
    assert not monitor.is_structural_leakage(), "Empty monitor should not detect leakage"
    assert monitor.get_penalty_multiplier() == 1.0, "No penalty with no leakage"


def test_entropy_monitor_positive_variance():
    """Test with positive variance (over-reporting)."""
    print("\n" + "="*70)
    print("TEST 2: Positive Variance (Over-reporting)")
    print("="*70)
    
    monitor = EntropyMonitor(mill_id="TEST_MILL_001", window_days=7)
    
    # Record 7 days of positive variance (over-reporting)
    for i in range(7):
        date = f"2026-03-{20+i:02d}"
        variance = 1000.0 + (i * 100)  # Positive (over-reporting)
        monitor.record_variance(date, variance)
    
    status = monitor.get_leakage_status()
    
    print(f"\nAfter 7 days of positive variance:")
    print(f"  Records in window: {status['records_in_window']}")
    print(f"  Negative count: {status['negative_count']}")
    print(f"  Leakage percentage: {status['leakage_percentage']:.1f}%")
    print(f"  Structural leakage: {status['structural_leakage']}")
    print(f"  Penalty multiplier: {status['penalty_multiplier']:.2f}")
    
    assert not monitor.is_structural_leakage(), "Positive variance should not trigger leakage"
    assert monitor.get_penalty_multiplier() == 1.0, "No penalty for positive variance"
    print("  ✓ Positive variance correctly NOT flagged as leakage")


def test_entropy_monitor_negative_variance():
    """Test with negative variance (under-reporting)."""
    print("\n" + "="*70)
    print("TEST 3: Negative Variance (Under-reporting)")
    print("="*70)
    
    monitor = EntropyMonitor(mill_id="TEST_MILL_001", window_days=7)
    
    # Record 7 days of negative variance (under-reporting)
    for i in range(7):
        date = f"2026-03-{20+i:02d}"
        variance = -1000.0 - (i * 100)  # Negative (under-reporting)
        monitor.record_variance(date, variance)
    
    status = monitor.get_leakage_status()
    
    print(f"\nAfter 7 days of negative variance:")
    print(f"  Records in window: {status['records_in_window']}")
    print(f"  Negative count: {status['negative_count']}")
    print(f"  Leakage percentage: {status['leakage_percentage']:.1f}%")
    print(f"  Structural leakage: {status['structural_leakage']}")
    print(f"  Penalty multiplier: {status['penalty_multiplier']:.2f}")
    
    assert monitor.is_structural_leakage(), "All negative variance should trigger leakage"
    assert monitor.get_penalty_multiplier() == 0.9, "Penalty should be 0.9 for leakage"
    print("  ✓ Negative variance correctly flagged as structural leakage")
    print("  ✓ Penalty multiplier: 0.9 (10% reduction)")


def test_entropy_monitor_mixed_variance():
    """Test with mixed positive and negative variance (no structural leakage)."""
    print("\n" + "="*70)
    print("TEST 4: Mixed Variance (No Structural Leakage)")
    print("="*70)
    
    monitor = EntropyMonitor(mill_id="TEST_MILL_001", window_days=7)
    
    # Record 7 days with mixed variance
    variance_values = [1000, -500, 800, -300, 600, -200, 400]  # Mixed signs
    
    for i, var in enumerate(variance_values):
        date = f"2026-03-{20+i:02d}"
        monitor.record_variance(date, var)
    
    status = monitor.get_leakage_status()
    
    print(f"\nAfter 7 days of mixed variance:")
    print(f"  Records in window: {status['records_in_window']}")
    print(f"  Negative count: {status['negative_count']}")
    print(f"  Leakage percentage: {status['leakage_percentage']:.1f}%")
    print(f"  Structural leakage: {status['structural_leakage']}")
    print(f"  Penalty multiplier: {status['penalty_multiplier']:.2f}")
    
    assert not monitor.is_structural_leakage(), "Mixed variance should not trigger leakage"
    assert monitor.get_penalty_multiplier() == 1.0, "No penalty for mixed variance"
    print("  ✓ Mixed variance correctly NOT flagged as leakage")


def test_entropy_monitor_window_size():
    """Test rolling window behavior."""
    print("\n" + "="*70)
    print("TEST 5: Rolling Window Behavior")
    print("="*70)
    
    monitor = EntropyMonitor(mill_id="TEST_MILL_001", window_days=3)
    
    print(f"\nAdding 5 records to 3-day window:")
    
    for i in range(5):
        date = f"2026-03-{20+i:02d}"
        variance = -1000.0  # All negative
        monitor.record_variance(date, variance)
        
        print(f"  Day {i+1}: Added variance={variance:.0f}")
        print(f"    → Records in window: {len(monitor.variance_records)}")
        print(f"    → Leakage detected: {monitor.is_structural_leakage()}")
    
    final_status = monitor.get_leakage_status()
    print(f"\nFinal window state:")
    print(f"  Records: {final_status['records_in_window']} (max window: {monitor.window_days})")
    print(f"  Leakage: {final_status['structural_leakage']}")
    
    assert len(monitor.variance_records) == 3, "Window should maintain max size"
    assert monitor.is_structural_leakage(), "Full window of negative should trigger leakage"
    print("  ✓ Rolling window correctly maintained")


def test_entropy_monitor_penalty_chain():
    """Test how penalty stacks with other mechanisms."""
    print("\n" + "="*70)
    print("TEST 6: Penalty Application Chain")
    print("="*70)
    
    monitor = EntropyMonitor(mill_id="TEST_MILL_001", window_days=7)
    
    # Create structural leakage scenario
    for i in range(7):
        date = f"2026-03-{20+i:02d}"
        variance = -500.0  # All negative
        monitor.record_variance(date, variance)
    
    print(f"\nPenalty application chain:")
    print(f"  Base advance rate (from policy): 50.0%")
    print(f"  After Gradual Squeeze: 40.0% (example computation)")
    print(f"  Structural penalty multiplier: {monitor.get_penalty_multiplier():.2f}")
    print(f"  Final rate: 40.0% × {monitor.get_penalty_multiplier():.2f} = {40.0 * monitor.get_penalty_multiplier():.1f}%")
    
    assert monitor.get_penalty_multiplier() == 0.9
    print("  ✓ Penalty correctly applies in sequence")


def test_entropy_monitor_status_output():
    """Test detailed status output."""
    print("\n" + "="*70)
    print("TEST 7: Detailed Status Output")
    print("="*70)
    
    monitor = EntropyMonitor(mill_id="NABIWI_MKWINDA", window_days=5)
    
    # Create a realistic scenario
    variance_values = [
        (-200, "2026-03-26"),  # Under
        (-150, "2026-03-27"),  # Under
        (-300, "2026-03-28"),  # Under
        (-100, "2026-03-29"),  # Under
        (-250, "2026-03-30"),  # Under (today)
    ]
    
    for variance, date in variance_values:
        monitor.record_variance(date, variance)
    
    status = monitor.get_leakage_status()
    
    print(f"\nRecent 5-day history for {status['mill_id']}:")
    print(f"  Structural Leakage: {status['structural_leakage']}")
    print(f"  Negative Days: {status['negative_count']}/{status['window_days']}")
    print(f"  Leakage Percentage: {status['leakage_percentage']:.0f}%")
    print(f"  Penalty Multiplier: {status['penalty_multiplier']:.0%}")
    print(f"\n  Variance History:")
    for record in status['variance_history']:
        print(f"    {record['date']}: {record['variance']:+.0f} ({record['sign']})")
    
    assert status['structural_leakage']
    assert status['negative_count'] == 5
    print("\n  ✓ Status output complete and accurate")


if __name__ == "__main__":
    test_entropy_monitor_basics()
    test_entropy_monitor_positive_variance()
    test_entropy_monitor_negative_variance()
    test_entropy_monitor_mixed_variance()
    test_entropy_monitor_window_size()
    test_entropy_monitor_penalty_chain()
    test_entropy_monitor_status_output()
    
    print("\n" + "="*70)
    print("✅ ALL ENTROPY MONITOR TESTS PASSED")
    print("="*70 + "\n")
