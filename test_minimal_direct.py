"""
Minimal direct test: Call evaluate_mill_capital exactly as test_e2e does
"""
from datetime import datetime, timezone
from sqlmodel import Session, select
from scripts.init_db import engine, Mill
from backend.cycle_manager import evaluate_mill_capital
from backend.trust_scorecard import TrustScorecardGenerator

mill_id = "test_mill_e2e_minimal"

# Step 1: Create mill
print("[1] Creating mill...")
with Session(engine) as session:
    stmt = select(Mill).where(Mill.id == mill_id)
    mill = session.exec(stmt).first()
    if not mill:
        mill = Mill(
            id=mill_id,
            name="Minimal Test Mill",
            location="coordinates -17.8, 31.0",
            meter_type="Inhemeter",
            efficiency_baseline=1000.0,
        )
        session.add(mill)
        session.commit()
        print(f"  Created mill {mill_id}")
    else:
        print(f"  Mill already exists")

# Step 2: Get trust score
print("[2] Getting trust score...")
trust_gen = TrustScorecardGenerator(mill_id)
today = datetime.now(timezone.utc)
scorecard = trust_gen.generate_daily_scorecard(today)
trust_score = scorecard["kpis"]["trust_integrity_score"]
print(f"  Trust score: {trust_score}")

# Step 3: Call evaluate_mill_capital
print("[3] Calling evaluate_mill_capital...")
with Session(engine) as session:
    try:
        rate = evaluate_mill_capital(mill_id, trust_score, session)
        print(f"  Rate returned: {rate}")
        
        if rate > 0.0:
            print(f"✅ SUCCESS: Got positive rate ({rate*100:.1f}%)")
        else:
            print(f"❌ FAILURE: Got zero rate")
            print("   This means an exception was caught and logged.")
    except Exception as e:
        print(f"  EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
