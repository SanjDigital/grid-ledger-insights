#!/usr/bin/env python3
"""
SMS Data Ingestion Script
Parses HiSuite SMS export and populates cycle table with operational data
Handles schema constraints by creating/linking required entities (mills, wallets)
"""

import csv
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

SMS_FILE = 'data/SMS exported from HiSuite2026-03-14_084735150.csv'
DB_PATH = 'data/gridledger.db'

def parse_sms_date(date_str):
    """Parse date from SMS format DD.M.YY to datetime"""
    try:
        parts = date_str.split('.')
        day = int(parts[0])
        month = int(parts[1])
        year = 2000 + int(parts[2])
        return datetime(year, month, day)
    except:
        return None

def extract_sms_metrics(content):
    """Parse SMS message for operational metrics"""
    
    # Make case-insensitive
    content_lower = content.lower()
    
    # Skip messages that don't match operational pattern
    if 'pa ' not in content_lower or 'open ' not in content_lower:
        return None
    
    result = {}
    
    # Extract date (DD.M.YY pattern)
    date_match = re.search(r'pa\s+(\d{1,2}\.\d{1,2}\.\d{2})', content_lower)
    if date_match:
        date_str = date_match.group(1)
        result['date'] = parse_sms_date(date_str)
        if not result['date']:
            return None
    else:
        return None
    
    # Extract meter open
    open_match = re.search(r'open\s+(\d+)', content_lower)
    if open_match:
        result['meter_open'] = int(open_match.group(1))
    
    # Extract meter close
    close_match = re.search(r'close\s+(\d+)', content_lower)
    if close_match:
        result['meter_close'] = int(close_match.group(1))
    
    # Extract units ground (ndagayil)
    units_match = re.search(r'ndagayil\s+(\d+)', content_lower)
    if units_match:
        result['units'] = int(units_match.group(1))
    else:
        # Try alternative: "ndagayila"
        units_match = re.search(r'ndagayila\s+(\d+)', content_lower)
        if units_match:
            result['units'] = int(units_match.group(1))
    
    # Extract amount (remove comma: 81,000 -> 81000)
    amount_match = re.search(r'amount\s+([\d,]+)', content_lower)
    if amount_match:
        amount_str = amount_match.group(1).replace(',', '')
        result['amount'] = int(amount_str)
    
    # Extract late fee (optional)
    late_match = re.search(r'late\s+(\d+)', content_lower)
    if late_match:
        result['late_fee'] = int(late_match.group(1))
    else:
        result['late_fee'] = 0
    
    return result if 'date' in result and 'units' in result and 'amount' in result else None

def derive_mill_id(phone_number):
    """Map phone number to mill identifier"""
    # Phone format: +265998265527
    # Extract last 8 digits: 98265527
    # Use as identifier or map to known mill names
    
    phone_mapping = {
        '+265998265527': 'NABIWI',  # Based on SMS export origin
        '0998265527': 'NABIWI',
        '998265527': 'NABIWI',
    }
    
    mill_id = phone_mapping.get(phone_number)
    if mill_id:
        return mill_id
    
    # Fallback: use phone number hash
    return f"MILL_{phone_number[-6:]}"

def ensure_mill_exists(cursor, mill_id):
    """Ensure mill exists in database; create if needed"""
    cursor.execute("SELECT id FROM mill WHERE id = ?", (mill_id,))
    if cursor.fetchone():
        return True  # Mill exists
    
    # Create mill if not exists
    cursor.execute("""
        INSERT INTO mill (
            id, name, location, meter_type, 
            efficiency_baseline, glass_box_certified
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        mill_id,
        f"{mill_id} Mill",
        f"Location for {mill_id}",
        "STANDARD",
        0.85,  # Default efficiency
        False
    ))
    return True

def ensure_wallets_exist(cursor, mill_id):
    """Ensure revenue and opex wallets exist; create if needed"""
    revenue_wallet_id = f"REV_{mill_id}"
    opex_wallet_id = f"OPX_{mill_id}"
    
    # Check/create revenue wallet
    cursor.execute("SELECT id FROM wallet WHERE id = ?", (revenue_wallet_id,))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO wallet (id, name, description, wallet_type)
            VALUES (?, ?, ?, ?)
        """, (revenue_wallet_id, f"Revenue Wallet for {mill_id}", 
              f"Receives revenue from {mill_id} operations", "REVENUE"))
    
    # Check/create opex wallet
    cursor.execute("SELECT id FROM wallet WHERE id = ?", (opex_wallet_id,))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO wallet (id, name, description, wallet_type)
            VALUES (?, ?, ?, ?)
        """, (opex_wallet_id, f"Opex Wallet for {mill_id}", 
              f"Receives opex from {mill_id} operations", "OPEX"))
    
    return revenue_wallet_id, opex_wallet_id

def ingest_sms_data(db_path, sms_file):
    """
    Parse SMS export and populate cycle table with required fields
    Creates mills and wallets as needed
    """
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("SMS DATA INGESTION")
    print("=" * 80)
    print()
    
    if not Path(sms_file).exists():
        print(f"ERROR: SMS file not found: {sms_file}")
        return None
    
    print(f"Reading SMS export: {sms_file}")
    
    cycles_parsed = 0
    cycles_ingested = 0
    errors = 0
    
    # Read CSV
    with open(sms_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            source = row.get('Source', '').strip()
            number = row.get('Number', '').strip()
            content = row.get('Content', '').strip()
            
            # Skip non-operational messages
            if source != 'From' or not content:
                continue
            
            # Try to parse metrics
            metrics = extract_sms_metrics(content)
            if not metrics:
                continue
            
            cycles_parsed += 1
            
            try:
                # Derive mill ID from phone number
                mill_id = derive_mill_id(number)
                
                # Ensure mill and wallets exist
                ensure_mill_exists(cursor, mill_id)
                revenue_wallet_id, opex_wallet_id = ensure_wallets_exist(cursor, mill_id)
                
                # Map to cycle schema
                cycle_start = metrics['date']
                cycle_end = cycle_start + timedelta(days=1)
                total_usage_kwh = metrics['units']
                total_actual_cash = metrics['amount']
                expected_revenue = metrics['amount'] + metrics['late_fee']
                variance = expected_revenue - total_actual_cash
                status = 'SEALED'
                
                # Insert cycle record with all required fields
                cursor.execute("""
                    INSERT INTO cycle (
                        mill_id, revenue_wallet_id, opex_wallet_id,
                        cycle_start, cycle_end,
                        total_usage_kwh, total_actual_cash, expected_revenue,
                        variance, status, audit_summary,
                        gap_breach_detected, reconciled_at,
                        anchor_status, anchor_retries
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    mill_id, revenue_wallet_id, opex_wallet_id,
                    cycle_start, cycle_end,
                    total_usage_kwh, total_actual_cash, expected_revenue,
                    variance, status, 'SMS INGESTION',
                    0, datetime.now(),
                    'PENDING', 0
                ))
                
                cycles_ingested += 1
                
            except Exception as e:
                errors += 1
    
    conn.commit()
    conn.close()
    
    print()
    print("-" * 80)
    print("INGESTION SUMMARY")
    print("-" * 80)
    print(f"Messages parsed: {cycles_parsed}")
    print(f"Cycles ingested: {cycles_ingested}")
    print(f"Errors: {errors}")
    print()
    
    return cycles_ingested

def verify_ingestion(db_path):
    """Verify cycle data was ingested successfully"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("VERIFICATION")
    print("-" * 80)
    
    # Count cycles by mill
    cursor.execute("""
        SELECT mill_id, COUNT(*) as cycle_count
        FROM cycle
        GROUP BY mill_id
        ORDER BY cycle_count DESC
    """)
    
    results = cursor.fetchall()
    if not results:
        print("No cycles found in database")
    else:
        print("Cycles by mill:")
        for mill_id, count in results:
            print(f"  {mill_id}: {count} cycles")
    
    print()
    
    # Date range
    cursor.execute("""
        SELECT 
            MIN(cycle_start) as earliest,
            MAX(cycle_start) as latest,
            COUNT(*) as total
        FROM cycle
    """)
    
    earliest, latest, total = cursor.fetchone()
    if earliest:
        print(f"Date range: {earliest} to {latest}")
        print(f"Total cycles: {total}")
    
    print()
    
    # Metrics summary
    cursor.execute("""
        SELECT
            ROUND(AVG(total_usage_kwh), 2) as avg_kwh,
            ROUND(AVG(total_actual_cash), 2) as avg_cash,
            ROUND(AVG(expected_revenue), 2) as avg_revenue
        FROM cycle
    """)
    
    avg_kwh, avg_cash, avg_revenue = cursor.fetchone()
    print(f"Average metrics:")
    print(f"  Usage: {avg_kwh} kWh/cycle")
    print(f"  Cash collected: {avg_cash} MK/cycle")
    print(f"  Expected revenue: {avg_revenue} MK/cycle")
    
    conn.close()

def main():
    print()
    
    # Ingest SMS data
    cycles = ingest_sms_data(DB_PATH, SMS_FILE)
    
    if cycles is None:
        print("Ingestion failed")
        return
    
    if cycles == 0:
        print("No cycles ingested. Check SMS file format.")
        return
    
    # Verify
    verify_ingestion(DB_PATH)
    
    print()
    print("=" * 80)
    print("SMS INGESTION COMPLETE")
    print("=" * 80)
    print()
    print("Next step: Run Node Inventory Query")
    print("  python run_node_inventory_query.py")
    print()

if __name__ == '__main__':
    main()
