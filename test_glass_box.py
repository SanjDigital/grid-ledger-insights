#!/usr/bin/env python
"""Test Glass Box Certification function."""

from scripts.init_db import engine
from sqlmodel import Session
from backend.revenue_engine import get_certification_status
import json

with Session(engine) as session:
    result = get_certification_status('NABIWI', session)
    print(json.dumps(result, indent=2, default=str))
