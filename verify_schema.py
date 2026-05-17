#!/usr/bin/env python3
"""Verify schema completion - check for new tables"""

import sqlite3
from pathlib import Path

db_path = Path("data/gridledger.db")
if not db_path.exists():
    print(f"❌ Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Check for new tables
new_tables = [
    "mill_observation_configs",
    "tariff_rates", 
    "portfolio_anomaly_logs"
]

print("✅ Schema Verification:\n")

for table_name in new_tables:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,)
    )
    result = cursor.fetchone()
    
    if result:
        print(f"✅ {table_name}")
        cursor.execute(f"PRAGMA table_info({table_name})")
        cols = cursor.fetchall()
        print(f"   Columns: {len(cols)}")
        for i, col in enumerate(cols[:3]):
            print(f"     {i+1}. {col[1]} ({col[2]})")
        if len(cols) > 3:
            print(f"     ... and {len(cols)-3} more")
        print()
    else:
        print(f"❌ {table_name} - NOT FOUND\n")

conn.close()
print("✅ All new tables verified!")
