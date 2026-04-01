import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from sqlmodel import Session
from scripts.init_db import engine, Mill, DailyReport
from backend.parse_operator import parse_sms_to_report

def ingest_daily_sms(raw_text: str):
    # 1. Parse the incoming SMS
    data = parse_sms_to_report(raw_text)
    if "error" in data:
        return data

    with Session(engine) as session:
        # 2. Fetch Mill using Meter ID (37-prefix)
        mill = session.get(Mill, data["mill_id"])
        
        if not mill:
            return {"error": f"Meter {data['mill_id']} not found in GridLedger."}

        # 3. Truth Meter Logic
        expected_revenue = data["usage_kwh"] * mill.efficiency_baseline
        variance = data["actual_cash"] - expected_revenue
        
        # 4. Save to DailyReport Table
        new_report = DailyReport(
            mill_id=data["mill_id"],
            opening_kwh=data["opening_kwh"],
            closing_kwh=data["closing_kwh"],
            actual_cash=data["actual_cash"]
        )
        session.add(new_report)
        session.commit()

        return {
            "operator": mill.name,
            "location": mill.location,
            "usage": f"{data['usage_kwh']} kWh",
            "variance": f"MK {variance:,.2f}",
            "status": "RED: AUDIT REQ (Code 003)" if variance < -5000 else "GREEN: VERIFIED"
        }

if __name__ == "__main__":
    # Test with Jeremiah's Meter ID
    test_sms = "37154463253 100 110 13500" # Usage: 10kWh * 1350 baseline = 13500 (Perfect Match)
    print(ingest_daily_sms(test_sms))