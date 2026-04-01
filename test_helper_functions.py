"""
Direct inspection: What do adherence and lag functions return?
"""
from datetime import datetime, timezone
from sqlmodel import Session
from scripts.init_db import engine, Mill, select
from backend.revenue_engine import get_last_cycle_adherence, get_last_cycle_lag

mill_id = "test_mill_e2e_minimal"

# Create mill if missing
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

# Test the helper functions
print(f"Testing helper functions for mill_id={mill_id}")
print()

with Session(engine) as session:
    print("[1] get_last_cycle_adherence()...")
    try:
        adherence = get_last_cycle_adherence(mill_id, session)
        print(f"    ✓ Result: {adherence}")
    except Exception as e:
        print(f"    ✗ Exception: {type(e).__name__}: {e}")

    print()
    print("[2] get_last_cycle_lag()...")
    try:
        lag = get_last_cycle_lag(mill_id, session)
        print(f"    ✓ Result: {lag}")
    except Exception as e:
        print(f"    ✗ Exception: {type(e).__name__}: {e}")
