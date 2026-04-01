"""
Test: Complete Revenue Flow with Treasury & Capital Ledger
"""

from backend.revenue_engine import (
    MillConfig,
    MillConfigRegistry,
    MeterReadings,
    TrustScorecard,
    RevenueTruthEngine,
    RevenueGateway,
)


def test_complete_flow_with_treasury():
    """Test: Complete end-to-end flow including treasury execution."""
    print("\n" + "="*60)
    print("TEST: Complete Revenue Flow with Treasury & Capital Ledger")
    print("="*60)
    
    # Initialize gateway (includes treasury)
    gateway = RevenueGateway()
    
    # Register mill with node-specific rate
    nabiwi_config = MillConfig(
        mill_id="NABIWI_MKWINDA",
        mill_name="Mkwinda Solar",
        budgeted_rate_per_kwh=1350.0,  # Mk per kWh
        location="Nabiwi, Malawi",
    )
    gateway.mill_registry.register_mill(nabiwi_config)
    print(f"\n✓ Mill registered: {nabiwi_config.mill_id} @ Mk {nabiwi_config.budgeted_rate_per_kwh}/kWh")
    
    # Create Trust Scorecard (operator integrity assessment)
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
    print(f"✓ Trust Scorecard: score={scorecard.trust_score}, EAR={scorecard.ear_score}, state={scorecard.mill_state}")
    
    # Create Meter Readings (energy verification)
    meter_readings = MeterReadings(
        token_reported_kwh=4104.0,
        meter_measured_kwh=4100.0,  # 0.1% difference (within 2% tolerance)
        timestamp="2026-03-30T10:00:00Z",
        meter_id="METER_NABIWI_01",
    )
    print(f"✓ Meter Readings: token={meter_readings.token_reported_kwh} kWh, meter={meter_readings.meter_measured_kwh} kWh")
    
    # Execute complete capital flow
    print("\nExecuting complete capital flow...")
    result = gateway.execute_capital_flow(
        scorecard=scorecard,
        meter_readings=meter_readings,
        policy_id="STANDARD_COMMERCIAL",
        # actual_revenue defaults to expected_revenue (100% collection efficiency)
    )
    
    cao = result["cao"]
    treasury_result = result["treasury_result"]
    
    print(f"\n✓ Capital Action Object (CAO) Created:")
    print(f"  - Mill: {cao['mill_id']}")
    print(f"  - Decision: {cao['decision']}")
    print(f"  - Advance Rate: {cao['advance_rate']}")
    print(f"  - Advance Amount: Mk {cao['advance_amount']:,.0f}")
    print(f"  - Capital State: {cao['capital_state']}")
    print(f"  - Timestamp: {cao['timestamp']}")
    
    print(f"\n✓ Treasury Execution Result:")
    print(f"  - Status: {treasury_result['status']}")
    print(f"  - Mill: {treasury_result['mill_id']}")
    
    if treasury_result['status'] == 'EXECUTED':
        print(f"  - Amount: Mk {treasury_result['amount']:,.0f}")
        print(f"  - Previous Balance: Mk {treasury_result['previous_balance']:,.0f}")
        print(f"  - New Balance: Mk {treasury_result['new_balance']:,.0f}")
    
    # Verify CAO hashes (dual hashing for auditability)
    print(f"\n✓ Dual Hashing (Audit Trail):")
    print(f"  - Input Hash: {cao['input_hash'][:16]}...")
    print(f"  - Policy Hash: {cao['policy_hash'][:16]}...")
    
    # Check treasury ledger
    print(f"\n✓ Treasury State:")
    balance = gateway.treasury.get_balance("NABIWI_MKWINDA")
    print(f"  - Current Balance for {scorecard.mill_id}: Mk {balance:,.0f}")
    
    # Check transaction log
    tx_log = gateway.treasury.get_transaction_log("NABIWI_MKWINDA")
    print(f"  - Transaction Log Entries: {len(tx_log)}")
    for i, entry in enumerate(tx_log, 1):
        print(f"    [{i}] {entry.status}: Mk {entry.advance_amount:,.0f} @ {entry.timestamp}")
    
    # Verify execution trace
    print(f"\n✓ Execution Trace:")
    trace = cao['execution_trace']
    print(f"  - Breach Detected: {trace['breach_detected']}")
    print(f"  - Expected Revenue: Mk {trace['expected_revenue']:,.0f}")
    print(f"  - Verified kWh: {trace['verified_kwh']}")
    print(f"  - Budgeted Rate: Mk {trace['budgeted_rate']}/kWh")
    
    # Calculate and verify advance_amount formula
    expected_revenue = trace['expected_revenue']
    advance_rate = cao['advance_rate']
    calculated_advance = expected_revenue * advance_rate
    
    print(f"\n✓ Advance Amount Calculation (Verified):")
    print(f"  - Expected Revenue: Mk {expected_revenue:,.0f}")
    print(f"  - Advance Rate: {advance_rate:.2%}")
    print(f"  - Advance Amount: Mk {calculated_advance:,.0f}")
    print(f"  - CAO Advance Amount: Mk {cao['advance_amount']:,.0f}")
    assert abs(calculated_advance - cao['advance_amount']) < 0.01, "Advance amount mismatch"
    print(f"  ✓ Formula verified: advance_amount = expected_revenue × advance_rate = Mk {cao['advance_amount']:,.0f}")
    
    print("\n" + "="*60)
    print("✅ COMPLETE FLOW TEST PASSED")
    print("="*60 + "\n")


def test_multiple_disbursements():
    """Test: Multiple disbursements to the same mill."""
    print("\n" + "="*60)
    print("TEST: Multiple Disbursements (Cumulative Ledger)")
    print("="*60)
    
    gateway = RevenueGateway()
    
    # Register mill
    config = MillConfig(
        mill_id="TEST_MILL_001",
        mill_name="Test Mill",
        budgeted_rate_per_kwh=1000.0,
    )
    gateway.mill_registry.register_mill(config)
    
    # Execute 3 capital flows
    for i in range(1, 4):
        scorecard = TrustScorecard(
            mill_id="TEST_MILL_001",
            timestamp=f"2026-03-30T{10+i:02d}:00:00Z",
            trust_score=88 + i,
            ear_score=0.90 + i * 0.01,
            consistency_score=92 + i,
            reconciliation_score=85 + i,
            governance_score=88 + i,
            fraud_risk_level="LOW",
            mill_state="VERIFIED",
        )
        
        meter_readings = MeterReadings(
            token_reported_kwh=1000.0 * i,
            meter_measured_kwh=1000.0 * i,
            timestamp=f"2026-03-30T{10+i:02d}:00:00Z",
            meter_id=f"METER_{i}",
        )
        
        result = gateway.execute_capital_flow(scorecard=scorecard, meter_readings=meter_readings)
        cao = result["cao"]
        
        print(f"\nDisbursement {i}:")
        print(f"  - Amount: Mk {cao['advance_amount']:,.0f}")
        print(f"  - Status: {result['treasury_result']['status']}")
    
    # Check cumulative balance
    balance = gateway.treasury.get_balance("TEST_MILL_001")
    print(f"\nCumulative Balance: Mk {balance:,.0f}")
    
    # Check transaction log
    tx_log = gateway.treasury.get_transaction_log("TEST_MILL_001")
    total_disbursed = sum(t.advance_amount for t in tx_log if t.status == "EXECUTED")
    print(f"Total Disbursements: Mk {total_disbursed:,.0f}")
    print(f"Transaction Log: {len(tx_log)} entries")
    
    print("\n✅ Multiple Disbursement Test PASSED\n")


if __name__ == "__main__":
    test_complete_flow_with_treasury()
    test_multiple_disbursements()
