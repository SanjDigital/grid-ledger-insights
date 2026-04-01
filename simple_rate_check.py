import sys
from sqlmodel import Session
from scripts.init_db import engine

print("Testing evaluate_mill_capital...")

try:
    from backend.cycle_manager import evaluate_mill_capital
    
    with Session(engine) as session:
        rate = evaluate_mill_capital("NABIWI", trust_score=85.0, session=session)
        print(f"Rate for NABIWI: {rate}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
