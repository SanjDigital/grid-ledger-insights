#!/usr/bin/env python3
"""Simple E2E test runner with output capture."""

import sys
import traceback

def run_tests():
    print("=" * 80)
    print("END-TO-END INTEGRATION TESTS")
    print("=" * 80)
    
    try:
        from test_e2e_per_cycle import (
            test_e2e_allocation_with_rate_reduction,
            test_scheduler_integration,
            test_advance_rate_gate_blocks_zero_rate
        )
        
        print("\n[TEST 1/3] Allocate → Mark missing → Resolve → Verify rate reduction")
        print("-" * 80)
        try:
            test_e2e_allocation_with_rate_reduction()
            print("✓ TEST 1 PASSED\n")
        except AssertionError as e:
            print(f"✗ TEST 1 FAILED: {e}\n")
            traceback.print_exc()
            return False
        except Exception as e:
            print(f"✗ TEST 1 ERROR: {e}\n")
            traceback.print_exc()
            return False
        
        print("\n[TEST 2/3] Scheduler integration")
        print("-" * 80)
        try:
            test_scheduler_integration()
            print("✓ TEST 2 PASSED\n")
        except Exception as e:
            print(f"✗ TEST 2 FAILED: {e}\n")
            traceback.print_exc()
            return False
        
        print("\n[TEST 3/3] Gate blocks zero advance rate")
        print("-" * 80)
        try:
            test_advance_rate_gate_blocks_zero_rate()
            print("✓ TEST 3 PASSED\n")
        except Exception as e:
            print(f"✗ TEST 3 FAILED: {e}\n")
            traceback.print_exc()
            return False
        
        print("=" * 80)
        print("✓ ALL TESTS PASSED")
        print("=" * 80)
        return True
        
    except ImportError as e:
        print(f"IMPORT ERROR: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
