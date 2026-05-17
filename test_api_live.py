#!/usr/bin/env python3
"""Quick test of live institutional API endpoints"""

import requests
import json

BASE_URL = "http://localhost:8000"
API_KEY = "letmein123"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

print("=" * 60)
print("GRIDLEDGER INSTITUTIONAL API LIVE TEST")
print("=" * 60)

# Test 1: Audit Trail (empty initially)
print("\n[TEST 1] GET /api/institutional/audit-trail/full")
try:
    resp = requests.get(f"{BASE_URL}/api/institutional/audit-trail/full", headers=headers)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Response: {json.dumps(data, indent=2)[:500]}...")
        print("✓ PASS - Endpoint responding")
    else:
        print(f"✗ FAIL - {resp.text}")
except Exception as e:
    print(f"✗ ERROR: {e}")

# Test 2: Submit Mandate
print("\n[TEST 2] POST /api/institutional/mandate-submission")
try:
    payload = {
        "mandate_id": "GL1_TEST_001",
        "submitted_by": "operator_01",
        "role": "operator",
        "mandate_version_hash": "abc123def456",
        "acknowledgment_type": "FULL_READ",
        "session_id": "sess_001"
    }
    resp = requests.post(
        f"{BASE_URL}/api/institutional/mandate-submission",
        headers=headers,
        json=payload
    )
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        print("✓ PASS - Mandate submitted")
    else:
        print(f"✗ FAIL - {resp.text}")
except Exception as e:
    print(f"✗ ERROR: {e}")

# Test 3: Record Friction Analytics
print("\n[TEST 3] POST /api/institutional/friction-analytics")
try:
    payload = {
        "session_id": "sess_001",
        "mandate_id": "GL1_TEST_001",
        "scroll_depth_pct": 100,
        "time_on_statement_ms": 45000,
        "interaction_count": 7,
        "bypass_attempted": False
    }
    resp = requests.post(
        f"{BASE_URL}/api/institutional/friction-analytics",
        headers=headers,
        json=payload
    )
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        print("✓ PASS - Friction recorded")
    else:
        print(f"✗ FAIL - {resp.text}")
except Exception as e:
    print(f"✗ ERROR: {e}")

# Test 4: Verify Audit Trail Updated
print("\n[TEST 4] GET /api/institutional/audit-trail/full (after submissions)")
try:
    resp = requests.get(f"{BASE_URL}/api/institutional/audit-trail/full", headers=headers)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Total records: {len(data)}")
        if len(data) > 0:
            print(f"Latest record: {json.dumps(data[-1], indent=2, default=str)}")
            print("✓ PASS - Data persisted")
        else:
            print("⚠ WARNING - No records found")
    else:
        print(f"✗ FAIL - {resp.text}")
except Exception as e:
    print(f"✗ ERROR: {e}")

print("\n" + "=" * 60)
print("API TEST COMPLETE")
print("=" * 60)
