"""
Test that logs to a file to bypass terminal instability
"""
import sys
import logging
from datetime import datetime, timezone
from sqlmodel import Session, select
from scripts.init_db import engine, Mill
from backend.cycle_manager import evaluate_mill_capital
from backend.trust_scorecard import TrustScorecardGenerator
from backend.revenue_engine import get_last_cycle_adherence, get_last_cycle_lag

# Configure logging to file
log_file = "test_output.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info("=" * 80)
logger.info("TEST: evaluate_mill_capital with file logging")
logger.info("=" * 80)

mill_id = "test_mill_file_log"

# Step 1: Create mill
logger.info(f"[STEP 1] Creating mill {mill_id}")
with Session(engine) as session:
    stmt = select(Mill).where(Mill.id == mill_id)
    mill = session.exec(stmt).first()
    if not mill:
        mill = Mill(
            id=mill_id,
            name="File Log Test Mill",
            location="coordinates -17.8, 31.0",
            meter_type="Inhemeter",
            efficiency_baseline=1000.0,
        )
        session.add(mill)
        session.commit()
        logger.info(f"  Created new mill")
    else:
        logger.info(f"  Mill already exists")

# Step 2: Get trust score
logger.info(f"[STEP 2] Computing trust score")
trust_gen = TrustScorecardGenerator(mill_id)
today = datetime.now(timezone.utc)
scorecard = trust_gen.generate_daily_scorecard(today)
trust_score = scorecard["kpis"]["trust_integrity_score"]
logger.info(f"  Trust score: {trust_score}")

# Step 3: Test helper functions first
logger.info(f"[STEP 3] Testing helper functions in isolation")
with Session(engine) as session:
    try:
        adherence = get_last_cycle_adherence(mill_id, session)
        logger.info(f"  adherence = {adherence}")
    except Exception as e:
        logger.error(f"  get_last_cycle_adherence FAILED: {e}", exc_info=True)
    
    try:
        lag = get_last_cycle_lag(mill_id, session)
        logger.info(f"  lag = {lag} hours")
    except Exception as e:
        logger.error(f"  get_last_cycle_lag FAILED: {e}", exc_info=True)

# Step 4: Call evaluate_mill_capital
logger.info(f"[STEP 4] Calling evaluate_mill_capital({mill_id}, {trust_score}, session)")
with Session(engine) as session:
    try:
        rate = evaluate_mill_capital(mill_id, trust_score, session)
        logger.info(f"  Result: rate = {rate} ({rate*100:.1f}%)")
        
        if rate > 0.0:
            logger.info(f"✅ TEST PASSED: Got positive advance rate")
        else:
            logger.warning(f"❌ TEST FAILED: Got zero advance rate (likely exception caught)")
    except Exception as e:
        logger.error(f"Exception raised: {type(e).__name__}: {e}", exc_info=True)

logger.info("=" * 80)
logger.info(f"Log file saved to: {log_file}")
logger.info("=" * 80)

# Print confirmation
print(f"\n✓ Wrote output to {log_file}\n")
