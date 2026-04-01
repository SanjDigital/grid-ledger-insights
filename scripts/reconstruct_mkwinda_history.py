import csv
import re
from datetime import datetime, timezone

from sqlmodel import Session, select
from scripts.init_db import engine, Mill, TokenPurchase, DailyReport, Cycle

METER_ID = "37154345799"
RATE_PER_KWH = 1300
SMS_SOURCE_NUMBER = "+265999684121"
CSV_PATH = "SMS_exported_from_HiSuite.csv"

TOKEN_PURCHASES = [
    {"date": "2025-12-12 05:18:13", "units": 55.8, "amount": 20000, "rcpt": "592152025121276085716"},
    {"date": "2025-12-13 14:19:57", "units": 55.8, "amount": 20000, "rcpt": "592152025121376150935"},
    {"date": "2025-12-14 10:40:18", "units": 55.8, "amount": 20000, "rcpt": "592152025121476186687"},
    {"date": "2026-01-06 11:10:26", "units": 55.4, "amount": 20000, "rcpt": "592152026010677467951"},
    {"date": "2026-01-10 04:01:32", "units": 55.4, "amount": 20000, "rcpt": "592152026011077601550"},
    {"date": "2026-02-04 10:00:00", "units": 59.9, "amount": 20000, "rcpt": "FEB_TOKEN_01"},
    {"date": "2026-03-13 12:48:30", "units": 59.9, "amount": 20000, "rcpt": "592152026031381201737"},
]

SMS_RE_PATTERN = re.compile(r"openi?\.\s?(\d+),\s*kolozi?\.\s?(\d+),\s*unitsi?\.\s?(\d+\.?\d*),\s*kashi?\.\s?k?(\d+\.?\d*)", re.IGNORECASE)


def parse_report_from_sms(content: str):
    m = SMS_RE_PATTERN.search(content)
    if not m:
        return None
    opening_kwh = float(m.group(1))
    closing_kwh = float(m.group(2))
    units = float(m.group(3))
    cash_reported = float(m.group(4))
    return opening_kwh, closing_kwh, units, cash_reported


def load_sms_reports(csv_path=CSV_PATH):
    reports = []
    try:
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sender = row.get('Number') or row.get('number') or ''
                content = row.get('Content') or row.get('content') or ''
                ts_str = row.get('Time') or row.get('time') or ''
                if SMS_SOURCE_NUMBER not in sender:
                    continue
                parsed = parse_report_from_sms(content)
                if not parsed:
                    continue
                try:
                    timestamp = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
                except Exception:
                    try:
                        timestamp = datetime.fromisoformat(ts_str)
                    except Exception:
                        continue
                opening_kwh, closing_kwh, units, cash_reported = parsed
                reports.append({
                    'mill_id': METER_ID,
                    'timestamp': timestamp.replace(tzinfo=timezone.utc),
                    'opening_kwh': opening_kwh,
                    'closing_kwh': closing_kwh,
                    'cash_reported': cash_reported,
                })
    except FileNotFoundError:
        print(f"CSV file not found: {csv_path}. Skipping SMS backfill.")
    return sorted(reports, key=lambda x: x['timestamp'])


def ingest_token_purchases():
    with Session(engine) as session:
        for token in TOKEN_PURCHASES:
            ts = datetime.strptime(token['date'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
            existing = session.exec(select(TokenPurchase).where(TokenPurchase.token_id == token['rcpt'])).one_or_none()
            if existing:
                continue
            new_token = TokenPurchase(
                token_id=token['rcpt'],
                mill_id=METER_ID,
                purchase_date=ts,
                units_kwh=token['units'],
                cost_mwk=token['amount'],
            )
            session.add(new_token)
        session.commit()


def reconcile_cycles():
    with Session(engine) as session:
        tokens = session.exec(
            select(TokenPurchase)
            .where(TokenPurchase.mill_id == METER_ID)
            .order_by(TokenPurchase.purchase_date.asc())
        ).all()

        cycle_entries = []

        for idx, token in enumerate(tokens):
            start = token.purchase_date
            end = tokens[idx + 1].purchase_date if idx + 1 < len(tokens) else datetime.now(timezone.utc)

            reports = session.exec(
                select(DailyReport)
                .where(DailyReport.mill_id == METER_ID)
                .where(DailyReport.timestamp >= start)
                .where(DailyReport.timestamp < end)
            ).all()

            energy_consumed = sum((r.closing_kwh - r.opening_kwh) for r in reports)
            actual_cash = sum(r.cash_reported for r in reports)
            expected_cash = energy_consumed * RATE_PER_KWH
            variance = expected_cash - actual_cash

            cycle = Cycle(
                mill_id=METER_ID,
                start_token_id=token.token_id,
                end_report_id=reports[-1].id if reports else None,
                energy_consumed=energy_consumed,
                expected_cash=expected_cash,
                actual_cash=actual_cash,
                variance=variance,
            )
            session.add(cycle)
            cycle_entries.append(cycle)

        session.commit()

    return cycle_entries


if __name__ == '__main__':
    print("👉 Loading SMS reports and ingetting into DailyReport...")
    sms_reports = load_sms_reports()

    with Session(engine) as session:
        for rep in sms_reports:
            existing = session.exec(
                select(DailyReport)
                .where(DailyReport.mill_id == METER_ID)
                .where(DailyReport.timestamp == rep['timestamp'])
            ).one_or_none()
            if existing:
                continue
            dr = DailyReport(
                mill_id=METER_ID,
                timestamp=rep['timestamp'],
                opening_kwh=rep['opening_kwh'],
                closing_kwh=rep['closing_kwh'],
                cash_reported=rep['cash_reported'],
            )
            session.add(dr)
        session.commit()

    print("👉 Ingesting token purchases...")
    ingest_token_purchases()

    print("👉 Reconciling cycles...")
    cycles = reconcile_cycles()
    for c in cycles:
        print(f"Cycle {c.start_token_id} -> variance {c.variance:.2f} (status: {'RECONCILED' if abs(c.variance) <= 5000 else 'PENDING'})")

    print("Done.")
