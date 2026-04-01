#!/usr/bin/env python3
"""Debug trust score calculation."""

from scripts.init_db import engine, Mill
from sqlmodel import Session, select
from backend.trust_scorecard import TrustScorecardGenerator
from datetime import datetime, timezone

mill_id = 'debug_test_mill'
with Session(engine) as session:
    # Check if mill exists
    mill = session.exec(select(Mill).where(Mill.id == mill_id)).first()
    if not mill:
        mill = Mill(
            id=mill_id,
            name='Debug Test Mill',
            location='test',
            meter_type='test',
            efficiency_baseline=1000.0
        )
        session.add(mill)
        session.commit()
        print('Mill created')
    
    # Get trust score
    gen = TrustScorecardGenerator(mill_id)
    scorecard = gen.generate_daily_scorecard(datetime.now(timezone.utc))
    trust_score = scorecard['kpis']['trust_integrity_score']
    print(f'Trust score for new mill: {trust_score}')
    print(f'Full scorecard: {scorecard}')
