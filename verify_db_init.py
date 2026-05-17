#!/usr/bin/env python
"""Verify database initialization and institutional tables creation."""

from sqlmodel import Session, select, text
from scripts.init_db import engine
from backend.institutional_models import (
    MandateSubmission,
    FrictionAnalytics,
    DiscrepancyReport,
    EnforcementAction,
)

def verify_database():
    """Check database status and table creation."""
    with Session(engine) as session:
        # Query all tables
        result = session.exec(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")).all()
        
        # Extract table names - result is a list of Row objects, convert to strings
        table_names = []
        for r in result:
            if isinstance(r, tuple):
                table_names.append(r[0])
            elif hasattr(r, '__getitem__'):
                table_names.append(r[0])
            else:
                table_names.append(str(r))
        
        print("[OK] Database initialized successfully")
        print(f"[OK] Total tables: {len(table_names)}")
        print("\nTables in database:")
        for table in sorted(table_names):
            print(f"  - {table}")
        
        # Check for institutional tables
        institutional_tables = [
            'mandate_submissions',
            'friction_analytics',
            'discrepancy_reports',
            'enforcement_actions'
        ]
        
        found_tables = [t for t in institutional_tables if t in table_names]
        print(f"\n[OK] Institutional tables created: {len(found_tables)}/{len(institutional_tables)}")
        
        for table in institutional_tables:
            status = "[OK]" if table in table_names else "[FAIL]"
            print(f"  {status} {table}")
        
        return len(found_tables) == len(institutional_tables)

if __name__ == "__main__":
    success = verify_database()
    exit(0 if success else 1)
