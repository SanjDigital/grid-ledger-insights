# Dynamic Credit Envelope (DCE) - Implementation Guide

## Overview
The Dynamic Credit Envelope (DCE) module (`backend/capital_controls.py`) calculates per-mill credit capacity based on verified energy throughput, accountability metrics, and historical risk patterns.

**DCE Formula:**
```
DCE = α × VR × EAR × (1 − RiskPenalty)
```

This deterministically couples financing limits to:
- Physical energy consumption (metered_kwh)
- Reported accountability (EAR)
- Verified revenue (VR)
- Operational risk (breach history + volatility)

## Architecture

### Components

#### 1. Effective Revenue Rate (ERR)
```
ERR = total_cash_collected / metered_kwh
```
- Denominated in local currency per kWh (e.g., MWK/kWh)
- Derived from latest reconciliation record
- Reflects actual financial output per unit of verified energy

#### 2. Verified Revenue (VR)
```
VR = VT × ERR
```
- Where VT = Verified Throughput (already calculated from EAR)
- Coupled to accountability via EAR × metered energy
- If EAR = 0.8, then only 80% of metered energy counts toward VR

#### 3. Risk Penalty
```
RiskPenalty = min(0.5, breach_count × 0.1 + volatility × 0.05)
```

**Breach Component:**
- Count breaches in last 30 days from Cycle table (gap_breach_detected)
- Each breach adds 0.1 to penalty
- Example: 3 breaches = 0.3 penalty

**Volatility Component:**
- Coefficient of variation of variance_pct across recent reconciliations
- Calculated over 30-day window
- High volatility (unstable reporting) adds penalty
- Formula: (stddev / mean) × 0.05
- Example: CV=1.0 → 0.05 volatility penalty

**Cap:** Total penalty never exceeds 0.5 (50% reduction max)

Examples:
```
No breaches, low volatility (CV=0.1): penalty = 0.005
2 breaches, moderate volatility (CV=0.5): penalty = 0.2 + 0.025 = 0.225
5 breaches, high volatility (CV=1.0): min(0.5, 0.5 + 0.05) = 0.5
```

#### 4. Advance Rate (α)
- Configurable per mill
- Default: 0.6 (60%)
- Stored in CreditMetrics for auditability
- In production: Should be stored in MillConfig table

#### 5. Final DCE
```
DCE = α × VR × EAR × (1 − RiskPenalty)
```

**Example calculation:**
```
Mill: "mkwinda"
α = 0.6
VR = 100,000 MWK (VT=80 kWh × ERR=1,250 MWK/kWh)
EAR = 0.95
RiskPenalty = 0.1 (1 breach)

DCE = 0.6 × 100,000 × 0.95 × (1 - 0.1)
    = 0.6 × 100,000 × 0.95 × 0.9
    = 51,300 MWK

% of VR: 51,300 / 100,000 = 51.3% advance possible
```

## Database Schema

### CreditMetrics Table
```python
class CreditMetrics(SQLModel, table=True):
    id: Optional[int]                    # Auto-increment ID
    mill_id: str                         # Foreign key
    timestamp: datetime                  # Calculation timestamp
    
    # Input parameters
    advance_rate: float                  # α (0.0-1.0)
    effective_revenue_rate: float        # ERR (currency/kWh)
    energy_accountability_ratio: float   # EAR (0.0-1.0)
    verified_throughput: float           # VT (kWh)
    verified_revenue: float              # VR (currency)
    
    # Risk assessment
    breach_count_30d: int                # Recent breaches
    volatility_score: float              # Coefficient of variation
    risk_penalty: float                  # Combined penalty (0.0-0.5)
    
    # Result
    dynamic_credit_envelope: float       # Final DCE value
    
    # References
    reconciliation_record_id: Optional[int]  # Source recon record
    status: str                          # CALCULATED, APPLIED, SUSPENDED
```

**Constraints:**
- `advance_rate` ∈ [0, 1]
- `energy_accountability_ratio` ∈ [0, 1]
- `risk_penalty` ∈ [0, 0.5]

## API Endpoints

### 1. Calculate Current DCE
```
GET /api/v1/mills/{mill_id}/credit/dce
```

**Response:**
```json
{
  "mill_id": "mkwinda",
  "mill_name": "Mkwinda Maize Mill",
  "location": "Chikwawa District",
  "timestamp": "2026-03-29T16:45:00Z",
  
  "dynamic_credit_envelope": 51300.00,
  
  "components": {
    "advance_rate_alpha": 0.6,
    "verified_revenue_vr": 100000.00,
    "energy_accountability_ratio_ear": 0.95,
    "risk_penalty": 0.1
  },
  
  "metrics": {
    "effective_revenue_rate_err": 1250.00,
    "verified_throughput_kwh": 80.0,
    "breaches_30d": 1,
    "volatility_score": 0.05,
    "physical_consumed_kwh": 84.2,
    "total_cash_collected": 105100.0
  },
  
  "recommendation": "CONDITIONAL",
  "rationale": "Strong DCE: 51300 MWK (51.3% of VR); Perfect accountability: EAR=95%; 1 breach in last 30 days",
  
  "credit_metric_id": 42,
  "reconciliation_record_id": 127
}
```

### 2. DCE History
```
GET /api/v1/mills/{mill_id}/credit/history?days=30
```

**Response:**
```json
{
  "mill_id": "mkwinda",
  "mill_name": "Mkwinda Maize Mill",
  "period_days": 30,
  "dce_history": [
    {
      "timestamp": "2026-03-29T16:45:00Z",
      "dce": 51300.00,
      "vr": 100000.00,
      "ear": 0.95,
      "risk_penalty": 0.1,
      "breach_count": 1
    },
    ...previous snapshots...
  ]
}
```

### 3. Capital Tier Recommendation
```
GET /api/v1/mills/{mill_id}/credit/tier
```

**Response:**
```json
{
  "mill_id": "mkwinda",
  "capital_tier": "TIER_2_COMMERCIAL",
  "dce_percentage_of_vr": 51.3,
  "max_leverage_ratio": 2.5,
  "interest_rate_adjustment_bps": -250,
  "interest_rate_adjustment_pct": -2.50,
  "rationale": "Stable performance with acceptable variance",
  
  "dce_data": { ...full DCE response... }
}
```

## Capital Tiers

### Tier 1: Institutional Grade
```
Criteria:
  - DCE ≥ 60% of VR
  - EAR ≥ 95%
  - Zero breaches in last 30 days

Benefits:
  - Max leverage: 3.5x
  - Interest rate: -500 bps (~-5% adjustment)
  - Minimal onsite audits
  - Priority financing approval
```

### Tier 2: Commercial
```
Criteria:
  - DCE ≥ 40% of VR
  - EAR ≥ 85%
  - Stable, low volatility

Benefits:
  - Max leverage: 2.5x
  - Interest rate: -250 bps (~-2.5% adjustment)
  - Quarterly verification
  - Standard commercial terms
```

### Tier 3: Subprime
```
Criteria:
  - DCE ≥ 20% of VR
  - EAR ≥ 70%
  - Under operational review

Benefits/Restrictions:
  - Max leverage: 1.5x
  - Interest rate: 0 bps (baseline)
  - Monthly audits required
  - Elevated monitoring
```

### Tier 4: Restricted
```
Criteria:
  - DCE < 20% of VR
  - EAR < 70%
  - Persistent breaches

Restrictions:
  - Max leverage: 1.0x
  - Interest rate: +300 bps (~+3% adjustment)
  - Bi-weekly compliance checks
  - High-touch due diligence
```

## Integration Points

### 1. Reconciliation Pipeline
- DCE auto-calculated after each daily reconciliation
- Snapshot stored in CreditMetrics
- ERR derived from reconciliation.total_cash / reconciliation.physical_consumed

### 2. Breach Detection
- Gap breaches from Cycle.gap_breach_detected
- Temporal breaches from temporal_guard.py
- Signature/replay failures tracked in EnforcementEngine

### 3. Financing Decisions
- Token purchase eligibility: Check DCE ≥ certain threshold
- Collateral requirements: Tier-based adjustments
- Interest rate: Apply tier-specific adjustment (bps)

### 4. Audit Trails
- Every DCE calculation stored in CreditMetrics
- Linked to source reconciliation record
- Historical trend analysis via get_dce_history()

## Usage Examples

### Calculate DCE
```python
from backend.capital_controls import CapitalControls

result = CapitalControls.calculate_dce("mkwinda")
dce = result["dynamic_credit_envelope"]
tier = result["recommendation"]
print(f"Mill can advance up to {dce:,.0f} MWK ({tier})")
```

### Check Risk Metrics
```python
breach_count = CapitalControls.count_breaches_30d("mkwinda")
volatility = CapitalControls.calculate_volatility_score("mkwinda")
penalty = CapitalControls.calculate_risk_penalty(breach_count, volatility)
print(f"Risk penalty: {penalty:.1%}")
```

### Get DCE History
```python
history = CapitalControls.get_dce_history("mkwinda", days=30)
for snapshot in history:
    print(f"{snapshot['timestamp']}: DCE={snapshot['dce']}")
```

## Production Considerations

### 1. Per-Mill Alpha Configuration
- Implement MillConfig table to store advance_rate per mill
- Update `get_mill_advance_rate()` to query MillConfig
- Allow operators to override default (0.6) with audit trail

### 2. Dynamic Volatility Window
- Consider seasonal patterns (e.g., harvest season)
- May need rolling 90-day window for agricultural cycles
- Adjust penalty formula per sector

### 3. Breach Scoring
- Current: Simple count × 0.1
- Consider: Severity weighting (temporal breach = 0.15, signature = 0.05)
- Track resolution time (quick fixes reduce penalty)

### 4. Real-time Monitoring
- Schedule DCE recalculation daily (post-reconciliation)
- Alert on downgrade to lower tier
- Proactive notifications to operators of pending breaches

### 5. Audit Requirements
- Store calculation rationale (why XYZ tier?)
- Maintain immutable CreditMetrics records
- Provide detailed capital_recommendation_reason

### 6. Collateral Integration
- DCE should feed into collateral requirement calculation
- Example: Required collateral = (0.2 / leverage_ratio) × loan_amount
- Tier 2 @ 2.5x leverage → 8% collateral requirement

## Testing

### Test ERR Calculation
```python
err = CapitalControls.calculate_effective_revenue_rate(130650, 100.5)
assert round(err, 2) == 1300.0  # MWK/kWh
```

### Test VR Calculation
```python
vr = CapitalControls.calculate_verified_revenue(80, 1250)
assert vr == 100000.0  # MWK
```

### Test Risk Penalty Capping
```python
penalty = CapitalControls.calculate_risk_penalty(10, 0.9)
assert penalty == 0.5  # Capped at 50%
```

### Test DCE End-to-End
```python
result = CapitalControls.calculate_dce("test_mill_001")
assert "dynamic_credit_envelope" in result
assert "recommendation" in result
assert result["components"]["advance_rate_alpha"] in [0.0, 1.0]
```

## Related Documentation
- [EAR & VT Implementation](./CAPITAL_IMPACT_LAYER.md)
- [Temporal Guard Guide](./TEMPORAL_GUARD_GUIDE.md)
- [Trust Scorecard](./ARCHITECTURE.md)
