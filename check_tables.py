#!/usr/bin/env python3
"""Check all tables in database"""

import sqlite3

conn = sqlite3.connect('data/gridledger.db')
c = conn.cursor()

c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [row[0] for row in c.fetchall()]

print(f"Total tables: {len(tables)}\n")
for table in tables:
    print(f"  - {table}")

# Check for institutional tables specifically
institutional_tables = ['mandate_submissions', 'friction_analytics', 'discrepancy_reports', 'enforcement_actions']
print("\nGL-1 Institutional Tables:")
for table in institutional_tables:
    if table in tables:
        print(f"  [✓] {table}")
    else:
        print(f"  [✗] {table} MISSING")

conn.close()
