# Capital at Risk Handling System

**Status**: ✅ IMPLEMENTED & INTEGRATED  
**Version**: 1.0  
**Date**: 2024  
**Integration Point**: Enforcement Engine State Transitions

## Overview

Capital at Risk (CAR) Handling is the enforcement layer that implements capital control actions when a mill's financial integrity is compromised. When a mill transitions to COMPROMISED or SUSPENDED state, three capital control mechanisms activate:

1. **Cash Sweep** - Redirect incoming revenue toward outstanding balance reduction
2. **Credit Compression** - Set remaining credit to zero (suspend credit lines)
3. **Pricing Escalation** - Apply penalty rates to outstanding obligations

All actions are logged to the `CreditEvent` table for audit trail and regulatory compliance.

## Architecture

### Module Structure

```
backend/
  capital_at_risk.py          # Capital control logic and state triggers
  enforcement_engine.py       # Enhanced with CAR integration
  api_reports.py              # API functions for CAR queries
  main.py                     # FastAPI endpoints

scripts/
  init_db.py                  # CreditEvent table schema
```

### Data Flow

```
State Transition (GAP_BREACH, etc.)
        |
        v
EnforcementEngine.apply_decision()
        |
        ├─> Update MillIntegrityState
        |
        └─> [IF new_state in COMPROMISED, SUSPENDED]
                |
                v
            CapitalAtRisk.handle_state_transition()
                |
                ├─> SUSPENDED: All 3 actions
                |   - cash_sweep()
                |   - credit_compression()
                |   - pricing_escalation()
                |
                └─> COMPROMISED: Actions 1 & 3
                    - cash_sweep()
                    - pricing_escalation()
                    (credit reserved for SUSPENDED)
```

## Capital Control Actions

### 1. Cash Sweep

**Purpose**: Redirect incoming revenue to reduce outstanding exposure

**Mechanism**:
1. Identify outstanding balance (DCE from latest CreditMetrics)
2. Estimate incoming revenue (monthly average or actual stream)
3. Calculate sweep amount = incoming_revenue × sweep_rate (default 90%)
4. Create CreditEvent with CASH_SWEEP action type

**Formula**:
```
sweep_amount = estimated_daily_revenue × DEFAULT_CASH_SWEEP_PRIORITY

where:
  sweep_rate = 0.9 (90% of incoming revenue)
  estimated_daily_revenue = VR / 30
```

**Status Flow**:
```
LOGGED → (Ready for payment system integration)
```

**Database Record**:
```python
CreditEvent {
  action_type: "CASH_SWEEP"
  outstanding_balance: <current DCE>
  action_amount: <sweep amount>
  action_status: "LOGGED"
  notes: "Sweep 90% of incoming revenue..."
}
```

### 2. Credit Compression

**Purpose**: Suspend all remaining credit availability

**Mechanism**:
1. Get current DCE from latest CreditMetrics
2. Set CreditMetrics.status to "SUSPENDED"
3. Create CreditEvent with CREDIT_COMPRESSION action type

**Effect**:
- No new token purchases allowed (blocked at token purchase validation)
- Existing outstanding balance remains due
- Normal credit terms suspended indefinitely

**Status Flow**:
```
LOGGED → COMPLETED (immediately upon execution)
```

**Database Record**:
```python
CreditEvent {
  action_type: "CREDIT_COMPRESSION"
  outstanding_balance: <DCE before compression>
  action_amount: <DCE before compression>  # Full compression
  action_status: "COMPLETED"
  execution_timestamp: <now>
  notes: "Credit compressed from X to 0..."
}
```

### 3. Pricing Escalation

**Purpose**: Apply penalty interest rate to outstanding obligations

**Mechanism**:
1. Get outstanding balance from latest CreditMetrics
2. Apply penalty rate (default +500 bps = +5%)
3. Calculate annual interest impact
4. Create CreditEvent with PRICING_ESCALATION action type

**Formula**:
```
annual_interest_increase = outstanding_balance × (penalty_rate_bps / 10000)

where:
  penalty_rate_bps = 500 (default, can be overridden per event)
  e.g., 500 bps = 5% annual rate increase
```

**Impact Examples**:
- Outstanding balance: 100,000 MWK
- Penalty rate: +500 bps
- Annual cost: 5,000 MWK additional interest

**Status Flow**:
```
LOGGED → (Ready for interest accrual system integration)
```

**Database Record**:
```python
CreditEvent {
  action_type: "PRICING_ESCALATION"
  outstanding_balance: <DCE>
  action_amount: <annual_interest_increase>
  penalty_rate_bps: 500
  action_status: "LOGGED"
  notes: "Penalty rate of 500 bps applied..."
}
```

## State-Based Signal Escalation

Different mill states trigger different capital control intensity:

### SUSPENDED State
**When**: Mill enters SUSPENDED (most severe)
**Actions**: All 3 capital controls activate
```
SUSPENDED
  ├─ cash_sweep(sweep_rate=0.9)
  ├─ credit_compression()
  └─ pricing_escalation(penalty_rate=500 bps)
```

**Rationale**: Mill is completely blocked from normal operations. Maximum capital protection.

### COMPROMISED State
**When**: Mill enters COMPROMISED (medium severity)
**Actions**: Cash sweep + pricing escalation (not credit compression)
```
COMPROMISED
  ├─ cash_sweep(sweep_rate=0.9)
  └─ pricing_escalation(penalty_rate=500 bps)
```

**Rationale**: Mill may recover if accountability improves. Keep credit line intact but apply monitoring.

### Other States
**When**: VERIFIED, UNDER_REVIEW, BREACH
**Actions**: No capital controls (handled via DCE tier adjustments)

## Database Schema

### CreditEvent Table

```python
class CreditEvent(SQLModel, table=True):
    id: Optional[int]                    # Primary key
    mill_id: str                         # Foreign key to Mill
    timestamp: datetime                  # When action was logged
    
    action_type: str                     # CASH_SWEEP | CREDIT_COMPRESSION | PRICING_ESCALATION
    trigger_state: str                   # State that triggered: COMPROMISED, SUSPENDED
    trigger_reason: str                  # Breach reason: GAP_BREACH, ECONOMIC_DEFICIT, etc.
    
    outstanding_balance: float           # Outstanding balance when action triggered
    action_amount: float                 # Amount of action (sweep, compression, or interest cost)
    penalty_rate_bps: int                # Penalty in basis points (0-1000 range)
    
    action_status: str                   # LOGGED | INITIATED | COMPLETED | FAILED
    execution_timestamp: Optional[datetime]  # When action was executed
    notes: Optional[str]                 # Implementation notes, integration status
    
    credit_metric_id: Optional[int]      # Link to CreditMetrics for context
```

**Constraints**:
- `penalty_rate_bps` must be between 0 and 1000 (enforced)
- `action_status` in allowed states
- `action_type` in allowed types

## Integration Points

### 1. Enforcement Engine (`backend/enforcement_engine.py`)

When `apply_decision()` is called:

```python
@classmethod
def apply_decision(cls, mill_id: str, decision: EnforcementDecision) -> MillIntegrityState:
    # ... existing logic ...
    
    # Trigger capital controls if state changes to COMPROMISED/SUSPENDED
    if new_state in ["COMPROMISED", "SUSPENDED"] and old_state != new_state:
        try:
            capital_events = CapitalAtRisk.handle_state_transition(
                mill_id=mill_id,
                old_state=old_state,
                new_state=new_state,
                breach_reason=decision.breach_type,
            )
        except Exception as e:
            logger.error(f"Capital controls failed: {e}")
            # Non-blocking: enforcement continues
```

**Key Points**:
- Capital controls are **non-blocking** (failures don't prevent state transitions)
- Actions logged regardless of execution status
- Designed for gradual payment system integration

### 2. API Layer (`backend/api_reports.py` & `backend/main.py`)

Three API functions expose capital at risk data:

#### `get_capital_exposure_summary(mill_id: str)`

Returns:
```json
{
  "mill_id": "M001",
  "mill_name": "Mkwinda Mill",
  "outstanding_balance": 45000.00,
  "credit_status": "SUSPENDED | ACTIVE",
  "capital_events_30d": 3,
  "cash_swept_30d": 12000.00,
  "interest_impact_annual": 2250.00,
  "recent_events": [...]
}
```

#### `get_capital_events(mill_id: str, days: int = 30, action_type: str = None)`

Returns:
```json
{
  "mill_id": "M001",
  "period_days": 30,
  "event_count": 3,
  "events": [
    {
      "event_id": 1,
      "timestamp": "2024-01-15T10:30:00Z",
      "action_type": "CASH_SWEEP",
      "trigger_state": "SUSPENDED",
      "trigger_reason": "GAP_BREACH",
      "outstanding_balance": 100000.00,
      "action_amount": 8000.00,
      "penalty_rate_bps": 0,
      "action_status": "LOGGED"
    }
  ]
}
```

### 3. REST Endpoints

```
GET /api/v1/mills/{mill_id}/capital/exposure
    Query capital exposure summary

GET /api/v1/mills/{mill_id}/capital/events?days=30&action_type=CASH_SWEEP
    Query historical capital events with optional filters
```

## Implementation Stages

### Stage 1: Audit Trail (CURRENT)
All capital control actions:
- ✅ Logged to CreditEvent table
- ✅ Timestamped and reason-recorded
- ✅ Exposed via read API endpoints
- ✅ Ready for regulatory reporting

### Stage 2: Payment System Integration
Cash sweep actions need integration with:
- Revenue collection pipeline
- Automated sweep processing
- Account reconciliation

### Stage 3: Interest Accrual
Pricing escalation needs integration with:
- Interest accrual module
- Invoice generation
- Payment posting

### Stage 4: Credit Line Management
Credit compression needs integration with:
- Token purchase validation
- Facility management system
- Customer notifications

## Configuration Parameters

Default values (configurable per action):

```python
DEFAULT_CASH_SWEEP_PRIORITY = 0.9      # 90% of incoming revenue
DEFAULT_PENALTY_RATE_BPS = 500         # +500 basis points (+5%)
DEFAULT_CREDIT_COMPRESSION_RATE = 1.0  # Compress to zero immediately
```

Override examples:

```python
# Aggressive cash sweep (95%)
CapitalAtRisk.trigger_cash_sweep(
    mill_id="M001",
    trigger_state="SUSPENDED",
    trigger_reason="ECONOMIC_DEFICIT",
    sweep_rate=0.95
)

# Higher penalty rate (1000 bps = 10%)
CapitalAtRisk.trigger_pricing_escalation(
    mill_id="M001",
    trigger_state="SUSPENDED",
    trigger_reason="REPEATED_BREACHES",
    penalty_rate_bps=1000
)
```

## Audit Trail Queries

### Recent Capital Events
```python
events = CapitalAtRisk.get_credit_events(
    mill_id="M001",
    days=30,
    action_type="CASH_SWEEP"  # Optional filter
)
```

### Capital Exposure Summary
```python
summary = CapitalAtRisk.get_capital_exposure_summary("M001")
print(f"Outstanding: {summary['outstanding_balance']}")
print(f"Credit Status: {summary['credit_status']}")
print(f"Cash Swept: {summary['cash_swept_30d']}")
```

## Testing

### Unit Test Example
```python
def test_capital_controls_triggered_on_suspension():
    mill_id = "TEST_MILL"
    
    # Trigger enforcement decision
    decision = EnforcementEngine.classify_gap_breach("Test GAP")
    state = EnforcementEngine.apply_decision(mill_id, decision)
    
    # If state is SUSPENDED, verify capital events created
    events = CapitalAtRisk.get_credit_events(mill_id, days=1)
    assert len(events) == 3  # All 3 actions triggered
    
    # Verify action types
    action_types = {e['action_type'] for e in events}
    assert "CASH_SWEEP" in action_types
    assert "CREDIT_COMPRESSION" in action_types
    assert "PRICING_ESCALATION" in action_types
```

## Error Handling

Capital control actions are **non-blocking**. If action execution fails:
1. Error logged to application logs
2. Partial success still recorded
3. State transition completes normally
4. Manual remediation via admin panel (future enhancement)

Example:
```python
try:
    capital_events = CapitalAtRisk.handle_state_transition(...)
except CapitalAtRiskError as e:
    logger.error(f"Capital controls failed: {e}")
    # Enforcement decision still applied (best-effort enforcement)
```

## Deployment Checklist

- [x] Module created: `backend/capital_at_risk.py`
- [x] Schema added: `CreditEvent` table
- [x] Enforcement engine integrated
- [x] API endpoints created
- [x] Syntax validation passed
- [x] Import testing passed
- [x] Function existence verified
- [ ] Integration test with real data
- [ ] Load test with multiple concurrent events
- [ ] Backup/recovery procedures documented
- [ ] Admin panel for manual override (future)

## Future Enhancements

1. **Dynamic Parameters**: Configure sweep rates and penalty rates per mill/tier
2. **Payment Integration**: Real cash movement when sweep conditions met
3. **Interest Accrual**: Automated interest calculation and posting
4. **Notification System**: Alert operators of capital control actions
5. **Recovery Path**: Automatic credit restoration when mill status improves
6. **Escalation**: Additional actions for repeated violations

## Support

For questions or issues:
- Check CreditEvent table audit trail
- Review application logs for CapitalAtRisk module
- Query historical events via API `/capital/events` endpoint
- Review enforcement decisions in MillIntegrityState table
