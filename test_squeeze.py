"""
Quick unit tests for Gradual Squeeze and Entropy Monitor.

Tests verify:
1. compute_advance_rate() formula correctness
2. Squared efficiency penalty (not linear)
3. EntropyMonitor leakage detection
4. Penalty multiplier assignment
5. Recovery from leakage (positive variance clears)
"""

from backend.policy_execution_engine import compute_advance_rate
from backend.revenue_engine import EntropyMonitor

print("=" * 70)
print("GRADUAL SQUEEZE: Advance Rate Computation Tests")
print("=" * 70)

# Test 1: Perfect efficiency, high trust
result = compute_advance_rate(trust_score=90, digital_efficiency=1.0)
expected = 0.5 * 0.9 * 1.0  # 0.45
print(f"\nTest 1: Perfect efficiency (100%)")
print(f"  Input: trust_score=90, digital_efficiency=1.0, base_rate=0.5")
print(f"  Expected: {expected:.4f}")
print(f"  Got:      {result:.4f}")
assert abs(result - expected) < 0.0001, f"Expected {expected}, got {result}"
print(f"  ✓ PASS")

# Test 2: Good efficiency (80%)
result = compute_advance_rate(trust_score=90, digital_efficiency=0.8)
expected = 0.5 * 0.9 * 0.64  # 0.288 (note: 0.8² = 0.64, not 0.8)
print(f"\nTest 2: Good efficiency (80%)")
print(f"  Input: trust_score=90, digital_efficiency=0.8")
print(f"  Formula: 0.5 × 0.9 × (0.8²) = 0.5 × 0.9 × 0.64 = 0.288")
print(f"  Expected: {expected:.4f}")
print(f"  Got:      {result:.4f}")
assert abs(result - expected) < 0.0001, f"Expected {expected}, got {result}"
print(f"  ✓ PASS (Squared penalty working - not linear!)")

# Test 3: Fair efficiency (50%)
result = compute_advance_rate(trust_score=90, digital_efficiency=0.5)
expected = 0.5 * 0.9 * 0.25  # 0.1125
print(f"\nTest 3: Fair efficiency (50%)")
print(f"  Input: trust_score=90, digital_efficiency=0.5")
print(f"  Formula: 0.5 × 0.9 × (0.5²) = 0.5 × 0.9 × 0.25 = 0.1125")
print(f"  Expected: {expected:.4f}")
print(f"  Got:      {result:.4f}")
assert abs(result - expected) < 0.0001, f"Expected {expected}, got {result}"
print(f"  ✓ PASS")

# Test 4: Poor efficiency (40%) - HARD FLOOR ACTIVE
result = compute_advance_rate(trust_score=90, digital_efficiency=0.4)
expected = 0.0  # HARD FLOOR: < 50% efficiency = zero advance (circuit breaker)
print(f"\nTest 4: Poor efficiency (40%) - HARD FLOOR TRIGGERED")
print(f"  Input: trust_score=90, digital_efficiency=0.4")
print(f"  HARD FLOOR: efficiency < 0.5 → 0.0 (circuit breaker, no debate)")
print(f"  Expected: {expected:.4f}")
print(f"  Got:      {result:.4f}")
assert abs(result - expected) < 0.0001, f"Expected {expected}, got {result}"
print(f"  ✓ PASS (Hard floor enforced)")

# Test 5: Boundary test - just below hard floor (49%)
result = compute_advance_rate(trust_score=99, digital_efficiency=0.49)
expected = 0.0
print(f"\nTest 5: Just below hard floor (49%) - Trust doesn't override")
print(f"  Input: trust_score=99, digital_efficiency=0.49")
print(f"  HARD FLOOR: efficiency < 0.5 → 0.0 (trust irrelevant)")
print(f"  Expected: {expected:.4f}")
print(f"  Got:      {result:.4f}")
assert abs(result - expected) < 0.0001, f"Expected {expected}, got {result}"
print(f"  ✓ PASS (Hard floor overrides trust)")

# Test 6: At the hard floor boundary (exactly 50%)
result = compute_advance_rate(trust_score=90, digital_efficiency=0.5)
expected = 0.5 * 0.9 * 0.25  # 0.1125 - still calculates above threshold
print(f"\nTest 6: At hard floor (50% efficiency - still advances)")
print(f"  Input: trust_score=90, digital_efficiency=0.5")
print(f"  Formula: 0.5 × 0.9 × (0.5²) = 0.1125 (at/above threshold)")
print(f"  Expected: {expected:.4f}")
print(f"  Got:      {result:.4f}")
assert abs(result - expected) < 0.0001, f"Expected {expected}, got {result}"
print(f"  ✓ PASS (Hard floor is < 0.5, not ≤ 0.5)")

# Test 7: Just above hard floor (51%)
result = compute_advance_rate(trust_score=90, digital_efficiency=0.51)
expected = 0.5 * 0.9 * (0.51 ** 2)  # 0.117045
print(f"\nTest 7: Just above hard floor (51%)")
print(f"  Input: trust_score=90, digital_efficiency=0.51")
print(f"  Formula: 0.5 × 0.9 × (0.51²) = {expected:.6f}")
print(f"  Expected: {expected:.6f}")
print(f"  Got:      {result:.6f}")
assert abs(result - expected) < 0.0001, f"Expected {expected}, got {result}"
print(f"  ✓ PASS")

print("\n" + "=" * 70)
print("ENTROPY MONITOR: Structural Leakage Detection Tests")
print("=" * 70)

# Test 5: Build 3-day window of negative variance
print(f"\nTest 5: Structural Leakage Detection (All Negative)")
mon = EntropyMonitor("mill_001", window_days=3)

print(f"  Day 1: Record variance = -10 (under-reporting)")
mon.record_variance("2025-01-01", -10)
print(f"  Day 2: Record variance = -5 (under-reporting)")
mon.record_variance("2025-01-02", -5)
print(f"  Day 3: Record variance = -2 (under-reporting)")
mon.record_variance("2025-01-03", -2)

print(f"\n  Window analysis:")
print(f"    All signs: {[r.variance_sign for r in mon.variance_records]}")
print(f"    All negative? {all(r.variance_sign == -1 for r in mon.variance_records)}")

is_leakage = mon.is_structural_leakage()
penalty = mon.penalty_multiplier()
print(f"    is_structural_leakage(): {is_leakage}")
print(f"    penalty_multiplier():    {penalty}")

assert is_leakage is True, f"Expected leakage=True, got {is_leakage}"
assert penalty == 0.9, f"Expected penalty=0.9, got {penalty}"
print(f"  ✓ PASS")

# Test 6: Positive variance starts recovery (not instant reset)
print(f"\nTest 6: Recovery from Leakage (Sticky Decay, Not Instant Reset)")
mon.record_variance("2025-01-04", +1)

print(f"  Window analysis (post-positive):")
print(f"    All signs: {[r.variance_sign for r in mon.variance_records]}")
print(f"    All negative? {all(r.variance_sign == -1 for r in mon.variance_records)}")

is_leakage = mon.is_structural_leakage()
penalty = mon.penalty_multiplier()
print(f"    is_structural_leakage(): {is_leakage}")
print(f"    penalty_multiplier():    {penalty:.4f}")

assert is_leakage is False, f"Expected leakage=False after positive variance, got {is_leakage}"
assert 0.94 < penalty < 0.96, f"Expected penalty≈0.95 (sticky decay!), got {penalty}"
print(f"  ✓ PASS (Sticky Decay: NOT 1.0, but ~0.95 - prevents pulse exploit!)")

print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED")
print("=" * 70)

print("\nSummary:")
print("  ✓ compute_advance_rate() uses squared efficiency penalty (non-linear)")
print("  ✓ EntropyMonitor detects all-negative variance patterns")
print("  ✓ Positive variance starts recovery (not instant reset!)")
print("  ✓ Penalty multiplier uses sticky decay (0.9 → gradual recovery to 1.0)")
print("  ✓ Pulse exploit prevention: One positive day = 5% recovery, not 100%")
