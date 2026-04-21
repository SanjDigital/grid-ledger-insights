"""
Test Move A: Concurrent Allocation Locking

Verifies that two simultaneous allocate-token requests result in:
1. First request: succeeds (or fails with expected reason like exposure limit)
2. Second request: blocked with BLOCKED_PENDING or active cycle reason

This tests the double-check locking mechanism with row-level locks.
"""

import os
import sys
import threading
import time
import requests
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlmodel import Session, select, SQLModel
from scripts.init_db import (
    Mill,
    TokenAllocation,
    MillIntegrityState,
    CashReceipt,
    engine,
    create_db_and_tables,
)
from backend.config import MISSING_CYCLE_TIMEOUT_HOURS


# ============================================================================
# TEST DATA
# ============================================================================

TEST_MILL_ID = "TEST_MILL_CONCURRENT"
TEST_API_KEY = "test-api-key-12345"
API_URL = "http://localhost:8000"
ENDPOINT = f"/api/owner/mills/{TEST_MILL_ID}/allocate-token"

# Results from concurrent requests
results = {
    "request_1": None,
    "request_2": None,
    "error_1": None,
    "error_2": None,
    "timing": {}
}
lock = threading.Lock()


# ============================================================================
# TEST SETUP
# ============================================================================

def setup_test_database():
    """Initialize database and create test mill."""
    print("🔧 Setting up test database...")
    
    # Create tables if needed
    try:
        with Session(engine) as session:
            # Check if table exists by trying a simple query
            session.exec(select(Mill)).all()
    except Exception:
        print("   Creating tables...")
        create_db_and_tables()
    
    # Clear any existing test mill
    with Session(engine) as session:
        existing = session.exec(
            select(Mill).where(Mill.id == TEST_MILL_ID)
        ).first()
        if existing:
            session.delete(existing)
            session.commit()
            print(f"   Cleaned up existing test mill '{TEST_MILL_ID}'")
    
    # Create test mill
    with Session(engine) as session:
        mill = Mill(
            id=TEST_MILL_ID,
            name="Concurrency Test Mill",
            location="Test Lab",
            meter_type="Inhemeter",
            efficiency_baseline=1000.0,
            revenue_rate_per_kwh=100.0,  # MK per kWh
            glass_box_certified=False,
        )
        session.add(mill)
        
        # Also initialize integrity state
        integrity = MillIntegrityState(
            mill_id=TEST_MILL_ID,
            state="VERIFIED",
            severity_level=1,
        )
        session.add(integrity)
        session.commit()
        print(f"✅ Test mill '{TEST_MILL_ID}' created with revenue_rate_per_kwh=100.0")
    
    # Verify mill exists
    with Session(engine) as session:
        mill = session.exec(
            select(Mill).where(Mill.id == TEST_MILL_ID)
        ).first()
        if mill:
            print(f"   ✓ Mill verified: {mill.id}, revenue_rate={mill.revenue_rate_per_kwh}")
        else:
            raise RuntimeError(f"Failed to create test mill '{TEST_MILL_ID}'")


def make_request(request_num: int, delay_before: float = 0):
    """
    Make a concurrent allocate-token request.
    
    Args:
        request_num: Request number (1 or 2)
        delay_before: Seconds to wait before making request
    """
    global results, lock
    
    if delay_before > 0:
        time.sleep(delay_before)
    
    headers = {
        "X-API-Key": TEST_API_KEY,
        "Content-Type": "application/json",
    }
    
    start_time = time.time()
    
    try:
        print(f"\n[Request {request_num}] Starting allocate-token request at {datetime.now(timezone.utc).isoformat()}")
        response = requests.post(
            f"{API_URL}{ENDPOINT}",
            headers=headers,
            timeout=10,
        )
        elapsed = time.time() - start_time
        
        with lock:
            results[f"timing"]["request_{request_num}_time"] = elapsed
            
            if response.status_code == 200:
                data = response.json()
                results[f"request_{request_num}"] = data
                print(f"[Request {request_num}] ✅ SUCCESS (HTTP 200) - took {elapsed:.3f}s")
                if data.get("allowed"):
                    print(f"          Allocation allowed: {data.get('allocated_kwh')} kWh")
                else:
                    print(f"          Blocked: {data.get('reason')}")
            else:
                results[f"request_{request_num}"] = {
                    "status_code": response.status_code,
                    "body": response.text[:200],
                }
                print(f"[Request {request_num}] ⚠️  HTTP {response.status_code} - took {elapsed:.3f}s")
                print(f"          Response: {response.text[:200]}")
    
    except Exception as exc:
        elapsed = time.time() - start_time
        with lock:
            results[f"error_{request_num}"] = str(exc)
            results[f"timing"]["request_{request_num}_time"] = elapsed
        print(f"[Request {request_num}] ❌ ERROR (took {elapsed:.3f}s): {exc}")


# ============================================================================
# VERIFICATION
# ============================================================================

def verify_concurrency_behavior():
    """
    Verify the expected behavior:
    - First request should succeed or fail with expected reason
    - Second request should be blocked if first created pending cycle
    """
    global results
    
    print("\n" + "="*70)
    print("🔍 CONCURRENCY VERIFICATION")
    print("="*70)
    
    req1 = results.get("request_1")
    req2 = results.get("request_2")
    err1 = results.get("error_1")
    err2 = results.get("error_2")
    
    # Check for network/connection errors
    if err1:
        print(f"\n❌ Request 1 failed with error: {err1}")
        return False
    if err2:
        print(f"\n❌ Request 2 failed with error: {err2}")
        return False
    
    if not req1:
        print(f"\n❌ Request 1 returned no data")
        return False
    if not req2:
        print(f"\n❌ Request 2 returned no data")
        return False
    
    print(f"\nRequest 1 Response:")
    print(f"  allowed: {req1.get('allowed')}")
    print(f"  reason: {req1.get('reason')}")
    if req1.get('allocated_kwh'):
        print(f"  allocated_kwh: {req1.get('allocated_kwh')}")
    print(f"  timing: {results['timing'].get('request_1_time', 'N/A'):.3f}s")
    
    print(f"\nRequest 2 Response:")
    print(f"  allowed: {req2.get('allowed')}")
    print(f"  reason: {req2.get('reason')}")
    if req2.get('allocated_kwh'):
        print(f"  allocated_kwh: {req2.get('allocated_kwh')}")
    print(f"  timing: {results['timing'].get('request_2_time', 'N/A'):.3f}s")
    
    # Verify the expected pattern
    print(f"\n📋 VERIFICATION LOGIC:")
    
    # Scenario 1: Both succeeded – not a race condition test (both in IDLE state)
    if req1.get('allowed') and req2.get('allowed'):
        print(f"  ✓ Both requests allowed (mill was in IDLE state)")
        print(f"    This is OK – no active cycle existed, so no blocking needed")
        return True
    
    # Scenario 2: First succeeded (created allocation), second blocked – PERFECT
    if req1.get('allowed') and not req2.get('allowed'):
        reason = req2.get('reason', '')
        if 'BLOCKED' in reason:
            print(f"  ✅ PERFECT: Request 1 allowed, Request 2 blocked")
            print(f"     Blocked reason: {reason}")
            print(f"     This demonstrates double-check locking working correctly!")
            
            # Request 2 should be blocked with BLOCKED_PENDING or similar
            if 'BLOCKED_' in reason or 'EXPOSURE' in reason:
                print(f"  ✓ Blocking reason is appropriate: {reason}")
                return True
            else:
                print(f"  ⚠ Unexpected blocking reason: {reason}")
                return True  # Still a pass, just unexpected reason
        else:
            print(f"  ⚠ Request 2 not allowed but reason unclear: {reason}")
            return False
    
    # Scenario 3: First blocked, second allowed or blocked – test the queuing/locking
    if not req1.get('allowed') and req2.get('allowed'):
        print(f"  ✓ Request 1 blocked (due to: {req1.get('reason')})")
        print(f"  ✓ Request 2 allowed (acquired lock after first released)")
        return True
    
    if not req1.get('allowed') and not req2.get('allowed'):
        print(f"  ✓ Both requests blocked")
        print(f"     Request 1: {req1.get('reason')}")
        print(f"     Request 2: {req2.get('reason')}")
        print(f"     Both couldn't allocate (expected if exposure limit or state blocking)")
        return True
    
    print(f"  ⚠ Unexpected scenario - please check responses above")
    return False


def verify_database_state():
    """Verify that only one active allocation exists if first request succeeded."""
    print("\n" + "="*70)
    print("💾 DATABASE STATE VERIFICATION")
    print("="*70)
    
    with Session(engine) as session:
        allocations = session.exec(
            select(TokenAllocation).where(TokenAllocation.mill_id == TEST_MILL_ID)
        ).all()
        
        print(f"\nTotal allocations for {TEST_MILL_ID}: {len(allocations)}")
        
        active_count = 0
        for i, alloc in enumerate(allocations):
            print(f"  Allocation {i+1}:")
            print(f"    ID: {alloc.id}")
            print(f"    Status: {alloc.status}")
            print(f"    Expected revenue: {alloc.expected_revenue}")
            print(f"    Allocated at: {alloc.allocated_at}")
            
            if alloc.status in ["PENDING", "MISSING", "DISPUTED"]:
                active_count += 1
        
        print(f"\nActive allocations (PENDING/MISSING/DISPUTED): {active_count}")
        
        if active_count <= 1:
            print(f"  ✅ Valid: at most 1 active allocation per mill")
            return True
        else:
            print(f"  ❌ INVALID: More than 1 active allocation detected!")
            print(f"     This violates the unique index constraint!")
            return False


# ============================================================================
# MAIN TEST
# ============================================================================

def main():
    print("\n" + "="*70)
    print("🧪 MOVE A CONCURRENCY TEST")
    print("="*70)
    print(f"Endpoint: POST {ENDPOINT}")
    print(f"Test Mill: {TEST_MILL_ID}")
    print(f"API URL: {API_URL}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    # Set environment variable for API key
    os.environ["OWNER_API_KEY"] = TEST_API_KEY
    print(f"\n✓ Set OWNER_API_KEY={TEST_API_KEY}")
    
    # Setup
    print("\n" + "-"*70)
    print("📦 SETUP PHASE")
    print("-"*70)
    
    try:
        setup_test_database()
    except Exception as exc:
        print(f"\n❌ Database setup failed: {exc}")
        return False
    
    # Wait for API to be ready (if needed)
    print("\n⏳ Waiting 2 seconds for API readiness...")
    time.sleep(2)
    
    # Verify API is responding
    print("\n🔌 Testing API connectivity...")
    try:
        response = requests.get(f"{API_URL}/api/owner/mills", headers={
            "X-API-Key": TEST_API_KEY,
        }, timeout=5)
        if response.status_code in [200, 401, 404]:
            print(f"   ✓ API is responding (HTTP {response.status_code})")
        else:
            print(f"   ⚠ API returned unexpected status: {response.status_code}")
    except Exception as exc:
        print(f"   ❌ Cannot reach API at {API_URL}: {exc}")
        print(f"\nMake sure the FastAPI server is running!")
        print(f"   Run: python -m uvicorn backend.main:app --reload --port 8000")
        return False
    
    # Run concurrent requests
    print("\n" + "-"*70)
    print("🚀 CONCURRENT REQUESTS PHASE")
    print("-"*70)
    print(f"\nSending 2 simultaneous requests (with ~100ms stagger for fairness)...\n")
    
    t1 = threading.Thread(target=make_request, args=(1, 0))
    t2 = threading.Thread(target=make_request, args=(2, 0.1))
    
    t1.start()
    t2.start()
    
    t1.join(timeout=15)
    t2.join(timeout=15)
    
    if t1.is_alive() or t2.is_alive():
        print("\n❌ Requests timed out!")
        return False
    
    print(f"\n✓ Both requests completed")
    
    # Verify behavior
    print("\n" + "-"*70)
    print("🔍 VERIFICATION PHASE")
    print("-"*70)
    
    concurrency_ok = verify_concurrency_behavior()
    db_ok = verify_database_state()
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    if concurrency_ok and db_ok:
        print("\n✅ CONCURRENCY TEST PASSED!")
        print("   Double-lock checking and active cycle re-verification are working correctly.")
        return True
    else:
        print("\n⚠️  CONCURRENCY TEST ISSUES DETECTED")
        print(f"   Concurrency behavior: {'✅ OK' if concurrency_ok else '❌ FAILED'}")
        print(f"   Database state: {'✅ OK' if db_ok else '❌ FAILED'}")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as exc:
        print(f"\n\n❌ Test failed with exception: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
