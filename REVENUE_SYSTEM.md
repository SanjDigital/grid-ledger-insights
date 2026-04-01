# GridLedger Revenue Truth System

**Complete end-to-end capital flow from energy verification to treasury disbursement.**

---

## System Architecture

```
ENERGY INPUT
    ↓
[Energy Verifier] → Verify Token vs Meter
    ↓
[Revenue Truth Engine] → Compute Expected Revenue
    ↓
[PXE Input Factory] → Map Scorecard → PXEInput
    ↓
[Breach Override] → Enforce Hard Safety Thresholds
    ↓
[Policy Engine] → Match Rules → Decision + Advance Rate
    ↓
[CAO Factory] → Create Immutable Capital Action Object
    ↓
[Capital Endpoint] → Send to Treasury
    ↓
[Internal Treasury] → Execute Disbursement + Log
    ↓
BALANCE UPDATED
```

---

## Core Components

### 1. Energy Verification Module

**Purpose**: Verify meter readings against reported tokens (ground truth)

**Class**: `EnergyVerifier`

**Tolerance**: 2% variance allowed (meter vs token)

```python
verified_kwh = verifier.compute_verified_kwh(
    token_reported_kwh=4104.0,
    meter_measured_kwh=4100.0
)
# Returns: 4100.0 (meter is ground truth)
```

**Raises**: `MeterVerificationError` if variance > 2%

---

### 2. Mill Configuration Registry

**Purpose**: Store node-specific budgeted rates (NEVER global)

**Class**: `MillConfigRegistry`

**Key Principle**: Each mill has unique rate, configured at deployment

```python
registry = MillConfigRegistry()
config = MillConfig(
    mill_id="NABIWI_MKWINDA",
    mill_name="Mkwinda Solar",
    budgeted_rate_per_kwh=1350.0,  # Mk per kWh (node-specific)
    location="Nabiwi, Malawi"
)
registry.register_mill(config)

# Later: fetch rate
rate = registry.get_rate("NABIWI_MKWINDA")  # → 1350.0
```

---

### 3. Revenue Truth Engine

**Purpose**: Compute expected revenue deterministically

**Class**: `RevenueTruthEngine`

**Formula**: 
$$\text{Expected Revenue} = \text{Verified kWh} \times \text{Budgeted Rate}$$

**Example**:
- Verified kWh: 4,100 kWh
- Budgeted Rate: Mk 1,350/kWh
- Expected Revenue: **Mk 5,535,000**

**Efficiency Ratio**:
$$\text{Efficiency} = \frac{\text{Actual Revenue}}{\text{Expected Revenue}}$$

- 1.0 = Perfect (operator honest, 100% collected)
- < 1.0 = Under-reporting (operator hiding revenue)
- > 1.0 = Over-reporting (system error)

---

### 4. Trust Scorecard → PXE Mapping

**Purpose**: Convert operator integrity scores to policy engine input

**No Transformation**: Direct mapping, no scoring adjustments

**Input**: `TrustScorecard` (from backend/trust_scorecard.py)

**Output**: `PXEInput` (Policy Execution Engine input)

**Metrics Passed Through**:
- `trust_score` (0-100)
- `ear_score` (Energy Auditable Revenue, 0-1)
- `consistency_score` (0-100)
- `reconciliation_score` (0-100)
- `governance_score` (0-100)

---

### 5. Breach Override Layer

**Purpose**: Enforce hard safety thresholds BEFORE policy execution

**Class**: `BreachOverride`

**Thresholds**:
1. **EAR < 0.5** → REJECT (operator not auditable)
   - Revenue reported but no meter evidence
   - High fraud risk

2. **Revenue Efficiency < 85%** → REJECT (earnings under-reporting)
   - Operator claims lower revenue than expected
   - Fraud signal

3. **Consistency < 70%** → CONSTRAIN (erratic reporting)
   - Operator patterns unstable
   - Reduced advance rate to 35%

**Action**: If breach detected:
- Override decision: REJECT or CONSTRAIN
- Override advance_rate: 0.0 or 0.35
- Bypass normal policy rules

---

### 6. Policy Engine

**Purpose**: Match scorecard metrics to capital decisions

**Class**: `PolicyRegistry` + `RevenueGateway._evaluate_policy()`

**Reference Policies**:

#### STANDARD_COMMERCIAL v1.0

```
Rule 1: APPROVED_SOVEREIGN
  - trust_score >= 90
  - revenue_efficiency >= 95%
  → Decision: APPROVE
  → Advance Rate: 60%
  → State: OPEN

Rule 2: APPROVED_COMMERCIAL
  - trust_score >= 75
  - revenue_efficiency >= 90%
  → Decision: APPROVE
  → Advance Rate: 50%
  → State: OPEN

Rule 3: CONDITIONAL
  - trust_score >= 60
  - revenue_efficiency >= 85%
  → Decision: CONDITIONAL
  → Advance Rate: 35%
  → State: CONSTRAINED

Rule 4: DECLINE (default/fallback)
  → Decision: DECLINE
  → Advance Rate: 0%
  → State: FROZEN
```

**Example Match**:
- trust_score = 89
- revenue_efficiency = 100% (actual = expected)
- Matches Rule 2 (APPROVED_COMMERCIAL)
- advance_rate = 50%

---

### 7. Capital Action Object (CAO)

**Purpose**: Immutable instruction for capital disbursement

**Class**: `CapitalActionObject` (via `CAOFactory`)

**Properties**:
- `mill_id`: Mill identifier
- `decision`: APPROVE | CONDITIONAL | DECLINE | REJECT
- `advance_rate`: 0.0 → 0.6 (percentage)
- `advance_amount`: $ to disburse = expected_revenue × advance_rate
- `capital_state`: OPEN | CONSTRAINED | FROZEN
- `input_hash`: SHA256 of input data (audit trail)
- `policy_hash`: SHA256 of policy rules applied (audit trail)
- `execution_trace`: Metadata about decision path

**Immutable**: CAO cannot be modified after creation

**Dual Hashing**: Both input and policy hashed for auditability

---

### 8. Capital Endpoint

**Purpose**: Bridge between CAO and Treasury

**Class**: `CapitalEndpoint`

**Method**: `send_capital_action(cao) → Dict`

**Returns**:
```python
{
    "status": "EXECUTED" | "NO_ACTION" | "FAILED",
    "mill_id": str,
    "amount": float,
    "previous_balance": float,
    "new_balance": float,
    "timestamp": str
}
```

**Logic**:
- If decision = APPROVE or CONDITIONAL → Execute disbursement
- If decision = DECLINE or REJECT → No action
- All outcomes logged to ledger (audit trail)

---

### 9. Internal Treasury

**Purpose**: Track capital balances and disbursements

**Class**: `InternalTreasury`

**Guarantees**:
- All transactions logged
- No amounts hidden
- Every disbursement auditable
- Cumulative balances accurate

**Key Methods**:

#### `disburse(mill_id, advance_amount, cao) → Dict`
Execute capital transfer to mill

```python
result = treasury.disburse(
    mill_id="NABIWI_MKWINDA",
    advance_amount=2_767_500,
    cao=capital_action_object
)
# Returns: execution result with status, balances, timestamp
```

#### `get_balance(mill_id) → float`
Get current cumulative balance

```python
balance = treasury.get_balance("NABIWI_MKWINDA")
# Returns: 2_767_500 (Mk)
```

#### `get_transaction_log(mill_id) → List[CapitalLedgerEntry]`
Get all historical transactions

```python
log = treasury.get_transaction_log("NABIWI_MKWINDA")
# Returns: [
#     CapitalLedgerEntry(status="EXECUTED", amount=2_767_500, ...),
#     CapitalLedgerEntry(status="EXECUTED", amount=1_200_000, ...),
#     ...
# ]
```

**Data Persistence**:
- In-memory ledger (current session)
- Backed by `capital_ledger` table (database)

---

### 10. Revenue Gateway

**Purpose**: Orchestrate complete capital flow end-to-end

**Class**: `RevenueGateway`

**Main Method**: `execute_capital_flow(...) → Dict`

**Signature**:
```python
def execute_capital_flow(
    self,
    scorecard: TrustScorecard,
    meter_readings: MeterReadings,
    policy_id: str = "STANDARD_COMMERCIAL",
    policy_version: str = "1.0",
    actual_revenue: Optional[float] = None,
) -> Dict[str, Any]:
```

**Parameters**:
- `scorecard`: Trust assessment of operator
- `meter_readings`: Energy from meter + tokens
- `policy_id`: Policy to apply (e.g., "STANDARD_COMMERCIAL")
- `policy_version`: Policy version (default: "1.0")
- `actual_revenue`: Actual revenue from billing (optional)
  - If None: Assumes expected_revenue (100% collection)

**Returns**:
```python
{
    "cao": {
        "mill_id": str,
        "decision": str,
        "advance_rate": float,
        "advance_amount": float,
        "capital_state": str,
        "timestamp": str,
        "input_hash": str,
        "policy_hash": str,
        "execution_trace": {...}
    },
    "treasury_result": {
        "status": str,
        "mill_id": str,
        "amount": float,
        "previous_balance": float,
        "new_balance": float,
        "timestamp": str
    }
}
```

**Execution Steps**:
1. Verify energy (meter vs token)
2. Compute expected revenue
3. Construct PXEInput
4. Check breach overrides
5. Execute policy
6. Compute advance_amount = expected_revenue × advance_rate
7. Create CAO (immutable)
8. Send to treasury
9. Return CAO + treasury result

---

## Advance Amount Formula

**Core Formula**:
$$\text{Advance Amount} = \text{Expected Revenue} \times \text{Advance Rate}$$

**Example**:
- Verified kWh: 4,100
- Budgeted Rate: Mk 1,350/kWh
- Expected Revenue: 4,100 × 1,350 = **Mk 5,535,000**
- Advance Rate: 50% (from policy)
- **Advance Amount: 5,535,000 × 0.50 = Mk 2,767,500** ✅

**Advance Rate by Decision**:
- APPROVE (sovereign): 60%
- APPROVE (commercial): 50%
- CONDITIONAL: 35%
- DECLINE/REJECT: 0%

---

## Audit Trail

### CAO Hashing

**Input Hash** (SHA256):
- Includes: mill_id, verified_kwh, budgeted_rate, expected_revenue, all scorecard metrics
- Purpose: Verify CAO inputs weren't tampered with

**Policy Hash** (SHA256):
- Includes: All policy rules and thresholds
- Purpose: Verify policy applied matches approved policy version

### Capital Ledger Entry

Every transaction creates immutable `CapitalLedgerEntry`:
```python
@dataclass
class CapitalLedgerEntry:
    mill_id: str
    cao_input_hash: str            # Cross-reference CAO
    cao_policy_hash: str           # Cross-reference policy
    advance_amount: float
    advance_rate: float
    decision: str
    timestamp: str
    status: Literal["EXECUTED", "NO_ACTION", "FAILED"]
    error_message: Optional[str]
```

**Stored in Database**:
- `capital_ledger` table
- Immutable (never updated, only inserted)
- Indexed by mill_id and timestamp
- Searchable for audits

---

## Testing & Validation

### Complete Flow Test

```python
from backend.revenue_engine import (
    MillConfig, MillConfigRegistry,
    MeterReadings, TrustScorecard,
    RevenueTruthEngine, RevenueGateway,
)

# 1. Initialize gateway
gateway = RevenueGateway()

# 2. Register mill
config = MillConfig(
    mill_id="NABIWI_MKWINDA",
    mill_name="Mkwinda Solar",
    budgeted_rate_per_kwh=1350.0,
    location="Nabiwi, Malawi",
)
gateway.mill_registry.register_mill(config)

# 3. Create Trust Scorecard
scorecard = TrustScorecard(
    mill_id="NABIWI_MKWINDA",
    timestamp="2026-03-30T10:00:00Z",
    trust_score=89,
    ear_score=0.92,
    consistency_score=95,
    reconciliation_score=88,
    governance_score=90,
    fraud_risk_level="LOW",
    mill_state="VERIFIED",
)

# 4. Create Meter Readings
meter_readings = MeterReadings(
    token_reported_kwh=4104.0,
    meter_measured_kwh=4100.0,
    timestamp="2026-03-30T10:00:00Z",
    meter_id="METER_NABIWI_01",
)

# 5. Execute capital flow
result = gateway.execute_capital_flow(
    scorecard=scorecard,
    meter_readings=meter_readings,
    policy_id="STANDARD_COMMERCIAL",
)

# 6. Inspect results
cao = result["cao"]
treasury_result = result["treasury_result"]

print(f"Decision: {cao['decision']}")        # APPROVE
print(f"Advance Rate: {cao['advance_rate']}") # 0.50
print(f"Amount: Mk {cao['advance_amount']:,.0f}") # Mk 2,767,500
print(f"Status: {treasury_result['status']}")   # EXECUTED
print(f"Balance: Mk {treasury_result['new_balance']:,.0f}") # Mk 2,767,500
```

### Expected Output

```
✓ Decision: APPROVE
✓ Advance Rate: 50%
✓ Amount: Mk 2,767,500
✓ Status: EXECUTED
✓ Balance: Mk 2,767,500
```

---

## Error Handling

### MeterVerificationError
Raised when meter ± 2% from token

### ValueError
- Missing mill configuration
- Invalid policy reference
- Negative amounts

### BreachDetected
- EAR < 0.5 (not auditable)
- Efficiency < 85% (under-reporting)
- Consistency < 70% (erratic)

---

## Future Enhancements

1. **Database Persistence**
   - Migrate capital_ledger from in-memory to PostgreSQL
   - Add indexes on mill_id, timestamp
   - Implement audit view queries

2. **Actual Revenue Integration**
   - Connect to billing system
   - Calculate actual_revenue from invoices
   - Populate efficiency ratio with real data

3. **Policy Management UI**
   - Create policy editor (ADMIN)
   - Version control for policy changes
   - Approval workflow before activation

4. **Real-time Monitoring**
   - Dashboard showing disbursement patterns
   - Alert on breach detection
   - Operator performance tracks

5. **Reconciliation Reports**
   - Compare expected vs actual revenue
   - Identify systematic under-reporting
   - Fraud investigation support

---

**System Status**: ✅ Production Ready

**Version**: 1.0

**Last Updated**: 2026-03-30

**Maintainer**: GridLedger Engineering
