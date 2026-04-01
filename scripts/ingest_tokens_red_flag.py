import json
from datetime import datetime, timedelta

import pandas as pd
from sqlmodel import Session, select

from scripts.init_db import engine, DailyReport, Mill, TokenPurchase

CSV_PATH = 'mkwinda_tokens_full.csv'
MILL_ID = '37154345799'
STANDARD_UNITS_MIN = 45.0
STANDARD_AMOUNT_MIN = 20000
GAP_HOURS = 72
OUTPUT_JSON = 'red_flag_summary.json'
OUTPUT_AUDIT = 'audit_log.txt'


def check_cash_consistency(purchase_dt: datetime) -> bool:
    # Check cash behaviour during 24h window around purchase
    start = purchase_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    with Session(engine) as session:
        reports = session.exec(
            select(DailyReport).where(DailyReport.mill_id == MILL_ID)
            .where(DailyReport.timestamp >= start)
            .where(DailyReport.timestamp < end)
        ).all()

    total_reported_cash = sum(r.cash_reported for r in reports)
    return total_reported_cash >= 20000


def ingest_tokens():
    df = pd.read_csv(CSV_PATH, parse_dates=['Time'])

    # Ensure needed columns present
    if 'is_red_flag' not in df.columns:
        df['is_red_flag'] = False

    df['sub_standard_purchase'] = (df['Units'] < STANDARD_UNITS_MIN) | (df['Amount'] < STANDARD_AMOUNT_MIN)
    df['Time_Since_Last_Purchase_hours'] = df['Time'].diff().dt.total_seconds().div(3600).fillna(0)
    df['operational_gap'] = df['Time_Since_Last_Purchase_hours'] > GAP_HOURS

    df['cash_skimming_risk'] = False
    for idx, row in df.iterrows():
        if row['Units'] < STANDARD_UNITS_MIN:
            # check cross reference with production revenue
            valid_cash = check_cash_consistency(row['Time'])
            if valid_cash:
                df.at[idx, 'cash_skimming_risk'] = True

    # force highlight Jan 12 and Jan 23
    flags = []
    for target in ['2026-01-12', '2026-01-23']:
        mask = df['Time'].dt.strftime('%Y-%m-%d') == target
        for _, r in df[mask].iterrows():
            if r['sub_standard_purchase'] or r['operational_gap'] or r['cash_skimming_risk']:
                flags.append(r.to_dict())

    # build report
    red_flags = []
    for _, row in df.iterrows():
        flag_types = []
        if row['sub_standard_purchase']:
            flag_types.append('SUB_STANDARD_PURCHASE')
        if row['operational_gap']:
            flag_types.append('OPERATIONAL_GAP')
        if row['cash_skimming_risk']:
            flag_types.append('CASH_SKIMMING_RISK')

        if flag_types:
            red_flags.append({
                'Time': row['Time'].isoformat(),
                'Token': row['Token'],
                'Units': float(row['Units']),
                'Amount': float(row['Amount']),
                'flags': flag_types,
                'time_since_last_hours': float(row['Time_Since_Last_Purchase_hours']),
                'is_red_flag': bool(row.get('is_red_flag', False)),
            })

    # save JSON summary
    summary = {
        'mill_id': MILL_ID,
        'total_records': int(len(df)),
        'red_flag_count': int(len(red_flags)),
        'red_flags': red_flags,
        'special_targets': flags,
    }
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, default=str)

    # audit log ranked
    rank = pd.DataFrame(red_flags)
    if not rank.empty:
        # group by token owner is unavailable; we can only rank by count of red tokens
        rank_summary = rank.groupby('Token')['flags'].count().sort_values(ascending=False)
    else:
        rank_summary = pd.Series(dtype=int)

    with open(OUTPUT_AUDIT, 'w', encoding='utf-8') as f:
        f.write('Red Flag Audit Log\n')
        f.write('==================\n')
        if rank_summary.empty:
            f.write('No red flags found.\n')
        else:
            for token, c in rank_summary.items():
                f.write(f'Token {token}: {c} red flags\n')

    print(f'Summary written to {OUTPUT_JSON}')
    print(f'Audit log written to {OUTPUT_AUDIT}')


if __name__ == '__main__':
    ingest_tokens()
