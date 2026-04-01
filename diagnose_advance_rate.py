#!/usr/bin/env python3
"""Isolated check: Why does evaluate_mill_capital return 0.0?"""

import sys
from datetime import datetime, timezone
from sqlmodel import Session

print("=" * 80)
print("ISOLATED DIAGNOSIS: evaluate_mill_capital root cause")
print("=" * 80)

try:
    from scripts.init_db import engine, Mill
    from backend.cycle_manager import evaluate_mill_capital
    from backend.trust_scorecard import TrustScorecardGenerator
    from sqlmodel import select
    
    # Test 1: Check if NABIWI exists
    print("\n[STEP 1] Check if NABIWI exists...")
    with Session(engine) as session:
        nabiwi = session.exec(select(Mill).where(Mill.id == "NABIWI")).first()
        if nabiwi:
            print(f"  ✓ NABIWI found: {nabiwi.name}")
        else:
            print("  ✗ NABIWI not found in database")
            sys.exit(1)
    
    # Test 2: Get trust score for NABIWI
    print("\n[STEP 2] Get trust score for NABIWI...")
    try:
        gen = TrustScorecardGenerator("NABIWI")
        scorecard = gen.generate_daily_scorecard(datetime.now(timezone.utc))
        trust_score = scorecard['kpis']['trust_integrity_score']
        print(f"  ✓ Trust score: {trust_score}")
        print(f"  Components: {scorecard['components']}")
    except Exception as e:
        print(f"  ✗ Trust score generation failed: {e}")
        sys.exit(1)
    
    # Test 3: Call evaluate_mill_capital with actual trust score
    print("\n[STEP 3] Call evaluate_mill_capital with actual trust score...")
    with Session(engine) as session:
        try:
            rate = evaluate_mill_capital("NABIWI", trust_score=trust_score, session=session)
            print(f"  ✓ Advance rate: {rate:.4f} ({rate*100:.2f}%)")
        except Exception as e:
            print(f"  ✗ evaluate_mill_capital failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    # Test 4: Test with hypothetical high trust score
    print("\n[STEP 4] Test with hypothetical high trust score (85.0)...")
    with Session(engine) as session:
        try:
            rate_high = evaluate_mill_capital("NABIWI", trust_score=85.0, session=session)
            print(f"  ✓ Advance rate (trust=85): {rate_high:.4f} ({rate_high*100:.2f}%)")
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            sys.exit(1)
    
    # Test 5: Test with new mill (test_mill_e2e)
    print("\n[STEP 5] Test with new mill (test_mill_e2e)...")
    with Session(engine) as session:
        try:
            rate_new = evaluate_mill_capital("test_mill_e2e", trust_score=85.0, session=session)
            print(f"  ✓ Advance rate (new mill, trust=85): {rate_new:.4f} ({rate_new*100:.2f}%)")
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 80)
    print("DIAGNOSIS SUMMARY")
    print("=" * 80)
    
    if rate_high > 0.0:
        print(f"✓ With trust_score=85, rate is normal ({rate_high*100:.2f}%)")
        print(f"  → Trust score of {trust_score} is the limiting factor")
        print(f"  → Gate will NOT block new mills if trust_score > 0")
    else:
        print(f"✗ Even with trust_score=85, rate is 0.0")
        print(f"  → CRITICAL: Gate will block all token issuance")
        print(f"  → Root cause: evaluate_mill_capital or latency_penalty returning 0")
        
except Exception as e:
    print(f"\nFATAL ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    print("=" * 80)
