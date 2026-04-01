#!/usr/bin/env python3
"""
Validation: Hard Economic Floor Implementation
Verifies that the hard floor (50% efficiency circuit breaker) is working correctly.
"""

from backend.policy_execution_engine import compute_advance_rate

def validate_hard_floor():
    """Validate hard floor implementation."""
    print("=" * 70)
    print("HARD ECONOMIC FLOOR VALIDATION")
    print("=" * 70)
    
    test_cases = [
        # (trust_score, efficiency, expected_rate, description)
        (90.0, 1.0, 0.45, "Perfect efficiency"),
        (90.0, 0.8, 0.288, "Good efficiency (80%)"),
        (90.0, 0.5, 0.1125, "At boundary (50%)"),
        (99.0, 0.49, 0.0, "Just below (49%) + high trust → HARD FLOOR"),
        (90.0, 0.4, 0.0, "Poor efficiency (40%) → HARD FLOOR"),
        (90.0, 0.3, 0.0, "Very poor (30%) → HARD FLOOR"),
        (90.0, 0.0, 0.0, "Zero efficiency → HARD FLOOR"),
    ]
    
    all_passed = True
    for trust, efficiency, expected, desc in test_cases:
        actual = compute_advance_rate(trust, efficiency)
        passed = abs(actual - expected) < 0.0001
        
        status = "✅ PASS" if passed else "❌ FAIL"
        floor_note = " [HARD FLOOR]" if efficiency < 0.5 else ""
        
        print(f"\n{desc}{floor_note}")
        print(f"  Trust: {trust}%, Efficiency: {efficiency:.1%}")
        print(f"  Expected: {expected:.4f}, Got: {actual:.4f} {status}")
        
        if not passed:
            all_passed = False
            print(f"  ERROR: Mismatch!")
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL VALIDATIONS PASSED - Hard floor is working correctly")
    else:
        print("❌ VALIDATION FAILED - Hard floor implementation has issues")
    print("=" * 70)
    
    return all_passed

if __name__ == "__main__":
    import sys
    success = validate_hard_floor()
    sys.exit(0 if success else 1)
