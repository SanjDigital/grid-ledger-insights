"""
Debug script: Isolate why evaluate_mill_capital returns 0.0 for test_mill_e2e
"""
import sys
import logging
from datetime import datetime, timezone
from sqlmodel import Session, select
from scripts.init_db import engine, Mill
from backend.cycle_manager import evaluate_mill_capital
from backend.trust_scorecard import TrustScorecardGenerator

# Enable all logging to see what happens
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)-8s | %(name)-40s | %(message)s"
)

print("=" * 80)
print("DEBUG: evaluate_mill_capital() Behavior Analysis")
print("=" * 80)

mill_id = "test_mill_e2e"
print(f"\n1. Setting up test mill: {mill_id}")

# Create/verify test mill exists
with Session(engine) as session:
    stmt = select(Mill).where(Mill.id == mill_id)
    mill = session.exec(stmt).first()
    
    if not mill:
        print(f"   Creating new mill...")
        mill = Mill(
            id=mill_id,
            name="E2E Test Mill",
            location="coordinates -17.8, 31.0",
            meter_type="Inhemeter",
            efficiency_baseline=1000.0,
        )
        session.add(mill)
        session.commit()
        print(f"   ✓ Mill {mill_id} created")
    else:
        print(f"   ✓ Mill {mill_id} already exists")

# Get trust score
print(f"\n2. Computing trust score...")
trust_gen = TrustScorecardGenerator(mill_id)
today = datetime.now(timezone.utc)
scorecard = trust_gen.generate_daily_scorecard(today)
trust_score = scorecard["kpis"]["trust_integrity_score"]
print(f"   Trust score: {trust_score:.1f}")

# Call evaluate_mill_capital with explicit error handling
print(f"\n3. Calling evaluate_mill_capital({mill_id}, trust_score={trust_score}, session)...")

with Session(engine) as session:
    try:
        # This is the same call the test makes
        advance_rate = evaluate_mill_capital(mill_id, trust_score, session)
        print(f"   ✓ Result: advance_rate = {advance_rate:.4f} ({advance_rate*100:.1f}%)")
        
        if advance_rate == 0.0:
            print("\n   ⚠️  ZERO RATE RETURNED")
            print("   This usually means an exception was caught and logged.")
            print("   Check the DEBUG logs above for the actual error.")
        else:
            print(f"   ✓ Non-zero rate - no exception")
            
    except Exception as e:
        print(f"   ❌ EXCEPTION RAISED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("If advance_rate=0.0, the issue is in one of these functions:")
print("  • get_last_cycle_adherence()  (line 1161)")
print("  • get_last_cycle_lag()        (line 1215)")
print("  • compute_per_cycle_advance_rate() (policy_execution_engine.py)")
print("=" * 80)
