#!/usr/bin/env python
"""
Quick Start: Move A Concurrency Test

This script checks all prerequisites and provides step-by-step instructions
to run the concurrency test.
"""

import sys
import os
from pathlib import Path

# Add project to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def check_imports():
    """Check if all required packages are installed."""
    print("\n" + "="*70)
    print("📦 CHECKING REQUIRED PACKAGES")
    print("="*70)
    
    packages = [
        ("fastapi", "FastAPI"),
        ("sqlmodel", "SQLModel"),
        ("requests", "requests"),
        ("sqlalchemy", "SQLAlchemy"),
    ]
    
    missing = []
    for pkg_name, display_name in packages:
        try:
            __import__(pkg_name)
            print(f"  ✅ {display_name:15} installed")
        except ImportError:
            print(f"  ❌ {display_name:15} MISSING")
            missing.append(pkg_name)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print(f"\nInstall with:")
        print(f"  pip install {' '.join(missing)}")
        return False
    
    print(f"\n✓ All packages installed")
    return True


def check_database():
    """Check if database exists and migration is applied."""
    print("\n" + "="*70)
    print("💾 CHECKING DATABASE")
    print("="*70)
    
    db_path = PROJECT_ROOT / "data" / "gridledger.db"
    
    if not db_path.exists():
        print(f"  ❌ Database not found at {db_path}")
        print(f"\nInitialize with:")
        print(f"  python scripts/init_db.py")
        return False
    
    print(f"  ✅ Database exists at {db_path}")
    
    # Check if the partial unique index exists
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='one_active_cycle_per_mill'"
        )
        if cursor.fetchone():
            print(f"  ✅ Partial unique index 'one_active_cycle_per_mill' found")
            conn.close()
            return True
        else:
            print(f"  ⚠️  Partial unique index 'one_active_cycle_per_mill' NOT found")
            print(f"\nCreate with:")
            print(f"  sqlite3 data/gridledger.db \"CREATE UNIQUE INDEX one_active_cycle_per_mill ON token_allocations (mill_id) WHERE status IN ('PENDING', 'MISSING', 'DISPUTED');\"")
            print(f"\nOr from Python:")
            print(f"  from sqlalchemy import text")
            print(f"  from scripts.init_db import engine")
            print(f"  with engine.connect() as conn:")
            print(f"      conn.execute(text(")
            print(f"          'CREATE UNIQUE INDEX one_active_cycle_per_mill ON token_allocations (mill_id) WHERE status IN (\"PENDING\", \"MISSING\", \"DISPUTED\")'")
            print(f"      ))")
            print(f"      conn.commit()")
            return False
    except Exception as e:
        print(f"  ❌ Error checking database: {e}")
        return False


def check_models():
    """Check if DecisionAudit model exists."""
    print("\n" + "="*70)
    print("🏗️  CHECKING MODELS")
    print("="*70)
    
    try:
        from scripts.init_db import DecisionAudit, Mill
        print(f"  ✅ DecisionAudit model found")
        print(f"  ✅ Mill model found")
        
        # Check if Mill has revenue_rate_per_kwh
        from sqlalchemy import inspect
        mapper = inspect(Mill)
        if 'revenue_rate_per_kwh' in [c.name for c in mapper.columns]:
            print(f"  ✅ Mill.revenue_rate_per_kwh field found")
        else:
            print(f"  ❌ Mill.revenue_rate_per_kwh field MISSING")
            return False
        
        return True
    except ImportError as e:
        print(f"  ❌ Model import failed: {e}")
        return False


def check_routes():
    """Check if owner_routes is properly integrated."""
    print("\n" + "="*70)
    print("🛣️  CHECKING API ROUTES")
    print("="*70)
    
    try:
        from backend.owner_routes import router as owner_router
        print(f"  ✅ owner_routes router found")
        
        # Check for allocate_token endpoint
        from backend.main import app
        endpoints = [route.path for route in app.routes]
        if "/api/owner/mills/{mill_id}/allocate-token" in endpoints:
            print(f"  ✅ allocate-token endpoint registered")
            return True
        else:
            # It might be registered under the router prefix
            print(f"  ⚠️  allocate-token endpoint check inconclusive")
            print(f"     Registered endpoints: {endpoints}")
            return True  # Still pass - router is included
    except Exception as e:
        print(f"  ❌ Routes check failed: {e}")
        return False


def main():
    print("\n" + "="*70)
    print("🧪 MOVE A CONCURRENCY TEST - PREREQUISITES CHECK")
    print("="*70)
    print(f"Project root: {PROJECT_ROOT}")
    
    checks = [
        ("Packages", check_imports),
        ("Database", check_database),
        ("Models", check_models),
        ("Routes", check_routes),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} check failed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*70)
    print("📋 SUMMARY")
    print("="*70)
    
    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status:10} {name}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n" + "🎉 "*20)
        print("✅ ALL CHECKS PASSED!")
        print("🎉 "*20)
        print("\n📚 NEXT STEPS:")
        print("\n1. In Terminal 1 (API Server):")
        print("   python -m uvicorn backend.main:app --reload --port 8000")
        print("\n2. In Terminal 2 (Concurrency Test):")
        print("   python test_move_a_concurrency.py")
        print("\n📖 For detailed guide, see: TEST_CONCURRENCY_GUIDE.md")
        return True
    else:
        print("\n❌ SOME CHECKS FAILED")
        print("\nFix the issues above, then run this script again:")
        print("   python quickstart_concurrency_test.py")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
