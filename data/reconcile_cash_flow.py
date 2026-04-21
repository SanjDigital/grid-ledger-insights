"""
GridLedger Cash‑Flow Reconciliation Script
Joins operator production reports with Airtel Money receipts from the same SMS export.
Output: CSV with matched/unmatched cycles, amounts, and timing.
"""

import re
import csv
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

# Configuration
INPUT_CSV = "../SMS_exported_from_HiSuite2026-03-14_084735150.csv"  # change to your file
OUTPUT_CSV = "reconciliation_output.csv"
PRODUCTION_SENDER = "+265998265527"  # operator's phone number
TIMEZONE_OFFSET = 0  # Malawi is UTC+2, but timestamps in CSV are local? Assume UTC for simplicity

# Regex patterns
PROD_PATTERN = re.compile(
    r"pa\s+(\d{1,2})\.(\d{1,2})\.(\d{2,4})"
    r".*?ndagayil\s+(\d+)"
    r".*?units amount\s+([\d,]+)",
    re.IGNORECASE
)
AIR_AMOUNT_PATTERN = re.compile(
    r"sent MK\s+([\d,]+(?:\.\d{2})?)"
)
AIR_TRANS_ID_PATTERN = re.compile(
    r"Trans ID\s*:\s*(\S+)"
)
AIR_NDATUMIZA_PATTERN = re.compile(r"Ndatumiza Ndalama", re.IGNORECASE)

def parse_production(content: str, timestamp: datetime) -> Optional[Dict]:
    """Extract production date, units, revenue from SMS content."""
    m = PROD_PATTERN.search(content)
    if not m:
        return None
    day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if year < 100:
        year += 2000
    try:
        prod_date = datetime(year, month, day)
    except ValueError:
        return None
    units = int(m.group(4))
    revenue_str = m.group(5).replace(',', '')
    revenue = float(revenue_str)
    return {
        "date": prod_date,
        "units": units,
        "revenue": revenue,
        "timestamp": timestamp,
        "raw": content
    }

def parse_airtel(content: str, timestamp: datetime) -> Dict:
    """Extract Airtel receipt info: amount (if any), trans_id (if any), and type."""
    amount = None
    trans_id = None
    # Try to find amount in "You have sent MK XXXX"
    amt_match = AIR_AMOUNT_PATTERN.search(content)
    if amt_match:
        amount = float(amt_match.group(1).replace(',', ''))
    # Try to find Trans ID
    tid_match = AIR_TRANS_ID_PATTERN.search(content)
    if tid_match:
        trans_id = tid_match.group(1)
    is_ndatumiza = bool(AIR_NDATUMIZA_PATTERN.search(content))
    return {
        "timestamp": timestamp,
        "amount": amount,
        "trans_id": trans_id,
        "is_ndatumiza": is_ndatumiza,
        "raw": content
    }

def load_data(csv_path: str):
    """Read CSV, return lists of production events and Airtel receipts."""
    productions = []
    airtel_receipts = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ts = datetime.strptime(row['Time'], '%Y/%m/%d %H:%M:%S')
            except:
                continue
            number = row.get('Number', '')
            content = row.get('Content', '')
            if number == PRODUCTION_SENDER and 'ndagayil' in content.lower():
                prod = parse_production(content, ts)
                if prod:
                    productions.append(prod)
            elif 'airtel' in content.lower() or 'trans id' in content.lower() or 'ndatumiza' in content.lower():
                # Broad filter for Airtel-related messages
                air = parse_airtel(content, ts)
                if air['amount'] or air['is_ndatumiza'] or air['trans_id']:
                    airtel_receipts.append(air)
    return productions, airtel_receipts

def match_productions(productions: List[Dict], receipts: List[Dict], max_hours=48):
    """
    Match each production to the nearest Airtel receipt within max_hours.
    Returns list of dicts with match info.
    """
    results = []
    receipts_sorted = sorted(receipts, key=lambda x: x['timestamp'])
    for prod in productions:
        best_receipt = None
        best_lag = None
        for rec in receipts_sorted:
            lag = (rec['timestamp'] - prod['timestamp']).total_seconds() / 3600.0
            if abs(lag) <= max_hours:
                # Prefer receipts after production (positive lag) but accept before
                if best_receipt is None or abs(lag) < abs(best_lag):
                    best_receipt = rec
                    best_lag = lag
        if best_receipt:
            results.append({
                "prod_date": prod['date'].strftime('%Y-%m-%d'),
                "prod_time": prod['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                "units": prod['units'],
                "reported_revenue": prod['revenue'],
                "airtel_time": best_receipt['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                "airtel_amount": best_receipt['amount'],
                "trans_id": best_receipt.get('trans_id', ''),
                "match_type": "amount" if best_receipt['amount'] else "ndatumiza",
                "lag_hours": round(best_lag, 2),
                "status": "MATCHED"
            })
        else:
            results.append({
                "prod_date": prod['date'].strftime('%Y-%m-%d'),
                "prod_time": prod['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                "units": prod['units'],
                "reported_revenue": prod['revenue'],
                "airtel_time": "",
                "airtel_amount": "",
                "trans_id": "",
                "match_type": "",
                "lag_hours": "",
                "status": "UNMATCHED"
            })
    return results

def main():
    print("Loading SMS data...")
    prods, receipts = load_data(INPUT_CSV)
    print(f"Found {len(prods)} production reports and {len(receipts)} Airtel receipts.")
    results = match_productions(prods, receipts, max_hours=48)
    # Write CSV
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ["prod_date", "prod_time", "units", "reported_revenue", "airtel_time", "airtel_amount", "trans_id", "match_type", "lag_hours", "status"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(f"Reconciliation complete. Output written to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()