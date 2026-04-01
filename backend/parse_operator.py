"""
GridLedger SMS Parser
Current format: MILL_ID, OPENING_KWH, CLOSING_KWH, CASH
Example: "NABIWI,3410,3472,65000"
"""

import re
from datetime import datetime, timezone
from typing import Dict, Union, Optional

# Known mills (expand as needed)
KNOWN_MILLS = ["NABIWI", "MKWINDA", "CHANKHUTA", "AREA36", "SENTI"]

def parse_sms_to_report(raw_text: str) -> Dict[str, Union[str, float, int, None]]:
    """
    Parse operator SMS in format: MILL_ID,OPENING,CLOSING,CASH
    Spaces or commas as separators.
    """
    # Clean and normalize
    clean_text = raw_text.strip().upper()
    
    # Replace multiple spaces with single space, then split
    normalized = re.sub(r'\s+', ' ', clean_text)
    
    # Try comma separation first, then space
    if ',' in normalized:
        parts = [p.strip() for p in normalized.split(',')]
    else:
        parts = normalized.split(' ')
    
    # Filter out empty strings
    parts = [p for p in parts if p]
    
    if len(parts) < 4:
        return {"error": "Expected at least 4 fields: MILL OPEN CLOSE CASH", "raw": raw_text}
    
    # First part should be mill ID (37-prefix meter ID)
    mill_candidate = parts[0]
    if mill_candidate.startswith("37") and mill_candidate.isdigit() and len(mill_candidate) == 11:
        mill_id = mill_candidate
    else:
        # Fallback to known site names for legacy
        mill_id = None
        for known in KNOWN_MILLS:
            if known in mill_candidate:
                mill_id = known
                break
        if not mill_id:
            return {"error": f"Unknown mill ID or name. Expected 37-prefix ID or known site.", "raw": raw_text}
    
    # Extract numbers from remaining parts
    numbers = []
    for part in parts[1:4]:  # next 3 parts should be numbers
        # Remove any non-numeric characters except decimal
        cleaned = re.sub(r'[^\d.]', '', part)
        try:
            if '.' in cleaned:
                numbers.append(float(cleaned))
            else:
                numbers.append(int(cleaned))
        except ValueError:
            numbers.append(None)
    
    if len(numbers) < 3 or None in numbers:
        return {"error": "Could not parse numeric values", "raw": raw_text}
    
    opening, closing, cash = numbers[0], numbers[1], numbers[2]
    
    # Calculate usage
    usage = closing - opening
    
    # Validation rules (mill physics)
    if usage <= 0:
        return {"error": f"Usage {usage} <= 0 (closing must be > opening)", "raw": raw_text}
    
    if usage > 100:  # Typical max per day? Adjust based on your data
        return {"warning": f"High usage: {usage} kWh – verify", "raw": raw_text}
    
    if cash <= 0:
        return {"error": "Cash must be positive", "raw": raw_text}
    
    # Rough rate sanity check (adjust based on your mills)
    rate = cash / usage
    if rate < 500 or rate > 3000:
        return {"warning": f"Rate {rate:.0f} MWK/kWh unusual – verify", "raw": raw_text}
    
    return {
        "mill_id": mill_id,
        "opening_kwh": float(opening),
        "closing_kwh": float(closing),
        "usage_kwh": usage,
        "actual_cash": float(cash),
        "rate_mwk_per_kwh": rate,
        "raw_sms": raw_text,
        "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    }

# Test with your real data
if __name__ == "__main__":
    test_cases = [
        "NABIWI,3410,3472,65000",
        "MKWINDA 3450 3520 84000",      # space separated
        "CHANKHUTA,3580,3660,98000",
        "AREA36 3500 3510 15000",       # low cash – might flag warning
        "37154463253 100 110 13500",    # meter ID test
        "INVALID MILL 1 2 3"
    ]
    for msg in test_cases:
        print(f"\n📨 Input: {msg}")
        result = parse_sms_to_report(msg)
        for k, v in result.items():
            print(f"   {k}: {v}")