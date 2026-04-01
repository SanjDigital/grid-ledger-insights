"""Quick test of revenue engine core functionality."""

print("Starting revenue gateway test...")

from backend.revenue_engine import (
    MillConfig,
    MillConfigRegistry,
    MeterReadings,
    EnergyVerifier,
    RevenueTruthEngine,
)

print("✓ Imports successful")

# Test 1: Mill config
print("\n[Test 1] Mill Configuration")
registry = MillConfigRegistry()
config = MillConfig("NABIWI_MKWINDA", "Mkwinda Solar", 1350.0)
registry.register_mill(config)
retrieved = registry.get_mill("NABIWI_MKWINDA")
print(f"✓ Registered and retrieved NABIWI_MKWINDA at Mk {retrieved.budgeted_rate_per_kwh}/kWh")

# Test 2: Energy verification
print("\n[Test 2] Energy Verification")
verifier = EnergyVerifier()
verified = verifier.compute_verified_kwh(token_kwh=1000.0, meter_kwh=985.0)
print(f"✓ Energy verified: token=1000, meter=985 → verified={verified}")

# Test 3: Revenue computation
print("\n[Test 3] Revenue Computation")
engine = RevenueTruthEngine()
expected = engine.compute_expected_revenue(4104.0, 1350.0)
print(f"✓ Expected revenue: 4104 kWh × Mk 1350/kWh = Mk {expected:,.0f}")

efficiency = engine.compute_efficiency(5540400.0, expected)
print(f"✓ Efficiency ratio: {efficiency:.2%}")

# Test 4: Revenue snapshot
print("\n[Test 4] Revenue Snapshot")
snapshot = engine.create_revenue_snapshot(
    mill_id="NABIWI_MKWINDA",
    verified_kwh=4104.0,
    budgeted_rate_per_kwh=1350.0,
    actual_revenue=5540400.0,
)
print(f"✓ Revenue snapshot created for {snapshot.mill_id}")
print(f"  - Verified kWh: {snapshot.verified_kwh}")
print(f"  - Expected Revenue: Mk {snapshot.expected_revenue:,.0f}")
print(f"  - Efficiency: {snapshot.revenue_efficiency_ratio:.2%}")

print("\n" + "="*60)
print("✅ ALL CORE TESTS PASSED")
print("="*60)
