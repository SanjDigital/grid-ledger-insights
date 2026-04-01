import sys
import os
from datetime import datetime, timezone, timedelta

# Ensure parent directory is on path for module imports from other folders
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlmodel import Session, select
from scripts.init_db import engine, Mill, DailyReport, Operator
from backend.parse_operator import parse_sms_to_report

def ingest_daily_sms(raw_text: str):
    # 1. Parse the incoming SMS
    data = parse_sms_to_report(raw_text)
    if "error" in data:
        return data

    mill_id = data.get("mill_id")
    if not mill_id:
        return {"error": "No mill_id found in parsed report."}

    with Session(engine) as session:
        # 2. Fetch Mill using Meter ID
        mill = session.get(Mill, mill_id)
        if not mill:
            return {"error": f"Meter {mill_id} not found in GridLedger."}

        # operator identity mapping
        operator = session.exec(select(Operator).where(Operator.mill_id == mill_id)).first()
        operator_id = operator.operator_id if operator else None

        # 3. Truth Meter Logic
        expected_revenue = data["usage_kwh"] * mill.efficiency_baseline
        variance = data["actual_cash"] - expected_revenue

        # 4. Save to DailyReport Table
        report = DailyReport(
            mill_id=mill_id,
            operator_id=operator_id,
            opening_kwh=data["opening_kwh"],
            closing_kwh=data["closing_kwh"],
            actual_cash=data["actual_cash"],
            report_date=datetime.now(timezone.utc)
        )
        session.add(report)
        session.commit()

        if variance < -5000:
            return f"AUDIT ALERT: High Variance. Meter {mill_id} check required. Command: Press 003 on keypad and reply with balance."

        return f"Report verified for {mill.name} at {mill.location}."


def bulk_ingest_historical(mill_id: str, total_kwh: float, actual_total_cash: float):
    """Create one DailyReport per day for February (28 days) as simulated historical data."""
    with Session(engine) as session:
        mill = session.get(Mill, mill_id)
        if not mill:
            return {"error": f"Meter {mill_id} not found in GridLedger."}

        days = 28
        base_kwh = total_kwh / days
        base_cash = actual_total_cash / days

        start_date = datetime(2026, 2, 1, tzinfo=timezone.utc)
        created_reports = []

        for i in range(days):
            opening = base_kwh * i
            closing = opening + base_kwh
            cash = base_cash
            report_date = start_date.replace(day=1) + timedelta(days=i)

            daily_report = DailyReport(
                mill_id=mill_id,
                opening_kwh=opening,
                closing_kwh=closing,
                actual_cash=cash,
                report_date=report_date
            )
            session.add(daily_report)
            created_reports.append(daily_report)

        session.commit()

        return {
            "status": "ok",
            "mill_id": mill_id,
            "records_created": len(created_reports)
        }


if __name__ == "__main__":
    # Demo: Ingest one SMS and one historical bulk ingestion
    print(ingest_daily_sms("37154463253 100 110 13500"))
    print(bulk_ingest_historical("37154463253", 2800, 378000))
