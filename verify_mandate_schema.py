#!/usr/bin/env python3
"""Verify mandate_submissions schema has all 6 GL-1 fields"""

import sqlite3

conn = sqlite3.connect('data/gridledger.db')
c = conn.cursor()

# Get table schema
c.execute("PRAGMA table_info(mandate_submissions)")
cols = c.fetchall()

print("=" * 60)
print("GL-1 MANDATE SUBMISSIONS SCHEMA VERIFICATION")
print("=" * 60)
print(f"\nTotal columns: {len(cols)}\n")

# Expected 6 GL-1 fields
required_fields = {
    'id': 'PRIMARY KEY',
    'mandate_id': 'UNIQUE IDENTIFIER',
    'timestamp': 'TIMESTAMP_UTC',
    'institution_name': 'INSTITUTION NAME',
    'authorisation_level': 'AUTHORITY LEVEL',
    'capital_range': 'CAPITAL TIER',
    'mode_viewed': 'HOW VIEWED'
}

print("Schema:")
for col in cols:
    col_name = col[1]
    col_type = col[2]
    print(f"  {col_name:30} {col_type}")

print("\nGL-1 Requirements (6 fields):")
found_fields = {}
for col in cols:
    col_name = col[1]
    if col_name in required_fields:
        found_fields[col_name] = True
        print(f"  [✓] {col_name}")

missing = set(required_fields.keys()) - set(found_fields.keys())
if missing:
    print(f"\n[✗] MISSING FIELDS: {missing}")
else:
    print(f"\n[✓] ALL 6 GL-1 FIELDS PRESENT")

# Test insert with new fields
print("\n" + "=" * 60)
print("TESTING INSERT WITH 6 FIELDS")
print("=" * 60)

try:
    c.execute("""
        INSERT INTO mandate_submissions 
        (mandate_id, submitted_by, role, timestamp, mandate_version_hash, 
         acknowledgment_type, session_id, status, institution_name, 
         authorisation_level, capital_range, mode_viewed)
        VALUES (?, ?, ?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'GL1_TEST_VERIFY_001',
        'test_operator',
        'operator',
        'v1.0.0',
        'FULL_READ',
        'sess_test_001',
        'ACKNOWLEDGED',
        'NBM',
        'MANAGER',
        'TIER_A',
        'INTERACTIVE'
    ))
    conn.commit()
    print("[✓] Insert successful with all 6 fields\n")
    
    # Retrieve and verify
    c.execute("SELECT institution_name, authorisation_level, capital_range, mode_viewed FROM mandate_submissions WHERE mandate_id = ?", ('GL1_TEST_VERIFY_001',))
    result = c.fetchone()
    if result:
        print(f"[✓] Retrieved: institution_name={result[0]}, authorisation_level={result[1]}, capital_range={result[2]}, mode_viewed={result[3]}")
    
except Exception as e:
    print(f"[✗] ERROR: {e}")

conn.close()

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)
