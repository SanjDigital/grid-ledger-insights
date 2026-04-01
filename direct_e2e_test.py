#!/usr/bin/env python3
"""Direct test execution with explicit output."""

import sys
import os

# Add project root to path
sys.path.insert(0, r'c:\Users\USER\Documents\Python Projets\gridledger')

print("=" * 80, flush=True)
print("DIRECT E2E TEST EXECUTION", flush=True)
print("=" * 80, flush=True)

try:
    print("\nImporting test module...", flush=True)
    from test_e2e_per_cycle import (
        test_e2e_allocation_with_rate_reduction,
        test_scheduler_integration,
        test_advance_rate_gate_blocks_zero_rate
    )
    print("✓ Module imported successfully\n", flush=True)
    
    # TEST 1
    print("[TEST 1/3] Allocation lifecycle with rate reduction", flush=True)
    print("-" * 80, flush=True)
    try:
        test_e2e_allocation_with_rate_reduction()
        print("\n✓ TEST 1 PASSED\n", flush=True)
        test1_pass = True
    except Exception as e:
        print(f"\n✗ TEST 1 FAILED: {type(e).__name__}: {str(e)[:200]}\n", flush=True)
        test1_pass = False
    
    # TEST 2
    print("[TEST 2/3] Scheduler integration", flush=True)
    print("-" * 80, flush=True)
    try:
        test_scheduler_integration()
        print("\n✓ TEST 2 PASSED\n", flush=True)
        test2_pass = True
    except Exception as e:
        print(f"\n✗ TEST 2 FAILED: {type(e).__name__}: {str(e)[:200]}\n", flush=True)
        test2_pass = False
    
    # TEST 3
    print("[TEST 3/3] Gate validation (zero rate blocks issuance)", flush=True)
    print("-" * 80, flush=True)
    try:
        test_advance_rate_gate_blocks_zero_rate()
        print("\n✓ TEST 3 PASSED\n", flush=True)
        test3_pass = True
    except Exception as e:
        print(f"\n✗ TEST 3 FAILED: {type(e).__name__}: {str(e)[:200]}\n", flush=True)
        test3_pass = False
    
    # Summary
    print("=" * 80, flush=True)
    passed = sum([test1_pass, test2_pass, test3_pass])
    total = 3
    print(f"RESULTS: {passed}/{total} tests passed", flush=True)
    
    if passed == total:
        print("✓ ALL TESTS PASSED - PRODUCTION READY", flush=True)
        sys.exit(0)
    else:
        print(f"✗ {total - passed} test(s) failed", flush=True)
        sys.exit(1)
        
except Exception as e:
    print(f"\nFATAL ERROR: {type(e).__name__}: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    print("=" * 80, flush=True)
