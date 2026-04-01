#!/usr/bin/env python3
"""Quick verification that starvation zone works"""

from backend.policy_execution_engine import compute_advance_rate

print("\nSTARVATION ZONE VERIFICATION")
print("=" * 70)

# Test 1: Death zone
rate_death = compute_advance_rate(90, 0.45, 0.50)
print(f"1. Death zone (45%): {rate_death:.6f} (expect 0)")
assert rate_death == 0.0, "Death zone failed"

# Test 2: Starvation lower
rate_starv_lower = compute_advance_rate(80, 0.50, 0.50)
print(f"2. Starvation at 50%: {rate_starv_lower:.6f} (expect ~0.025)")
assert 0.024 < rate_starv_lower < 0.026, "Starvation lower boundary failed"

# Test 3: Starvation middle
rate_starv_mid = compute_advance_rate(85, 0.575, 0.50)
print(f"3. Starvation at 57.5%: {rate_starv_mid:.6f} (expect ~0.035)")
assert 0.034 < rate_starv_mid < 0.036, "Starvation middle failed"

# Test 4: Normal zone
rate_normal = compute_advance_rate(90, 0.65, 0.50)
print(f"4. Normal zone at 65%: {rate_normal:.6f} (expect ~0.190)")
assert 0.18 < rate_normal < 0.20, "Normal zone failed"

# Test 5: Verify 4x jump
ratio = rate_normal / compute_advance_rate(90, 0.64, 0.50)
print(f"5. Jump from 64% to 65%: {ratio:.2f}x (expect ~4x)")
assert ratio > 3.5, "Boundary jump failed"

print(f"\n[PASS] All starvation zone tests pass!")
print(f"[PASS] Boundaries precise at 50% and 65%")
print(f"[PASS] Four-layer system fully functional\n")
