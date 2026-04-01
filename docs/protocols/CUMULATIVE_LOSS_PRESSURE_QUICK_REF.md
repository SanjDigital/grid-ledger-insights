# Cumulative Loss Pressure: Quick Reference

## The Rule (One Sentence)
If an operator's 30-day rolling average efficiency is below 75%, their base rate is permanently halved until they recover.

## Key Formula
```
cumulative_penalty(mill_id):
  IF rolling_efficiency(mill_id, 30_days) < 0.75:
    RETURN 0.5    # Base rate becomes 50% of normal
  ELSE:
    RETURN 1.0    # No penalty
```

## In Practice

### Operator With Good Rolling Average (No Penalty)
```
30-day rolling EAR: 85%
Current efficiency: 85%
Trust: 80%

advance_rate = 0.50 × (0.80 × 85²) = 28.9%  [NORMAL]
```

### Same Operator, Bad Rolling Average (Penalty Applied)
```
30-day rolling EAR: 62%  [prolonged underperformance]
Current efficiency: 85%  [recently improved]
Trust: 80%

advance_rate = 0.25 × (0.80 × 85²) = 14.5%  [HALVED - memory penalty]
```

## Recovery
- Operator must maintain ≥75% rolling average for 30 days
- Penalty lifts automatically when threshold crossed
- No manual intervention, fully mechanical

## Interaction with Hard Floor
- Hard floor (< 50% current) is checked FIRST → 0.0 (immediate block)
- Cumulative penalty (< 75% rolling) is checked SECOND → base_rate × 0.5
- If hard floor triggered, cumulative penalty is irrelevant

## Implementation Files
- Core: `backend/capital_controls.py` (methods)
- Integration: `backend/policy_execution_engine.py` (compute_advance_rate)
- Tests: `test_squeeze.py`, `test_cumulative_penalty_quick.py`
- Docs: `CUMULATIVE_LOSS_PRESSURE.md`

## Code Usage

### Without penalty (backward compatible)
```python
rate = compute_advance_rate(trust=80, efficiency=0.85)
```

### With penalty lookup
```python
rate = compute_advance_rate(trust=80, efficiency=0.85, mill_id="MILL_001")
```

### Check operator's rolling efficiency
```python
from backend.capital_controls import CapitalControls
rolling_eff = CapitalControls.get_rolling_efficiency("MILL_001")
penalty = CapitalControls.cumulative_penalty("MILL_001")
```

## Operator Messaging
- "Your capital access is based on your 30-day performance"
- "One good month doesn't erase a month of poor performance"
- "Sustained improvement above 75% lifts the penalty automatically"

## Test Validation
✅ Backward compatible (optional mill_id parameter)  
✅ Hard floor takes priority  
✅ All existing tests pass  
✅ Integration complete  

## Future If Needed
- Change threshold: adjust 0.75 → different value
- Change penalty: adjust 0.5 → different multiplier  
- Change window: adjust 30_days → different duration
