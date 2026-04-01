#!/usr/bin/env python3
"""
Test: Suspicion Score System - Accumulate Pressure Without Proof

Validates the SuspicionTracker mechanism that accumulates pressure via:
- Variance deviation above tolerance
- Pattern anomalies (entropy, Z-score, etc.)
- Daily decay (forgiveness over time)
- Graduated penalty multiplier
"""

from backend.capital_controls import SuspicionTracker

def test_initialization():
    """Test: SuspicionTracker initializes with correct defaults."""
    print("\n" + "="*70)
    print("TEST: SuspicionTracker Initialization")
    print("="*70)
    
    tracker = SuspicionTracker(decay_rate=0.1, threshold=5.0)
    
    print(f"\nInitial state:")
    print(f"  Score: {tracker.score}")
    print(f"  Decay rate: {tracker.decay_rate}")
    print(f"  Threshold: {tracker.threshold}")
    print(f"  Penalty multiplier: {tracker.penalty_multiplier()}")
    
    assert tracker.score == 0.0
    assert tracker.decay_rate == 0.1
    assert tracker.threshold == 5.0
    assert tracker.penalty_multiplier() == 1.0
    
    print(f"\n[PASS] Initialization correct")


def test_variance_risk():
    """Test: Variance deviation above tolerance adds to suspicion."""
    print("\n" + "="*70)
    print("TEST: Variance Risk Calculation")
    print("="*70)
    
    tracker = SuspicionTracker(decay_rate=0.1, threshold=5.0)
    
    print(f"\nTolerance level: ±1.5%")
    print(f"Formula: daily_risk = max(0, variance - 1.5) / 10.0\n")
    
    # Test 1: Clean variance (within tolerance)
    score1 = tracker.update(deviation_pct=1.0, pattern_anomaly=False)
    print(f"Test 1: 1.0% variance (within tolerance)")
    print(f"  Expected: 0.0 addition (below tolerance)")
    print(f"  Got score: {score1:.4f}")
    assert score1 >= 0.0 and score1 < 0.01  # Near zero
    print(f"  [PASS]\n")
    
    # Test 2: Slightly above tolerance
    tracker.score = 0.0  # Reset
    score2 = tracker.update(deviation_pct=2.0, pattern_anomaly=False)
    expected2 = (2.0 - 1.5) / 10.0  # 0.05
    print(f"Test 2: 2.0% variance (slightly above tolerance)")
    print(f"  Expected: (2.0-1.5)/10.0 = {expected2:.4f}")
    print(f"  Got score: {score2:.4f}")
    assert abs(score2 - expected2) < 0.001
    print(f"  [PASS]\n")
    
    # Test 3: Significantly above tolerance
    tracker.score = 0.0  # Reset
    score3 = tracker.update(deviation_pct=4.5, pattern_anomaly=False)
    expected3 = (4.5 - 1.5) / 10.0  # 0.3
    print(f"Test 3: 4.5% variance (significantly above)")
    print(f"  Expected: (4.5-1.5)/10.0 = {expected3:.4f}")
    print(f"  Got score: {score3:.4f}")
    assert abs(score3 - expected3) < 0.001
    print(f"  [PASS]\n")


def test_pattern_anomaly():
    """Test: Pattern anomalies add fixed risk."""
    print("\n" + "="*70)
    print("TEST: Pattern Anomaly Risk")
    print("="*70)
    
    print(f"\nPattern anomaly contribution: +0.5 points\n")
    
    # Test 1: Variance only (no anomaly)
    tracker = SuspicionTracker()
    score1 = tracker.update(deviation_pct=2.0, pattern_anomaly=False)
    expected1 = (2.0 - 1.5) / 10.0  # 0.05
    print(f"Test 1: 2.0% variance, no anomaly")
    print(f"  Expected: 0.05")
    print(f"  Got: {score1:.4f}")
    assert abs(score1 - expected1) < 0.001
    print(f"  [PASS]\n")
    
    # Test 2: Variance + anomaly
    tracker.score = 0.0  # Reset
    score2 = tracker.update(deviation_pct=2.0, pattern_anomaly=True)
    expected2 = 0.05 + 0.5  # 0.55
    print(f"Test 2: 2.0% variance + pattern anomaly")
    print(f"  Expected: 0.05 + 0.5 = 0.55")
    print(f"  Got: {score2:.4f}")
    assert abs(score2 - expected2) < 0.001
    print(f"  [PASS]\n")
    
    # Test 3: No variance, just anomaly
    tracker.score = 0.0  # Reset
    score3 = tracker.update(deviation_pct=0.5, pattern_anomaly=True)
    expected3 = 0.0 + 0.5  # 0.5 (no variance risk)
    print(f"Test 3: 0.5% variance + pattern anomaly")
    print(f"  Expected: 0.0 + 0.5 = 0.5")
    print(f"  Got: {score3:.4f}")
    assert abs(score3 - expected3) < 0.001
    print(f"  [PASS]\n")


def test_daily_decay():
    """Test: Score decays daily."""
    print("\n" + "="*70)
    print("TEST: Daily Decay Mechanism")
    print("="*70)
    
    tracker = SuspicionTracker(decay_rate=0.1, threshold=5.0)
    
    print(f"\nDecay rate: 10% per day")
    print(f"Formula: score = score * (1 - decay_rate)\n")
    
    # Build up suspicion
    tracker.score = 5.0
    print(f"Starting score: {tracker.score:.4f}")
    
    for day in range(1, 6):
        decayed = tracker.decay_daily()
        expected = 5.0 * ((0.9) ** day)
        print(f"Day {day}: {decayed:.4f} (expected ~{expected:.4f})")
        assert abs(decayed - expected) < 0.001
    
    print(f"\nAfter 5 days: score ~{tracker.score:.4f}")
    print(f"After 10 days: would be ~{5.0 * (0.9**10):.4f}")
    print(f"  [PASS]\n")


def test_accumulation_and_decay():
    """Test: Suspicion accumulates then decays over time."""
    print("\n" + "="*70)
    print("TEST: Realistic Accumulation & Decay Scenario")
    print("="*70)
    
    tracker = SuspicionTracker(decay_rate=0.1, threshold=5.0)
    
    print(f"\nScenario: 18 suspicious days, then 21 clean days\n")
    
    # Days 1-18: Suspicious activity
    print("DAYS 1-18: Suspicious Activity")
    for day in range(1, 19):
        score = tracker.update(deviation_pct=2.5, pattern_anomaly=True)
        if day in [1, 6, 12, 18]:
            print(f"  Day {day}: Variance 2.5% + anomaly = Score {score:.2f}")
    
    print(f"\nScore after suspicious period: {tracker.score:.2f}")
    penalty_period1 = tracker.penalty_multiplier()
    print(f"Penalty multiplier: {penalty_period1}")
    assert tracker.score >= tracker.threshold  # Should be above threshold
    assert penalty_period1 == 0.8  # Penalty active
    
    # Days 16-36: Recovery
    print(f"\nDAYS 16-36: Clean Days (decay only)")
    for day in range(16, 37):
        score = tracker.decay_daily()
        if day in [16, 22, 28, 36]:
            print(f"  Day {day}: Score {score:.2f}")
    
    print(f"\nScore after recovery period: {tracker.score:.2f}")
    penalty_recovery = tracker.penalty_multiplier()
    print(f"Penalty multiplier: {penalty_recovery}")
    
    # Estimate when penalty lifts
    print(f"\n[Penalty recovery timeline]")
    if tracker.score >= tracker.threshold:
        print(f"  Still above threshold, penalty still active")
    else:
        print(f"  Below threshold, penalty lifted")
    
    print(f"  [PASS]\n")


def test_penalty_threshold():
    """Test: Penalty applies at threshold."""
    print("\n" + "="*70)
    print("TEST: Penalty Threshold Behavior")
    print("="*70)
    
    tracker = SuspicionTracker(decay_rate=0.0, threshold=5.0)  # No decay for test
    
    print(f"\nThreshold: 5.0")
    print(f"Penalty: 0.8 when score >= 5.0\n")
    
    # Test below threshold
    tracker.score = 4.9
    penalty1 = tracker.penalty_multiplier()
    print(f"Score 4.9: multiplier = {penalty1}")
    assert penalty1 == 1.0
    print(f"  [PASS] No penalty below threshold\n")
    
    # Test at threshold
    tracker.score = 5.0
    penalty2 = tracker.penalty_multiplier()
    print(f"Score 5.0: multiplier = {penalty2}")
    assert penalty2 == 0.8
    print(f"  [PASS] Penalty at threshold\n")
    
    # Test above threshold
    tracker.score = 7.5
    penalty3 = tracker.penalty_multiplier()
    print(f"Score 7.5: multiplier = {penalty3}")
    assert penalty3 == 0.8
    print(f"  [PASS] Penalty above threshold\n")


def test_max_score_cap():
    """Test: Score caps at maximum."""
    print("\n" + "="*70)
    print("TEST: Maximum Score Cap")
    print("="*70)
    
    tracker = SuspicionTracker(decay_rate=0.0)  # No decay
    
    print(f"\nMaximum score cap: {tracker.max_score}\n")
    
    # Try to exceed max
    tracker.score = 0.0
    for _ in range(50):
        tracker.update(deviation_pct=5.0, pattern_anomaly=True)
    
    print(f"After 50 updates with high risk:")
    print(f"  Score: {tracker.score}")
    print(f"  Max allowed: {tracker.max_score}")
    
    assert tracker.score <= tracker.max_score
    assert tracker.score == tracker.max_score
    
    print(f"\n  [PASS] Score capped at maximum\n")


def test_status_output():
    """Test: Status report format."""
    print("\n" + "="*70)
    print("TEST: Status Report Output")
    print("="*70)
    
    tracker = SuspicionTracker(decay_rate=0.1, threshold=5.0)
    tracker.score = 6.5
    
    status = tracker.get_status()
    
    print(f"\nStatus report:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    assert "current_score" in status
    assert "threshold" in status
    assert "penalty_active" in status
    assert "penalty_multiplier" in status
    assert "estimated_recovery_days" in status
    
    print(f"\n  [PASS] Status format correct\n")


def run_all_tests():
    """Run all suspicion score tests."""
    print("\n" + "="*70)
    print("SUSPICION SCORE TEST SUITE")
    print("="*70)
    print("\nValidates continuous suspicion accumulation without proof.")
    print("System remembers suspicious patterns and applies graduated penalties.")
    
    try:
        test_initialization()
        test_variance_risk()
        test_pattern_anomaly()
        test_daily_decay()
        test_accumulation_and_decay()
        test_penalty_threshold()
        test_max_score_cap()
        test_status_output()
        
        print("\n" + "="*70)
        print("ALL SUSPICION SCORE TESTS PASSED")
        print("="*70)
        return True
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
