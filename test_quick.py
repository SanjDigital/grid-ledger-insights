"""
Test that evaluate_mill_capital works after syntax fix
"""
from datetime import datetime, timezone
from sqlmodel import Session, select
from scripts.init_db import engine, Mill
from backend.cycle_manager import evaluate_mill_capital
from backend.trust_scorecard import TrustScorecardGenerator

with open("evaluate_mill_test.log", "w", encoding='utf-8') as log:
    try:
        mill_id = "test_mill_syntax_fix"
        
        log.write(f"[TEST] Checking evaluate_mill_capital after syntax fix\n")
        log.write(f"Mill ID: {mill_id}\n")
        
        # Create mill
        with Session(engine) as session:
            stmt = select(Mill).where(Mill.id == mill_id)
            mill = session.exec(stmt).first()
            if not mill:
                mill = Mill(
                    id=mill_id,
                    name="Syntax Fix Test Mill",
                    location="coordinates -17.8, 31.0",
                    meter_type="Inhemeter",
                    efficiency_baseline=1000.0,
                )
                session.add(mill)
                session.commit()
                log.write("Created new mill\n")
            else:
                log.write("Mill already exists\n")
        
        # Get trust score
        trust_gen = TrustScorecardGenerator(mill_id)
        today = datetime.now(timezone.utc)
        scorecard = trust_gen.generate_daily_scorecard(today)
        trust_score = scorecard["kpis"]["trust_integrity_score"]
        log.write(f"Trust score: {trust_score}\n")
        
        # Call evaluate_mill_capital
        with Session(engine) as session:
            rate = evaluate_mill_capital(mill_id, trust_score, session)
            log.write(f"Advance rate: {rate:.4f} ({rate*100:.1f}%)\n")
            
            if rate > 0.0:
                log.write("RESULT: SUCCESS - Got positive advance rate\n")
                print("SUCCESS")
            else:
                log.write("RESULT: FAILED - Got zero advance rate\n")
                print("FAILED")
    except Exception as e:
        log.write(f"EXCEPTION: {type(e).__name__}: {e}\n")
        import traceback
        log.write(traceback.format_exc())
        print(f"ERROR: {e}")

penalty = mon.record_variance("2025-01-01", -10)
print(f"Day 1: penalty={penalty}")

penalty = mon.record_variance("2025-01-02", -5)
print(f"Day 2: penalty={penalty}")

penalty = mon.record_variance("2025-01-03", -2)
print(f"Day 3: penalty={penalty}")

print(f"Structural leakage: {mon.is_structural_leakage()}")

penalty = mon.record_variance("2025-01-04", +1)
print(f"Day 4 (positive): penalty={penalty}")

print("Quick test complete!")
