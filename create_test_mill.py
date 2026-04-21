#!/usr/bin/env python
"""Quick script to create test mill data for smoke tests."""

from pathlib import Path
from sqlmodel import create_engine, Session, select
from scripts.init_db import Mill

DATA_DIR = Path(__file__).resolve().parents[0] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

sqlite_url = f"sqlite:///{DATA_DIR / 'gridledger.db'}"
engine = create_engine(sqlite_url)

with Session(engine) as session:
    # Check if test mill already exists
    stmt = select(Mill).where(Mill.id == 'TEST_MILL_01')
    mill = session.exec(stmt).first()
    if not mill:
        mill = Mill(
            id='TEST_MILL_01',
            name='Test Mill',
            location='Test Location',
            meter_type='Inhemeter',
            efficiency_baseline=1000.0,
            revenue_rate_per_kwh=1350.0
        )
        session.add(mill)
        session.commit()
        print('✅ Test mill created: TEST_MILL_01')
    else:
        print('ℹ️  Test mill already exists: TEST_MILL_01')
