from backend.revenue_engine import EntropyMonitor

mon = EntropyMonitor("test_mill", window_days=3, recovery_rate=0.05)
print("Created monitor")

penalty = mon.record_variance("2025-01-01", -10)
print(f"Day 1: penalty={penalty}")

penalty = mon.record_variance("2025-01-02", -5)
print(f"Day 2: penalty={penalty}")

penalty = mon.record_variance("2025-01-03", -2)
print(f"Day 3: penalty={penalty}")

print(f"Structural leakage: {mon.is_structural_leakage()}")

penalty = mon.record_variance("2025-01-04", +1)
print(f"Day 4 (positive): penalty={penalty}")

print("Quick test complete!")
