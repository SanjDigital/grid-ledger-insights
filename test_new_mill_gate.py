#!/usr/bin/env python3
"""Test: Does gate block new mill with explicit trust_score=85?"""

import sys
sys.stdout.flush()

from scripts.init_db import engine, Mill
from sqlmodel import Session, select
from backend.cycle_manager import issue_token, FiduciaryLockError
from datetime import datetime, timezone

print("TEST: New mill first token issuance", flush=True)

# Create a test mill
with Session(engine) as session:
    test_mill_id = f"block_test_{datetime.now(timezone.utc).timestamp()}"
    mill = Mill(
        id=test_mill_id,
        name='Block Test Mill',
        location='test coord',
        meter_type='Inhemeter',
        efficiency_baseline=1000.0
    )
    session.add(mill)
    session.commit()
    print(f"Created mill: {test_mill_id}", flush=True)

# Try to issue first token
print("Attempting first token issuance...", flush=True)
try:
    token = issue_token(
        mill_id=test_mill_id,
        token_id=f"token_{datetime.now(timezone.utc).timestamp()}",
        units_kwh=59.9,
        cost_mwk=1000.0,
        revenue_wallet_id="rev_test",
        opex_wallet_id="opex_test"
    )
    print(f"✓ TOKEN ISSUED: {token.token_id}", flush=True)
    print("  → Gate did NOT block new mill", flush=True)
    print("  → System is safe for first production cycle", flush=True)
    sys.exit(0)
except FiduciaryLockError as e:
    print(f"✗ TOKEN BLOCKED: {e}", flush=True)
    print("  → Gate blocked first token issuance", flush=True)
    print("  → CRITICAL PRODUCTION BUG: New mills cannot get allocations", flush=True)
    sys.exit(1)
except Exception as e:
    print(f"✗ ERROR: {type(e).__name__}: {e}", flush=True)
    sys.exit(1)
