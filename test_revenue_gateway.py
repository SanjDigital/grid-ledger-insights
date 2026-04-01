"""
Test: Complete Revenue Gateway (Energy → Revenue → Policy → Capital)

Validate:
1. Mill config system (node-level rates, no hardcoding)
2. Energy verification (2% tolerance)
3. Revenue computation (expected vs actual)
4. PXE input mapping (direct, no transformation)
5. Breach overrides (pre-policy enforcement)
6. CAO factory (dual hashing)
7. Policy execution
"""

from backend.revenue_engine import (
    MillConfig,
    MillConfigRegistry,
    MeterReadings,
    EnergyVerifier,
    RevenueTruthEngine,
    TrustScorecard,
    PXEInputFactory,
    BreachOverride,
    CAOFactory,
    PolicyRegistry,
    RevenueGateway,
    MeterVerificationError,
)


def test_mill_config():
    """Test: Mill configuration with node-specific rates."""
    print("\n=== TEST: Mill Config (Node-Specific Rates) ===")
    
    registry = MillConfigRegistry()
    
    # Register NABIWI_MKWINDA with Mk 1350/kWh
    nabiwi_config = MillConfig(
        mill_id="NABIWI_MKWINDA",
        mill_name="Mkwinda Solar (Nabiwi)",
        budgeted_rate_per_kwh=1350.0,  # Mk per kWh, node-specific
        location="Nabiwi, Malawi",
    )
    
    registry.register_mill(nabiwi_config)
    
    # Verify retrieval
    retrieved = registry.get_mill("NABIWI_MKWINDA")
    assert retrieved.budgeted_rate_per_kwh == 1350.0, "Rate mismatch"
    
    # Verify no global default
    try:
        registry.get_mill("UNKNOWN_MILL")
        assert False, "Should reject missing mill"
    except ValueError as e:
        print(f"✓ Correctly rejected missing mill: {e}")
    
    print(f"✓ NABIWI_MKWINDA registered with Mk {nabiwi_config.budgeted_rate_per_kwh}/kWh")


def test_energy_verification():
    """Test: Independent meter verification with 2% tolerance."""
    print("\n=== TEST: Energy Verification (2% Tolerance) ===")
    
    verifier = EnergyVerifier()
    
    # Case 1: Perfect match
    verified = verifier.compute_verified_kwh(
        token_kwh=1000.0,
        meter_kwh=1000.0,
    )
    assert verified == 1000.0, "Perfect match failed"
    print(f"✓ Perfect match: token=1000, meter=1000 → verified={verified}")
    
    # Case 2: Within tolerance (1.5% mismatch)
    verified = verifier.compute_verified_kwh(
        token_kwh=1000.0,
        meter_kwh=985.0,  # 1.5% lower
    )
    assert verified == 985.0, "Within tolerance failed"
    print(f"✓ Within tolerance: token=1000, meter=985 (1.5%) → verified={verified}")
    
    # Case 3: Exceeds tolerance (2.5% mismatch)
    try:
        verifier.compute_verified_kwh(
            token_kwh=1000.0,
            meter_kwh=975.0,  # 2.5% lower
        )
        assert False, "Should reject 2.5% mismatch"
    except MeterVerificationError as e:
        print(f"✓ Correctly rejected mismatch: {e}")


def test_revenue_truth_engine():
    """Test: Expected revenue computation."""
    print("\n=== TEST: Revenue Truth Engine ===")
    
    engine = RevenueTruthEngine()
    
    # Scenario: NABIWI_MKWINDA with 4104 kWh @ Mk 1350/kWh
    verified_kwh = 4104.0
    budgeted_rate = 1350.0
    
    expected_revenue = engine.compute_expected_revenue(verified_kwh, budgeted_rate)
    expected_calc = 4104.0 * 1350.0
    
    assert expected_revenue == expected_calc, "Revenue calculation mismatch"
    print(f"✓ Expected revenue: {verified_kwh} kWh × Mk {budgeted_rate}/kWh = Mk {expected_revenue:,.0f}")
    
    # Efficiency: operator reported Mk 5,550,000 (perfect match)
    actual_revenue = 5540400.0
    efficiency = engine.compute_efficiency(actual_revenue, expected_revenue)
    print(f"✓ Efficiency: {actual_revenue:,.0f} / {expected_revenue:,.0f} = {efficiency:.2%}")


def test_pxe_input_mapping():
    """Test: Trust Scorecard → PXE Input (Direct, No Transformation)."""
    print("\n=== TEST: PXE Input Mapping (Direct Passthrough) ===")
    
    # Trust Scorecard output
    scorecard = TrustScorecard(
        mill_id="NABIWI_MKWINDA",
        timestamp="2026-03-30T10:00:00Z",
        trust_score=89,
        ear_score=0.92,
        consistency_score=95,
        reconciliation_score=88,
        governance_score=90,
        fraud_risk_level="LOW",
        mill_state="VERIFIED",
    )
    
    # Revenue Snapshot
    revenue_snapshot = RevenueTruthEngine.create_revenue_snapshot(
        mill_id="NABIWI_MKWINDA",
        verified_kwh=4104.0,
        budgeted_rate_per_kwh=1350.0,
        actual_revenue=5540400.0,
    )
    
    # Direct mapping (no transformation)
    pxe_input = PXEInputFactory.from_scorecard_and_revenue(
        scorecard, revenue_snapshot
    )
    
    assert pxe_input.trust_score == 89, "trust_score not mapped"
    assert pxe_input.revenue_efficiency_ratio == (5540400.0 / 5540400.0), "efficiency not mapped"
    
    print(f"✓ PXE Input constructed (direct, no transformation)")
    print(f"  - trust_score: {pxe_input.trust_score}")
    print(f"  - revenue_efficiency: {pxe_input.revenue_efficiency_ratio:.2%}")


def test_breach_overrides():
    """Test: Breach override layer (pre-policy enforcement)."""
    print("\n=== TEST: Breach Overrides (Pre-Policy) ===")
    
    # Case 1: No breach
    scorecard = TrustScorecard(
        mill_id="NABIWI_MKWINDA",
        timestamp="2026-03-30T10:00:00Z",
        trust_score=89,
        ear_score=0.92,
        consistency_score=95,
        reconciliation_score=88,
        governance_score=90,
        fraud_risk_level="LOW",
        mill_state="VERIFIED",
    )
    
    revenue_snapshot = RevenueTruthEngine.create_revenue_snapshot(
        mill_id="NABIWI_MKWINDA",
        verified_kwh=4104.0,
        budgeted_rate_per_kwh=1350.0,
        actual_revenue=5540400.0,
    )
    
    pxe_input = PXEInputFactory.from_scorecard_and_revenue(
        scorecard, revenue_snapshot
    )
    
    breach_eval = BreachOverride.evaluate(pxe_input)
    assert not breach_eval["breach_detected"], "False positive breach detection"
    print(f"✓ No breach: {breach_eval['reason']}")
    
    # Case 2: Mill suspended
    scorecard_suspended = TrustScorecard(
        mill_id="NABIWI_MKWINDA",
        timestamp="2026-03-30T10:00:00Z",
        trust_score=89,
        ear_score=0.92,
        consistency_score=95,
        reconciliation_score=88,
        governance_score=90,
        fraud_risk_level="LOW",
        mill_state="SUSPENDED",  # ← Breach
    )
    
    pxe_input_suspended = PXEInputFactory.from_scorecard_and_revenue(
        scorecard_suspended, revenue_snapshot
    )
    
    breach_eval_suspended = BreachOverride.evaluate(pxe_input_suspended)
    assert breach_eval_suspended["breach_detected"], "Did not detect SUSPENDED state"
    assert breach_eval_suspended["override_action"] == "REJECT", "Should reject SUSPENDED"
    print(f"✓ Breach detected: {breach_eval_suspended['reason']}")


def test_cao_factory():
    """Test: Capital Action Object with dual hashing."""
    print("\n=== TEST: CAO Factory (Dual Hashing) ===")
    
    scorecard = TrustScorecard(
        mill_id="NABIWI_MKWINDA",
        timestamp="2026-03-30T10:00:00Z",
        trust_score=89,
        ear_score=0.92,
        consistency_score=95,
        reconciliation_score=88,
        governance_score=90,
        fraud_risk_level="LOW",
        mill_state="VERIFIED",
    )
    
    revenue_snapshot = RevenueTruthEngine.create_revenue_snapshot(
        mill_id="NABIWI_MKWINDA",
        verified_kwh=4104.0,
        budgeted_rate_per_kwh=1350.0,
        actual_revenue=5540400.0,
    )
    
    pxe_input = PXEInputFactory.from_scorecard_and_revenue(
        scorecard, revenue_snapshot
    )
    
    # Create CAO
    policy_dict = {
        "policy_id": "STANDARD_COMMERCIAL",
        "version": "1.0",
        "rules": [],
    }
    
    cao = CAOFactory.create(
        pxe_input=pxe_input,
        decision="APPROVE",
        advance_rate=0.50,
        capital_state="OPEN",
        policy_dict=policy_dict,
        execution_trace={"test": "trace"},
    )
    
    assert cao.mill_id == "NABIWI_MKWINDA", "CAO mill_id mismatch"
    assert cao.decision == "APPROVE", "CAO decision mismatch"
    assert len(cao.input_hash) == 64, "Input hash should be SHA256 (64 hex chars)"
    assert len(cao.policy_hash) == 64, "Policy hash should be SHA256 (64 hex chars)"
    
    print(f"✓ CAO created:")
    print(f"  - Mill: {cao.mill_id}")
    print(f"  - Decision: {cao.decision}")
    print(f"  - Advance Rate: {cao.advance_rate}")
    print(f"  - Capital State: {cao.capital_state}")
    print(f"  - Input Hash: {cao.input_hash[:16]}...")
    print(f"  - Policy Hash: {cao.policy_hash[:16]}...")


def test_revenue_gateway_complete():
    """Test: Complete end-to-end revenue flow."""
    print("\n=== TEST: Complete Revenue Gateway ===")
    
    gateway = RevenueGateway()
    
    # Register mill
    nabiwi_config = MillConfig(
        mill_id="NABIWI_MKWINDA",
        mill_name="Mkwinda Solar",
        budgeted_rate_per_kwh=1350.0,
    )
    gateway.mill_registry.register_mill(nabiwi_config)
    
    # Trust Scorecard
    scorecard = TrustScorecard(
        mill_id="NABIWI_MKWINDA",
        timestamp="2026-03-30T10:00:00Z",
        trust_score=89,
        ear_score=0.92,
        consistency_score=95,
        reconciliation_score=88,
        governance_score=90,
        fraud_risk_level="LOW",
        mill_state="VERIFIED",
    )
    
    # Meter Readings
    meter_readings = MeterReadings(
        token_reported_kwh=4104.0,
        meter_measured_kwh=4100.0,  # 0.1% difference (within 2% tolerance)
        timestamp="2026-03-30T10:00:00Z",
        meter_id="METER_NABIWI_01",
    )
    
    # Execute capital flow
    cao = gateway.execute_capital_flow(
        scorecard=scorecard,
        meter_readings=meter_readings,
        policy_id="STANDARD_COMMERCIAL",
    )
    
    print(f"✓ Capital flow complete:")
    print(f"  - Decision: {cao.decision}")
    print(f"  - Advance Rate: {cao.advance_rate}")
    print(f"  - Capital State: {cao.capital_state}")
    print(f"  - Timestamp: {cao.timestamp}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("REVENUE ENGINE TEST SUITE")
    print("="*60)
    
    test_mill_config()
    test_energy_verification()
    test_revenue_truth_engine()
    test_pxe_input_mapping()
    test_breach_overrides()
    test_cao_factory()
    test_revenue_gateway_complete()
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED")
    print("="*60)
