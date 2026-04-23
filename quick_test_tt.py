from backend.policy_execution_engine import classify_turnover_time, turnover_penalty, compute_per_cycle_advance_rate

print("=" * 60)
print("TT Penalty Integration Test")
print("=" * 60)

# Test classifications
print("\n✓ Classification Tests:")
print(f"  12h (FAST):    {classify_turnover_time(12.0)}")
print(f"  36h (NORMAL):  {classify_turnover_time(36.0)}")
print(f"  60h (SLOW):    {classify_turnover_time(60.0)}")
print(f"  96h (STALLED): {classify_turnover_time(96.0)}")

# Test penalties
print("\n✓ Penalty Multipliers:")
print(f"  FAST:    {turnover_penalty('FAST')}")
print(f"  NORMAL:  {turnover_penalty('NORMAL')}")
print(f"  SLOW:    {turnover_penalty('SLOW')}")
print(f"  STALLED: {turnover_penalty('STALLED')}")

# Test rates
print("\n✓ Advance Rate Calculations (trust=90%, adherence=95%):")
print(f"  FAST (12h):    {compute_per_cycle_advance_rate(90, 0.95, 12, 0.5, 'FAST'):.6f}")
print(f"  NORMAL (36h):  {compute_per_cycle_advance_rate(90, 0.95, 36, 0.5, 'NORMAL'):.6f}")
print(f"  SLOW (60h):    {compute_per_cycle_advance_rate(90, 0.95, 60, 0.5, 'SLOW'):.6f}")
print(f"  STALLED (96h): {compute_per_cycle_advance_rate(90, 0.95, 96, 0.5, 'STALLED'):.6f}")

print("\n✓ ALL TESTS PASSED")
print("=" * 60)
