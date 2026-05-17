#!/usr/bin/env python3
"""
Test suite for GridLedger Qualification Engine v1.0
Tests deterministic evaluation and replay verification
"""

import sys
from datetime import datetime
from qualification_engine import QualificationEngine, evaluate_qualification

def test_baseline_eligibility():
    """Test Baseline pathway evaluation"""
    print("Testing Baseline pathway...")

    engine = QualificationEngine()

    # Test NABIWI baseline eligibility
    result = engine.evaluate_qualification('NABIWI', datetime(2026, 5, 8))

    baseline = result.baseline_evidence
    assert baseline.eligible == True, f"Expected Baseline eligible, got {baseline.eligible}"
    assert baseline.metrics['total_cycles'] > 700, f"Expected >700 cycles, got {baseline.metrics['total_cycles']}"
    assert baseline.metrics['completion_rate_pct'] == 100.0, f"Expected 100% completion, got {baseline.metrics['completion_rate_pct']}"

    print("✓ Baseline pathway test passed")

def test_glass_box_eligibility():
    """Test Glass Box pathway evaluation"""
    print("Testing Glass Box pathway...")

    engine = QualificationEngine()

    # Test NABIWI glass box eligibility
    result = engine.evaluate_qualification('NABIWI', datetime(2026, 5, 8))

    glass_box = result.glass_box_evidence
    assert glass_box.eligible == True, f"Expected Glass Box eligible, got {glass_box.eligible}"
    assert glass_box.metrics['max_consecutive_clean_cycles'] >= 62, f"Expected ≥62 consecutive cycles, got {glass_box.metrics['max_consecutive_clean_cycles']}"
    assert glass_box.metrics['avg_adherence_pct'] >= 90.0, f"Expected ≥90% adherence, got {glass_box.metrics['avg_adherence_pct']}"

    print("✓ Glass Box pathway test passed")

def test_forensic_ineligibility():
    """Test Forensic pathway ineligibility (expected to fail)"""
    print("Testing Forensic pathway ineligibility...")

    engine = QualificationEngine()

    # Test NABIWI forensic ineligibility
    result = engine.evaluate_qualification('NABIWI', datetime(2026, 5, 8))

    forensic = result.forensic_evidence
    assert forensic.eligible == False, f"Expected Forensic ineligible, got {forensic.eligible}"
    assert 'variance_coefficient <= 15%' in [f.split(':')[0] for f in forensic.disqualifying_factors], "Expected variance coefficient failure"

    print("✓ Forensic pathway ineligibility test passed")

def test_replay_consistency():
    """Test that multiple evaluations produce identical results"""
    print("Testing replay consistency...")

    engine = QualificationEngine()

    # Run evaluation twice
    result1 = engine.evaluate_qualification('NABIWI', datetime(2026, 5, 8))
    result2 = engine.evaluate_qualification('NABIWI', datetime(2026, 5, 8))

    # Results should be identical
    assert result1.baseline_eligible == result2.baseline_eligible
    assert result1.glass_box_eligible == result2.glass_box_eligible
    assert result1.forensic_eligible == result2.forensic_eligible
    assert result1.data_snapshot_hash == result2.data_snapshot_hash

    print("✓ Replay consistency test passed")

def test_invalid_node():
    """Test evaluation of non-existent node"""
    print("Testing invalid node handling...")

    engine = QualificationEngine()

    try:
        result = engine.evaluate_qualification('NONEXISTENT', datetime(2026, 5, 8))
        # Should still return a result, but with baseline ineligible
        assert result.baseline_eligible == False
        assert "No cycle records found" in result.baseline_evidence.reason
        print("✓ Invalid node test passed")
    except Exception as e:
        print(f"✗ Invalid node test failed: {e}")
        return False

    return True

def test_as_of_date_filtering():
    """Test that as_of_date parameter correctly filters data"""
    print("Testing as_of_date filtering...")

    engine = QualificationEngine()

    # Evaluate with early date (should have fewer cycles)
    early_result = engine.evaluate_qualification('NABIWI', datetime(2024, 1, 1))
    late_result = engine.evaluate_qualification('NABIWI', datetime(2026, 5, 8))

    # Later date should include more cycles
    assert late_result.baseline_evidence.metrics['total_cycles'] >= early_result.baseline_evidence.metrics['total_cycles']

    print("✓ As-of-date filtering test passed")

def run_all_tests():
    """Run all qualification engine tests"""
    print("=" * 60)
    print("QUALIFICATION ENGINE v1.0 - TEST SUITE")
    print("=" * 60)

    tests = [
        test_baseline_eligibility,
        test_glass_box_eligibility,
        test_forensic_ineligibility,
        test_replay_consistency,
        test_invalid_node,
        test_as_of_date_filtering
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            result = test()
            if result is False:
                failed += 1
            else:
                passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("🎉 ALL TESTS PASSED - Qualification Engine is ready for production!")
        return True
    else:
        print("❌ Some tests failed - review implementation")
        return False

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)