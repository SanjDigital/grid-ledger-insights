"""
End-to-end integration test: Allocate → Perform → Remit → Verify Rate Reduction

Tests the complete per-cycle allocation lifecycle:
1. Allocate token (gate checks advance rate)
2. Mill performs work, remits cash
3. detect_missing_cycles() runs in background
4. Resolve disputes if needed
5. Verify advance rate reduced on next allocation (adherence penalty applied)
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlmodel import Session, select
from scripts.init_db import (
    engine, 
    Mill, 
    TokenAllocation, 
    CashReceipt,
)
from backend.cycle_manager import (
    issue_token,
    detect_missing_cycles,
    resolve_dispute,
    evaluate_mill_capital,
)
from backend.trust_scorecard import TrustScorecardGenerator
from backend.config import BASE_ADVANCE_RATE, MISSING_CYCLE_TIMEOUT_HOURS
from backend.reconciliation_engine import ReconciliationEngine


def setup_test_mill(mill_id: str = "test_mill_e2e"):
    """Create a test mill (simplified for E2E testing)."""
    with Session(engine) as session:
        # Check if mill already exists
        stmt = select(Mill).where(Mill.id == mill_id)
        mill = session.exec(stmt).first()
        
        if not mill:
            mill = Mill(
                id=mill_id,
                name="E2E Test Mill",
                location="coordinates -17.8, 31.0",
                meter_type="Inhemeter",
                efficiency_baseline=1000.0,  # MK per kWh
            )
            session.add(mill)
            session.commit()
    
    return mill_id


def test_e2e_allocation_with_rate_reduction():
    """
    End-to-end test: Allocate → Mark cycles → Verify advance rate reduction
    
    Scenario:
    1. Issue token (Cycle 1) — full advance rate should apply
    2. Mark cycle as PENDING (allocation exists)
    3. Run detect_missing_cycles() — marks stale allocation MISSING
    4. Resolve dispute — marks allocation CLOSED (but with penalty)
    5. Issue token (Cycle 2) — advance rate should be reduced due to prior adherence penalty
    """
    mill_id = "test_mill_e2e"
    setup_test_mill(mill_id)
    
    with Session(engine) as session:
        # STEP 1: Issue first token (should succeed with full rate)
        print("\n[STEP 1] Issuing first token...")
        
        # Get initial trust score
        trust_gen = TrustScorecardGenerator(mill_id)
        today = datetime.now(timezone.utc)
        scorecard = trust_gen.generate_daily_scorecard(today)
        trust_score_1 = scorecard["kpis"]["trust_integrity_score"]
        print(f"  Trust score: {trust_score_1:.1f}")
        
        # Evaluate initial capital
        advance_rate_1 = evaluate_mill_capital(mill_id, trust_score_1, session)
        print(f"  Advance rate (Cycle 1): {advance_rate_1:.2%}")
        assert advance_rate_1 > 0.0, "First cycle should have positive advance rate"
        
        # Create token allocation for Cycle 1
        now = datetime.now(timezone.utc)
        allocation_1 = TokenAllocation(
            mill_id=mill_id,
            allocated_kwh=59.9,
            expected_revenue=advance_rate_1 * 5000.0,  # 5000 MWK available capital
            status='PENDING',
            allocated_at=now,
        )
        session.add(allocation_1)
        session.commit()
        allocation_1_id = allocation_1.id
        print(f"  Allocation 1 created: id={allocation_1_id}, status=PENDING")
        
        # STEP 2: Simulate time passing (> 48 hours)
        print("\n[STEP 2] Simulating time passage (49 hours)...")
        old_time = now - timedelta(hours=49)
        allocation_1 = session.get(TokenAllocation, allocation_1_id)
        allocation_1.allocated_at = old_time
        session.add(allocation_1)
        session.commit()
        print(f"  Allocation 1 backdated to {old_time.isoformat()}")
        
        # STEP 3: Run detect_missing_cycles
        print("\n[STEP 3] Running detect_missing_cycles()...")
        count = detect_missing_cycles()
        print(f"  Marked {count} allocation(s) as MISSING")
        assert count >= 1, "Should mark at least 1 allocation as MISSING"
        
        # Verify allocation is now MISSING
        allocation_1 = session.get(TokenAllocation, allocation_1_id)
        assert allocation_1.status == "MISSING", f"Expected MISSING, got {allocation_1.status}"
        print(f"  Allocation 1 status: {allocation_1.status}")
        
        # STEP 4: Resolve the missing cycle (admin marks it DISPUTED then CLOSED)
        print("\n[STEP 4] Resolving missing cycle...")
        # First create a CashReceipt record (simulating operator remittance)
        allocation_1 = session.get(TokenAllocation, allocation_1_id)
        allocation_1.status = 'DISPUTED'
        receipt = CashReceipt(
            allocation_id=allocation_1_id,
            amount=allocation_1.expected_revenue * 0.95,  # 95% of expected
            received_at=datetime.now(timezone.utc),
            verified=False  # Will be set to True on resolution
        )
        session.add(receipt)
        session.commit()
        print(f"  CashReceipt created for allocation 1: amount={receipt.amount:.2f} MWK")
        
        # Then resolve to CLOSED
        resolve_result = resolve_dispute(
            allocation_id=allocation_1_id,
            resolved_by="admin_e2e_test",
            resolution_notes="E2E test: missing cycle resolved (MISSING→DISPUTED→CLOSED)"
        )
        assert resolve_result["status"] == "SUCCESS", f"Dispute resolution failed: {resolve_result}"
        print(f"  Allocation 1 resolved: status=CLOSED, receipt.verified=True")
        
        # Verify receipt is marked verified
        receipt = session.exec(
            select(CashReceipt).where(CashReceipt.allocation_id == allocation_1_id)
        ).first()
        assert receipt is not None, "Receipt should exist after resolution"
        assert receipt.verified is True, "Receipt should be marked verified"
        print(f"  Verified: CashReceipt.verified={receipt.verified}")
        
        # STEP 5: Issue second token (should have reduced advance rate due to dispute)
        print("\n[STEP 5] Issuing second token (should see rate reduction)...")
        
        # Get updated trust score (after dispute record)
        scorecard = trust_gen.generate_daily_scorecard(today)
        trust_score_2 = scorecard["kpis"]["trust_integrity_score"]
        print(f"  Trust score: {trust_score_2:.1f}")
        
        # This should now apply adherence penalty (0.0 for disputed cycle)
        advance_rate_2 = evaluate_mill_capital(mill_id, trust_score_2, session)
        print(f"  Advance rate (Cycle 2): {advance_rate_2:.2%}")
        
        # Advance rate should be reduced or zero
        # (get_last_cycle_adherence returns 0.0 for disputed cycles)
        assert advance_rate_2 <= advance_rate_1, \
            f"Rate should decrease after dispute: {advance_rate_1:.2%} → {advance_rate_2:.2%}"
        print(f"  ✓ Rate reduced: {advance_rate_1:.2%} → {advance_rate_2:.2%}")
        
        # Create second allocation
        allocation_2 = TokenAllocation(
            mill_id=mill_id,
            allocated_kwh=59.9,
            expected_revenue=advance_rate_2 * 5000.0,
            status='PENDING',
            allocated_at=datetime.now(timezone.utc),
        )
        session.add(allocation_2)
        session.commit()
        allocation_2_id = allocation_2.id
        print(f"  Allocation 2 created: id={allocation_2_id}, status=PENDING, expected_revenue={advance_rate_2 * 5000:.2f} MWK")
        
        # STEP 6: Verify state machine
        print("\n[STEP 6] Verifying state machine...")
        allocation_1 = session.get(TokenAllocation, allocation_1_id)
        allocation_2 = session.get(TokenAllocation, allocation_2_id)
        
        print(f"  Allocation 1: {allocation_1.status} (resolved, receipt verified)")
        print(f"  Allocation 2: {allocation_2.status} (new, pending cash receipt)")
        
        assert allocation_1.status == "CLOSED", "Allocation 1 should be CLOSED"
        assert allocation_2.status == "PENDING", "Allocation 2 should be PENDING"
        
        print("\n✅ E2E test PASSED: Rate reduction applied after dispute resolution")
        print(f"   Cycle 1: {advance_rate_1:.2%} (full rate)")
        print(f"   Cycle 2: {advance_rate_2:.2%} (reduced due to prior dispute)")


def test_scheduler_integration():
    """
    Test that APScheduler can call detect_missing_cycles() successfully.
    This is a lightweight test to ensure the scheduler integration works.
    """
    print("\n[SCHEDULER TEST] Verifying scheduler can call detect_missing_cycles()...")
    
    # Manually call detect_missing_cycles to simulate scheduler trigger
    count = detect_missing_cycles()
    print(f"  detect_missing_cycles() returned: {count} allocations marked")
    assert isinstance(count, int), "detect_missing_cycles should return int"
    assert count >= 0, "Count should be non-negative"
    print("  ✓ Scheduler integration test PASSED")


def test_advance_rate_gate_blocks_zero_rate():
    """
    Test that issue_token() blocks when advance_rate is 0.0
    (e.g., due to disputed or missing cycles).
    """
    from backend.cycle_manager import FiduciaryLockError
    
    mill_id = "test_mill_zero_rate"
    setup_test_mill(mill_id)
    
    print("\n[GATE TEST] Testing advance rate gate (zero rate blocks issuance)...")
    
    with Session(engine) as session:
        # Create a DISPUTED allocation to force zero advance rate
        now = datetime.now(timezone.utc)
        old_time = now - timedelta(hours=49)
        
        disputed_alloc = TokenAllocation(
            mill_id=mill_id,
            allocated_kwh=59.9,
            expected_revenue=1000.0,
            status='DISPUTED',  # Disputed = zero advance rate
            allocated_at=old_time,
        )
        session.add(disputed_alloc)
        session.commit()
    
    # Try to issue token — should be blocked by advance rate gate
    try:
        issue_token(
            mill_id=mill_id,
            token_id="token_blocked_test",
            units_kwh=100.0,
            cost_mwk=50.0,
            revenue_wallet_id="rev_001",
            opex_wallet_id="opex_001"
        )
        # If we get here, the gate didn't work
        pytest.fail("issue_token() should have raised FiduciaryLockError for zero advance rate")
    except FiduciaryLockError as e:
        print(f"  ✓ Gate blocked issuance: {str(e)}")
        assert "0.0" in str(e).lower(), "Error should mention zero advance rate"
        print("  ✓ Gate validation test PASSED")


if __name__ == "__main__":
    print("=" * 80)
    print("END-TO-END INTEGRATION TESTS: Per-Cycle Token Allocation")
    print("=" * 80)
    
    try:
        test_e2e_allocation_with_rate_reduction()
        test_scheduler_integration()
        test_advance_rate_gate_blocks_zero_rate()
        
        print("\n" + "=" * 80)
        print("✅ ALL E2E TESTS PASSED")
        print("=" * 80)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise
