# GridLedger Verification Protocol
Status: v3.0 (Phase 1 Enhancements: Idempotency, Time-Weighted Risk, Effective Rate Forensics)
Authority: FL00R G3N3RAL

> **v3.0 Amendment Log (Phase 1 – April 2026)**
> - §2.7: Idempotency mechanism added (24-hour cache, Idempotency-Key header, safe retry semantics)
> - §2.8: Time-weighted risk calculation added (linear multiplier, caps stale allocations)
> - §2.9: Effective rate tracking metric added (forensic, reveals operator bucket mix behavior)
> - §2.10: Nabiwi calibration baseline established (1,340–1,360 MWK/kWh band from Q1 2026 SMS data)
> - §3.2: Per-mill observation protocol (no enforcement, collect 5–10 cycles, then tighten bands)
> - §5.2: API endpoint documentation updated with new headers and response fields

---

## 0. Signal-to-Signature: The Seven-Step Enforcement Chain

*This section is the capital markets summary of the full protocol. Every step below maps to a specific layer in Sections 1–10.*

```
Step 1 — PHYSICAL EVENT
  59.9 kWh energy token allocated to node.
  Production capacity physically constrained by token.
  No energy → no production. The gate is not a policy. It is physics.

Step 2 — SIGNED PAYLOAD (Layer 1)
  Operator submits event signed with Ed25519 key.
  Canonical JSON normalisation. Tamper-evident at origin.
  Identity is verified. Activity is not yet trusted.

Step 3 — CONTINUITY CHECK (Layer 2)
  previous.meter_close == current.meter_open
  Any break in sequence: GapBreachError raised immediately.
  Missing or reordered events cannot pass this gate.

Step 4 — FINANCIAL TRANSLATION (Layer 3)
  ERR (Expected Revenue Rate) = allocated_kWh × revenue_rate_per_kWh
  ARR (Actual Revenue Rate) = cash_remitted / kWh_allocated
  Variance computed. Tolerance: ±5%.
  EAR (Energy Accountability Ratio) = reported_kWh / metered_kWh

Step 5 — FORENSIC ANCHOR (Merkle)
  All window events hashed into Merkle tree.
  Root stored as cryptographic anchor.
  Changing, inserting, deleting, or reordering any event changes the root.
  Auditor can recompute root from raw events at any time.

Step 6 — TRUST SCORECARD (0–100)
  Reconciliation Score (50%): physical vs. ledger variance
  Consistency Score (30%): statistical anomaly detection
  Governance Score (20%): signature and RBAC enforcement
  EAR Tier applied (TIER 1/2/3) via Bounded Imperfection Doctrine.
  Score drives financing recommendation: APPROVE / CONDITIONAL / DECLINE.

Step 7 — POLICY EXECUTION ENGINE (Layer 4 — PXE)
  Verified state → deterministic Capital Action Object (CAO).
  No human interpretation inside execution boundary.
  Identical inputs → identical outputs. Always.
  Capital gate: ALLOW / REDUCE / BLOCK.
```

**The investor statement**: Seven steps from physics to capital decision. No discretion. No self-reporting trusted. False reporting is not prevented — it is made economically, physically, and statistically unsustainable over time.

---

## 1. The trust model

GridLedger operates under a **Zero-Trust Data Assumption**.

The system does **not** validate whether reported data is true.  
It enforces whether reported data is **possible** under known constraints.

The system’s authority comes from proving **impossibility**, not asserting truth.

### 1.1 Security assumptions

#### Input integrity

GridLedger assumes the following inputs are sourced from **high-integrity channels**:

- `TokenPurchase` records (economic inputs)
- `physical_reading` values (reconciliation inputs)

If these inputs are not independently verifiable, outputs remain **directionally valid**, not forensically absolute.

#### Shadow meter risk (consistent spoofing)

The system explicitly acknowledges **consistent spoofing via a parallel ledger (“Shadow Meter”)**:

- A disciplined operator may maintain internally consistent meter logs.
- A sophisticated operator may bypass actual physical consumption while keeping reported continuity perfect.

Implication:

- Layer 2 will validate such data.
- Detection is deferred to Layer 3 constraints.

#### Cryptographic sovereignty

All events must be signed by an authorized `operator_id`.

The system trusts **Identity**.  
The system verifies **Constraints**.  
The system does not trust **Activity** at face value.

---

## 2. Architectural layers

### Layer 1: Identity & integrity (**implemented**)

Mechanism:

- Ed25519 digital signatures
- Canonical JSON normalization

Guarantee:

- Data origin is verifiable
- Payloads are tamper-evident after submission

Constraint:

- Does not validate correctness of submitted values

### Layer 2: Continuity constraint engine (**implemented**)

Mechanism:

- `check_gap_breach_event()` — `backend/authority_engine.py`

Core rule:

- `previous.meter_close == current.meter_open`

Guarantee:

- Detects missing or altered sequence continuity
- Enforces internal consistency across sequential event logs

Critical limitation:

Layer 2 validates continuity, not semantic truth. A perfectly consistent but fabricated dataset:

- will pass all Layer 2 checks
- will appear operationally valid

### Layer 2.5: Energy Cost Tracking (TariffRate System) (**implemented**)

**Purpose**:

- Track owner's energy cost from ESCOM (for profit margin analysis)
- Support MERA tariff adjustments in owner's financial models
- Enable cost reconciliation per ESCOM invoices
- **NOT** used in per-cycle enforcement logic

**Critical Distinction**:

GridLedger's enforcement uses two distinct rates that must never be conflated:

| Rate | Field | Example | Purpose | Used By |
|------|-------|---------|---------|---------|
| **Revenue Rate** | `Mill.revenue_rate_per_kwh` | 1,350 MK/kWh (Nabiwi) | What operator charges customers | `allocate_token()` → `expected_revenue` |
| **Energy Cost** | `TariffRate.rate_mk_per_kwh` | 284.15 MK/kWh (MERA ET7 Jan 2026) | What owner pays ESCOM | Owner's P&L, cost accounting |

**Why the Distinction Matters**:

- Owner buys energy from ESCOM at the MERA tariff (K284.15/kWh as of 2026-01-19 for ET7)
- Owner agrees with operator on a fixed customer-facing rate (e.g., K1,350/kWh)
- Margin = (1,350 − 284.15) × kWh = profit or loss per cycle
- If enforcement used energy cost instead of revenue rate, `expected_revenue` would be understated by ~79%, breaking Grid Ledger's verification logic

**Problem Example** (Before fixing):

```
NABIWI revenue rate agreement: K1,350/kWh
ESCOM energy cost: K160.13/kWh

WRONG (using energy cost):
  expected_revenue = 59.9 kWh × K160.13 = K9,592
  actual_revenue = K80,955 (operator paid per agreement)
  adherence = 80,955 / 9,592 = 844% (system thinks operator stole cash!)

CORRECT (using revenue rate):
  expected_revenue = 59.9 kWh × K1,350 = K80,865
  actual_revenue = K80,955
  adherence = 80,955 / 80,865 = 100.1% (normal, within tolerance)
```

#### 3.0a Tariff Rate Model (TariffRate table) – Cost Tracking Only

Immutable append-only ledger of historical **owner energy costs** (not used in enforcement):

| Field | Type | Purpose |
|-------|------|---------|
| `mill_id` | string | Which location (owner's cost tracking) |
| `rate_mk_per_kwh` | float | ESCOM tariff rate in MK per kWh |
| `effective_date` | datetime | When MERA tariff becomes active |
| `set_by` | string | Admin identifier (e.g., "MERA_ADMIN") |
| `notes` | string (optional) | Reason: "MERA Jan 2026 adjustment +12%" |
| `created_at` | datetime | Record creation timestamp |

**Usage**: Cost accounting, P&L analysis, MERA tariff tracking (owner's operational finance).  
**NOT used**: Per-cycle enforcement, adherence calculations, expected revenue.

#### 3.0b Revenue Rate Model – Mill.revenue_rate_per_kwh

Static per-mill field in the `Mill` model:

```python
class Mill(SQLModel, table=True):
    id: str  # e.g., "NABIWI_NRID"
    # ...
    revenue_rate_per_kwh: float  # e.g., 1,350.0 for Nabiwi
```

**Properties**:
- Set by owner–operator agreement (e.g., "operator will charge customers K1,350 per kWh")
- **Static** (not versioned like TariffRate) because it's a contractual obligation
- Changes only when owner and operator renegotiate the customer-facing price
- **Directly used** in all enforcement calculations: `expected_revenue = allocated_kwh × revenue_rate_per_kwh`

#### 3.0c Enforcement Integration

**Expected Revenue Calculation** (backend/token_gateway.py):

```python
# CORRECT: Use revenue_rate_per_kwh (what operator charges customers)
mill = session.get(Mill, mill_id)
allocated_kwh = 59.9
expected_revenue = allocated_kwh * mill.revenue_rate_per_kwh  # e.g., 59.9 * 1,350 = 80,865

allocation = TokenAllocation(
    mill_id=mill_id,
    allocated_kwh=allocated_kwh,
    expected_revenue=expected_revenue,  # Now accurate for adherence verification
    status="PENDING"
)
```

**EAR & Adherence Calculations**:

All downstream metrics depend on correct `expected_revenue`:
- Energy Accountability Ratio: EAR = reported_kwh / metered_kwh (independent of rates)
- Revenue Ratio: actual_revenue / expected_revenue (uses revenue_rate_per_kwh)
- Glass Box adherence: Requires expected_revenue to be per-operator-agreement, not ESCOM cost basis

#### 3.0d MERA Tariff Tracking (Cost Accounting, Phase 2)

When MERA announces a new tariff (e.g., ET7 schedule: 253.70 Mk/kWh until 2026-01-19, then 284.15 Mk/kWh effective 2026-01-19):

1. **Log in TariffRate** (for owner's cost tracking):
   ```sql
   -- Historical rate (pre-Jan 19, 2026)
   INSERT INTO tariff_rates (mill_id, rate_mk_per_kwh, effective_date, set_by, notes)
   VALUES ('NABIWI_NRID', 253.70, '2026-01-01T00:00:00Z', 'GRIDLEDGER_SYSTEM', 'MERA ET7 rate before Jan 2026 adjustment');
   
   -- New rate effective Jan 19, 2026 (+12% adjustment)
   INSERT INTO tariff_rates (mill_id, rate_mk_per_kwh, effective_date, set_by, notes)
   VALUES ('NABIWI_NRID', 284.15, '2026-01-19T00:00:00Z', 'GRIDLEDGER_SYSTEM', 'MERA Jan 2026 ET7 tariff adjustment: +12.0% to 284.15 Mk/kWh');
   ```

2. **Do NOT change Mill.revenue_rate_per_kwh** — that's the operator agreement, not affected by ESCOM's cost changes.

3. **Owner's cost accounting** can query TariffRate to compute profit margins for quarters/years:
   ```python
   # Owner profit per cycle = (revenue_rate - energy_cost) × kWh
   # Example for Nabiwi (59.9 kWh per cycle):
   # Pre-Jan 19: profit = (1,350 - 253.70) × 59.9 = 65,694 Mk per cycle
   # Post-Jan 19: profit = (1,350 - 284.15) × 59.9 = 63,870 Mk per cycle (↓ 1,824 Mk or -2.8%)
   profit = (mill.revenue_rate_per_kwh - tariff_rate.rate_mk_per_kwh) * 59.9
   ```

**Key Principle**: TariffRate is informational for owner accounting; it never affects the operator's enforced obligations.

---

## 2.7 Idempotency & Duplicate Prevention (Phase 1 – **implemented**)

### Purpose

Prevent duplicate token allocations and cash receipt records when requests are retried (network timeouts, client-side retries, etc.).

### Mechanism

**IdempotencyRecord Table**:

| Field | Type | Purpose |
|-------|------|---------|
| `id` | int | Primary key |
| `idempotency_key` | str (unique) | Client-provided UUID (required header) |
| `mill_id` | string | Mill identifier |
| `created_at` | datetime | When this cache entry was created |
| `response_json` | json | Cached response body (serialized) |
| `allocation_id` | int | Associated TokenAllocation.id |
| `expires_at` | datetime | TTL expiry (24 hours from creation) |

**Request Flow**:

1. **Client sends request with `Idempotency-Key` header**:
   ```bash
   curl -X POST http://localhost:8000/api/owner/mills/NABIWI_01/allocate-token \
     -H "X-API-Key: owner-secret" \
     -H "Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000"
   ```

2. **Server checks cache FIRST** (before acquiring locks):
   - Query `IdempotencyRecord` WHERE `idempotency_key = 550e8400...` AND `expires_at > now()`
   - If found and not expired: return cached response immediately (no new allocation)
   - If not found or expired: proceed to allocation logic

3. **On successful allocation**:
   - Store response in `IdempotencyRecord.response_json`
   - Set `expires_at = now() + 24 hours`
   - Return response

4. **Retry semantics**:
   - Identical `Idempotency-Key` + same `mill_id` = guaranteed identical response
   - Safe to retry indefinitely; no duplicate side effects

### Benefits

- **Network resilience**: Client can safely retry failed requests without creating extra allocations
- **Operator workflow**: Multiple submission attempts don't accumulate phantom tokens
- **Auditability**: Retried requests map to same allocation ID, not new ones

---

## 2.8 Time-Weighted Risk (Phase 1 – **implemented**)

### Purpose

Make delays (overdue allocations) progressively more expensive by applying a multiplier to capital-at-risk calculations. This incentivizes operators to submit receipts promptly and discourages stale allocations.

### Formula

```
time_weighted_risk = capital_at_risk × (1 + 0.1 × overdue_days)
  capped at 2.0× (maximum multiplier)
```

**Where**:
- `overdue_days` = (now − allocation.created_at) / 86400, measured in days
- Linear growth: each additional day adds 10% penalty
- Cap: After 10 days, multiplier is frozen at 2.0× (no incentive to abandon the cycle completely)

### Behavior

| Condition | Multiplier | Effect |
|-----------|-----------|--------|
| Same day allocation | 1.0× | No penalty, normal capital at risk |
| 2 days overdue | 1.2× | 20% additional pressure |
| 5 days overdue | 1.5× | 50% additional pressure |
| 10+ days overdue | 2.0× | Maximum pressure (capped at 2.0×) |

### Implementation

**Computed dynamically** in `_compute_capital_at_risk()`:

```python
def _compute_capital_at_risk(mill_id: str, cycle_state: str, session: Session) -> tuple[Decimal, Decimal]:
    """
    Returns (capital_at_risk, time_weighted_risk)
    
    time_weighted_risk factors overdue days into risk pressure:
    - Linear multiplier: 1 + 0.1 × overdue_days
    - Capped at 2.0× to avoid infinite penalties
    - Incentivizes prompt receipt submission
    """
    allocation = session.exec(
        select(TokenAllocation).where(
            TokenAllocation.mill_id == mill_id,
            TokenAllocation.status == "PENDING"
        ).order_by(TokenAllocation.created_at.desc())
    ).first()
    
    if not allocation:
        return Decimal(0), Decimal(0)
    
    overdue_seconds = (datetime.utcnow() - allocation.created_at).total_seconds()
    overdue_days = max(0, overdue_seconds / 86400)
    
    multiplier = min(2.0, 1.0 + (0.1 * overdue_days))  # Cap at 2.0×
    
    capital_at_risk = Decimal(str(allocation.expected_revenue))
    time_weighted_risk = capital_at_risk * Decimal(str(multiplier))
    
    return capital_at_risk, time_weighted_risk
```

### Decision Impact

**Decision Feed Priority**: Allocations with high `time_weighted_risk` appear first, signaling urgency.

```python
# In get_decision_feed():
priority = (log_comp * 0.7) + (linear_comp * 0.3)  # Weighted log-linear priority
# time_weighted_risk drives both components → stale cycles bubble up
```

---

## 2.9 Effective Rate Forensic Metric (Phase 1 – **implemented**)

### Purpose

Derive **operator's actual revenue per kWh** from cash receipts and energy inputs. This reveals operator behavior (bucket mix, pricing discipline, margin optimization) without enforcing it.

### Formula

```
effective_rate_per_kwh = actual_cash_received / allocated_kwh
```

**Example**:
- Allocated: 59.9 kWh
- Actual remittance: MWK 80,955
- Effective rate: 80,955 ÷ 59.9 = **1,350.3 MWK/kWh**

### Interpretation

**This is NOT an error metric.** It's a *behavioral window*.

| Scenario | Effective Rate | Interpretation |
|----------|----------------|-----------------|
| Operator serving 20L buckets (lower margin) | < budgeted rate | Honest, serving cost-conscious customers |
| Operator serving 5L buckets (higher margin) | > budgeted rate | Honest, serving premium segments |
| Operator hiding bucket mix | ~budgeted rate but no cash reconciliation | Potential fraud flag (see physics layer) |
| Operator siphoning cash | Significantly below budgeted | Leakage detected |

### Data Flow

1. **Logged in every `DecisionBasis`**: Each allocation decision includes the effective rate from the previous cycle
2. **Computed from most recent**: `actual_cash_received` from latest `CashReceipt` + `allocated_kwh` from latest `TokenAllocation`
3. **Optional field**: `DecisionBasis.effective_rate_per_kwh: Optional[Decimal]` (None if no prior cycle or no receipt)

### Audit Trail

Every decision_basis audit entry includes:

```json
{
  "mill_id": "NABIWI_01",
  "decision_log_timestamp": "2026-04-14T10:30:00Z",
  "decision_basis": {
    "capital_at_risk": "80865.00",
    "time_weighted_risk": "80865.00",
    "effective_rate_per_kwh": "1350.3",
    "cycle_state": "PENDING",
    "trust_score": 95,
    ...
  }
}
```

### Nabiwi Calibration (Ground Truth)

**Analysis of Feb–Mar 2026 SMS logs** (27 cycles, 591 buckets reported):

| Metric | Value | Source |
|--------|-------|--------|
| **Average effective rate** | 1,350.0 MWK/bucket | 19 cycles with explicit rate |
| **Variance** | ±0.0% | 100% pricing discipline across 37 days |
| **No bucket-mix leakage** | Confirmed | Rate stable across 60/40/33/22 bucket days |
| **Fraud risk** | LOW | All indicators clean: pricing discipline 100%, deductions transparent, meter-to-cash alignment perfect |

**Action**: Set Nabiwi observation band at **1,340–1,360 MWK/kWh** (±0.75% tolerance based on actual variance).

---

## 2.10 Per-Mill Observation Protocol (Phase 1 – **implemented**)

### Context

Different mills have different operator behavior, bucket mix strategies, and customer bases. A universal enforcement band would cause false alarms on mills with legitimate pricing variations.

**Decision**: Collect 5–10 baseline cycles per mill BEFORE applying tight enforcement bands.

### Workflow

**Phase: Observation (Week 1–2)**

1. Deploy system with idempotency + time-weighted risk + effective rate tracking (no enforcement changes)
2. Observe 5–10 cycles per mill in parallel
3. For each cycle:
   - Log `effective_rate_per_kwh` in decision_basis
   - Export audit trail: `SELECT * FROM decision_audit WHERE mill_id = 'MILL_X' ORDER BY timestamp DESC`
   - Flag if effective rate falls outside Phase 1 conservative band (1,100–1,500)

4. **After 5–10 cycles**:
   - Calculate mill-specific band: `median ± 2 standard deviations`
   - Document findings (per-mill baseline report)
   - Move to enforcement phase for that mill

**Example: Nabiwi (already calibrated)**

- After 37 days of SMS logs + Q1 2026 data: band = **1,340–1,360**
- Observation complete; ready for enforcement
- Any future cycle outside band → flag for review

**Example: Mkwinda (new mill, week 2)**

- Deploy system, observe 10 cycles
- Cycles report (hypothetically): 1,210, 1,198, 1,225, 1,200, 1,188, 1,215, 1,205, 1,220, 1,195, 1,210 MWK/bucket
- Band = 1,200 ± 20 = **1,180–1,220** (tighter than Phase 1 default)
- From week 3 onwards: flag if rate falls outside [1,180–1,220]

### Key Principles

- **Observation first, enforcement second**: No blocking until baseline established
- **Per-mill basis**: Each mill gets its own band based on actual data, not global assumption
- **Forensic film validates**: After 10–15 cycles, conduct manual field observation (bucket count, cash handling) to validate effective_rate band
- **Progressive tightening**: If fraud detected during forensic film, tighten band further or escalate

### UI/Reporting

**Decision Feed shows**:
- Mill ID
- Current effective_rate_per_kwh (from last cycle)
- Observation band (if in observation phase)
- **Status**: "OBSERVING" vs. "ENFORCING"

**Exports**:
- Per-mill baseline report (HTML): effective rate histogram, band recommendations, risk assessment
- Audit trail (CSV): timestamp, effective_rate_per_kwh, capital_at_risk, time_weighted_risk

### Transition to Enforcement

Once 5–10 cycles collected and forensic film completed:

1. Lock mill-specific band in `MillObservationConfig` table
2. Set `enforcement_status = "ACTIVE"`
3. From next cycle: any out-of-band rate → automatic decision_basis.reason = "EFFECTIVE_RATE_ANOMALY" (flag for review, no blocking yet)
4. After 2–3 flagged cycles: escalate to enforcement (reduce allocation or block)

---

### Layer 3: Economic & physical verification layer

This layer provides reality constraints beyond self-reported data.

#### 3.1 Economic constraint engine – Dynamic Credit Envelope (DCE) (**implemented**)

Status:

- Capital Controls module fully implemented and integrated
- Dynamic Credit Envelope (DCE) calculated for all mills
- EAR-based tier classification applied to credit decisions

Function:

- Calculates maximum financeable credit amount
- Enforces economic feasibility constraints
- Adjusts terms based on EAR tier classification

Strategic role:

This is the system's primary defense against consistent spoofing, over-reported production, and unreliable operators through automated economic enforcement.

Implementation: `backend/capital_controls.py`

Documentation: `CAPITAL_CONTROLS_GUIDE.md`, `BOUNDED_IMPERFECTION_DOCTRINE.md`

#### 3.1a Capital at Risk Handling (**implemented**)

Status: Enforcement layer active for COMPROMISED and SUSPENDED mill states.

Purpose:

- Implement economic consequences when mill financial integrity fails
- Activate capital preservation measures automatically
- Enforce collateral and escrow requirements

Mechanism:

Three enforcement levers activate on COMPROMISED/SUSPENDED state transition:

1. **Advance Rate Reduction** — reduces available credit multiplier per risk profile
2. **Collateral/Escrow Requirement** — requires higher security deposit
3. **Manual Audit Requirement** — blocks automated credit decisions

Implementation: `backend/capital_at_risk.py`

Documentation: `CAPITAL_AT_RISK_GUIDE.md`

#### 3.2 Physical anchor layer (indicative verification)

Mechanism:

- reconciliation cycles (`run_daily_recon`)
- manual `physical_reading` input

Validation rule:

- `physical_consumed ≈ reported_consumed ± tolerance`

Current limitation:

- no direct integration with smart-meter / prepaid-meter APIs
- physical readings are externally supplied

Operational protocol (recommended):

- timestamped meter photos
- seal ID verification
- random audit enforcement

Classification:

- probabilistic verification layer (non-deterministic)

#### 3.3 Forensic & statistical engine (**implemented**)

Function:

- Detects long-term inconsistencies through pattern analysis

Detection signals:

- energy-to-output efficiency anomalies
- revenue vs consumption divergence
- low-variance (“too perfect”) reporting
- cross-period inconsistencies

Output:

- risk scores
- fraud likelihood indicators
- operator integrity profiles

Role:

Converts repeated deception into statistically detectable patterns.

#### 3.3.1 Forensic Baseline Standardization (**implemented**)

Status: Phase 2 Forensic Audit (Node 02 – Nabiwi) complete.

Purpose:

- Transition from audit estimates to forensically-verified baselines
- Enforce single source-of-truth for credit decisions
- Maintain historical context for transparency and audit trail

Mechanism:

- Central constants define verified vs. historical metrics per node
- API responses return verified baseline as primary field + historical note as disclosure
- DCE calculations use ONLY verified reconciliation records, never estimates

Implementation:

Location: `backend/api_reports.py` (constants), `backend/capital_controls.py` (constraint enforcement)

**Phase 2 Forensic Audit Constants** (Node 02 – Nabiwi):

**Verified Post-System Era** (current operator accountability):
- NABIWI_VERIFIED_LEAKAGE = 6,833 kWh (89 gap days, metered + reported reconciliation)

**Prior Operator Attribution** (certain but pre-dates current operator):
- NABIWI_PRIOR_OPERATOR = 5,701 kWh (zero production events submitted, ESCOM records sovereign)

**Historical Context** (trend analysis only):
- NABIWI_HISTORICAL_ESTIMATE = 10,991 kWh (both eras combined)

**Attribution Clarification**:

The 6,833 kWh is verified through metering + reporting records during current operator's tenure (active reporting era with 89 gap days). The 5,701 kWh is *certain* (ESCOM metering is sovereign) but attributed to prior operator in pre-system period when zero production events were submitted. These are not both "verified" in the same sense: 6,833 is verified through *dual sources* (metering + reporting discrepancy), while 5,701 is certain but *pre-operator*. Excluding 5,701 from current operator's accountability is legally and fiducially correct.

**DCE Constraint**:

DCE = α × VR × EAR × (1 − RiskPenalty) calculation uses **ONLY verified post-system inputs**:
- VT (Verified Throughput) sourced from current operator's reconciliation records
- EAR (Energy Accountability Ratio) from current operator's verified metering data
- Never uses prior-operator allocations or historical estimates in credit decisions

Rationale:

Credit obligations require forensically defensible numbers tied to accountable party. The 6,833 kWh verifies current operator's energy accountability. The 5,701 kWh is pre-system and thus outside current operator's accountability window. Mixing eras or allocations creates legal and fiduciary exposure.

API Integration:

Example response from `GET /api/v1/mills/{mill_id}/performance`:
```json
{
  "total_hidden_energy_verified_kWh": 6833,
  "historical_estimate_note": "Includes lower-confidence historical periods totaling 10,991 kWh."
}
```

Documentation:

- Comprehensive framework: `FORENSIC_BASELINE_NODE02.md`
- Module constraint: documented in `capital_controls.py` docstring

#### 3.3.2 EAR Tier Classification – Bounded Imperfection Doctrine (**implemented**)

Status: Three-tier classification system deployed across capital controls pipeline.

Purpose:

- Replace unrealistic "EAR must equal 1.0" requirement with operational realism
- Recognize that metering systems, physical losses, and operational discrepancies are normal
- Map EAR ranges to specific credit tiers with proportional financing adjustments

Mechanism:

- EAR (Energy Accountability Ratio) calculated from: `EAR = reported_kwh / metered_kwh`, clipped to [0, 1]
- Three classification tiers based on bounded ranges
- Each tier maps to specific DCE multiplier, credit eligibility, and monitoring requirements

**Three-Tier Classification**:

| Tier | EAR Range | DCE Multiplier | Credit Tier | Eligibility |
|------|-----------|---|---|---|
| **TIER 1** | EAR ≥ 95% | 1.00 | FULL_CREDIT_UNLOCK | Institutional financing, optimal terms |
| **TIER 2** | 90% ≤ EAR < 95% | 0.95 | CONDITIONAL_FINANCEABLE | Commercial financing, standard terms, quarterly monitoring |
| **TIER 3** | EAR < 90% | 0.80 | RESTRICTED | Subprime/restricted financing, immediate investigation |

Implementation:

Location: `backend/ear_thresholds.py`

Core function: `get_ear_tier(ear: float)` returns tier classification with DCE multiplier

**Integration Points**:
- `backend/capital_controls.py` — applies DCE multiplier in credit calculations
- `backend/api_reports.py` — returns tier classification in mill performance summary
- `backend/trust_scorecard.py` — incorporates tier in creditworthiness scoring

**DCE Application**:
```
DCE = α × VR × EAR × (1 − RiskPenalty) × tier_multiplier

Where:
  tier_multiplier = 1.00 (TIER 1), 0.95 (TIER 2), or 0.80 (TIER 3)
```

Rationale:

- Tier 1 (≥95%): Metering accuracy within ±0.5-1% normal range; no penalty
- Tier 2 (90-95%): Within 1-5% normal system loss range; 5% DCE penalty reflects elevated monitoring cost
- Tier 3 (<90%): Material discrepancies exceeding normal loss range; 20% DCE penalty and investigation required

Documentation:

- Comprehensive framework: `BOUNDED_IMPERFECTION_DOCTRINE.md`
- Integration guide: `CAPITAL_CONTROLS_GUIDE.md`

#### 3.3.3 Monitoring Gaps: Specific Energy Consumption (SEC) Deferred

Status: Specified but not currently implemented; deferred based on signal strength analysis.

Specification:

SEC (kWh per unit of production output) was identified as a forensic signal during v2.3 architecture review. The concept is sound: consistent manipulation of production figures requires either:
- Coordinated over-reporting of units (detectable via SEC drift), or
- Sophisticated equipment tampering (changes energy/production ratio)

Rationale for Deferral:

The Nabiwi operational data shows that SEC signal strength is currently insufficient to warrant implementation:
- Observed SEC ratio (kWh per unit) is near-perfect: 1:1 with std = 0.032
- This extremely low variance indicates highly consistent production equipment
- The signal-to-noise ratio is too low to detect manipulation above natural equipment variance
- Alternative signals (EAR, variance breach, event completeness) are more discriminating on current data

Path Forward:

- **Monitor for signal emergence**: If Nabiwi SEC variance increases to std > 0.5 (reflecting equipment aging, degradation, or operational changes), SEC monitoring becomes valuable
- **Portfolio application**: If multi-meter analysis reveals operators with higher SEC variance (std > 0.1), SEC tier classification becomes a secondary forensic signal
- **Implementation trigger**: When 3+ nodes show sufficient SEC variance to exceed noise floor, add SEC bounded-range logic (similar to EAR tiers)

Current Equivalent:

EAR (Energy Accountability Ratio) subsumes much of SEC's forensic utility on current Nabiwi data because EAR directly captures the metered-vs-reported mismatch regardless of production unit chaos.

---

#### 3.4 Event Completeness Check (**planned**)

Status: Specification defined; implementation pending.

Purpose:

- Detect missing production events when metered energy is present
- Catch the inverse of over-reporting: energy consumed but never reported
- Protect against systematic non-reporting (the "silent shutdown" pattern)

Problem Statement:

Layer 2 validates continuity *within* submitted events; it cannot detect *missing* events. The Nabiwi data shows 89 gap days where energy was metered (ESCOM records) but no production events were submitted at all. This pattern is operationally invisible to current layers unless explicitly named as a constraint.

**Trigger**:
```
IF metered_kWh(window) > 0 AND COUNT(production_events, window) = 0
THEN flag_event_completeness_breach(mill_id, window)
```

Mechanism:

For each reconciliation window:
1. Check if ESCOM meter recorded consumption (metered_kWh > 0)
2. Check if operator submitted any production events (COUNT(events) > 0)
3. If consumption exists but no events, raise completeness breach

Severity:

- Level 3 (like variance breach) — indicates systematic non-reporting
- Triggers immediate audit investigation
- May indicate deliberate data suppression or system failure

Resolution:

Operator must either:
- Submit retroactive event log with attestation + photo evidence
- Provide technical explanation (system outage, meter failure, administrative block)  
- Accept state transition to `UNDER_REVIEW` pending investigation

Implementation Path:

Add to `backend/reconciliation_engine.py` → `run_daily_recon()`

#### 3.5 Temporal Integrity Guard (**planned**)

Status: Cross-cutting specification; implementation pending.

Purpose:

- Detect and warn on clock drift in submitted timestamps
- Protect Merkle window anchoring from timestamp manipulation
- Surface timing anomalies that may indicate spoofing

Problem Statement:

Operators submit event timestamps from mobile devices with no guaranteed NTP synchronization. A 24-hour clock drift is functionally invisible to the system but materially affects which reconciliation window an event belongs to, potentially reordering events or splitting cohesive sequences.

**Temporal Integrity Mechanisms**:

1. **Clock Drift Detection** — Monitor timestamp consistency within operator submissions
   - Flag if operator's clock drifts > 1 hour relative to system time
   - Record drift magnitude in event audit trail

2. **Cross-Event Ordering Check** — Verify temporal ordering within a submitted batch
   - Flag if timestamps are non-monotonic (out-of-order events)
   - Warn if gaps exceed expected cycle duration (e.g., > 25 hours for daily reports)

3. **Merkle Window Boundary Risk** — Alert if timestamps cluster near window boundaries
   - High-precision timestamps at window partition points may indicate deliberate window manipulation
   - Recommend physical audit of events near boundaries

Implementation Path:

Add to `backend/cycle_manager.py` during event ingestion

---

## 3. Forensic anchoring: Merkle windows (**implemented**)

Mechanism:

- implemented in `backend/reconciliation_engine.py`

Events are grouped into reconciliation windows. A Merkle tree is constructed for each window. The Merkle root becomes the cryptographic anchor.

Properties:

- **tamper-evident**: changing, inserting, deleting, or reordering window events changes the root
- **deterministic**: the same ordered window produces the same root
- **auditable**: an auditor can recompute the root from the window’s raw events

Note:

- Merkle proof generation / partial inclusion proofs are not yet implemented as an exported feature in this repository.

---

## 4. Breach & exception handling

### Gap breach

- Trigger: continuity violation  
- Layer: 2  
- Meaning: missing or altered event sequence

### Energy deficit breach (**planned**)

- Trigger: `reported_kwh > purchased_kwh`  
- Layer: 3.1  
- Severity: critical  
- Meaning: reported production exceeds economic capacity

### Variance breach

- Trigger: `|reported - physical| > tolerance`  
- Layer: 3.2  
- Meaning: mismatch between reported and observed consumption

---

## 4.5 Capital Governance: Four-Layer Penalty System

**Purpose**: Enforce capital discipline through graduated, mechanical penalties applied to Dynamic Credit Envelope (DCE) calculations. Each layer targets different failure modes—absolute circuit breakers, mediocrity elimination, long-term underperformance, and continuous behavioral risk.

**Status**: All four layers fully implemented and integrated; 10 starvation tests + 7 integration tests passing.

### Layer 1: Death Zone (Absolute Circuit Breaker)

**Mechanism**: Immediate and total capital blockade at efficiency threshold  
**Trigger**: `if current_efficiency < 50%`  
**Action**: Advance rate → $0 (funding blocked entirely, no exceptions)  
**Recovery**: Improve operational efficiency above 50%  

**Rationale**: Operations with fundamental energy supply dysfunction below minimum viability threshold cannot be salvaged. No amount of trust or historical performance justifies lending when current operations cannot sustain basic functionality.

**Key Property**: Cannot be overridden by trust, cumulative loss, or suspicion scores. Acts as ultimate safety valve.

**Example**:
```
operator efficiency: 45%
trust score: 95/100
suspicion score: 1.0
cumulative loss: none

Action: BLOCKED
Advance rate: $0

Reason: Death zone overrides all other factors
Recovery: Operator must improve efficiency > 50%
```

### Layer 2: Starvation Zone (Mediocrity Killer)

**Mechanism**: Severe penalty for operators with adequate but poor efficiency (50–65%)

**Trigger**: `if 50% ≤ current_efficiency < 65%`  
**Penalty**: `advance_rate = calculated_rate × 0.25` (only 25% of normal calculation)  
**Recovery**: Improve efficiency to 65% or above  
**Duration**: While efficiency remains in 50–65% range

**Rationale**: Eliminates comfortable "plateau" where operators can extract capital indefinitely despite minimal performance. By reducing capital to unsustainable levels (typically $25-50/month on $10k base), operators face binary choice: invest in operational improvement or exit the system.

**Economics**:
- Monthly revenue at 55% efficiency: ~$25 (with $10k capital, $500/month costs)
- Monthly loss: ~$475 (clearly unsustainable)
- Result: Operator hits runway limit in ~21 months or improves to 65%+

**Why 25%?**
- Too high (50%+): Operators camp indefinitely (defeats purpose)
- Too low (10%): Forces immediate exit (loses good-faith improvers)
- At 25%: Revenue drops below typical operating costs, forcing decision within weeks/months

**Why 65% as escape velocity?**
- Rate at 64%: ~$0.044
- Rate at 65%: ~$0.190
- Ratio: 4.3× improvement
- Creates powerful incentive to cross threshold with small efficiency gain

**Example**:
```
operator efficiency: 58% (in starvation zone)
trust score: 80/100
normal calculation: 0.50 × 0.80 × (0.58²) = 0.135
with starvation: 0.135 × 0.25 = 0.034 (only 3.4%)

Monthly revenue on $10k capital: $28/month
Monthly operating cost: $500/month
Monthly loss: -$472/month
Status: UNSUSTAINABLE → Forces operational improvement or exit
```

**Key Property**: Starvation zone penalty is independent of cumulative loss and suspicion penalties; all three stack multiplicatively.

### Layer 3: Cumulative Loss Pressure

**Mechanism**: Persistent penalty based on 30-day rolling average efficiency  
**Trigger**: `if rolling_avg_efficiency < 75%`  
**Penalty**: `dce = base_dce × 0.5` (50% capital reduction)  
**Recovery**: Accumulate 30-day rolling average ≥ 75%  
**Memory**: Penalty persists until recovery metric met

**Rationale**: Captures the pain of repeated underperformance. An operator may have one bad day (caught by death zone if critical), but consistent subpar execution for weeks indicates systemic issues requiring capital restraint.

**Timeline**:
- Rolling avg < 75% detected → immediately applies 0.5× multiplier
- Days of clean operations accumulate
- Once rolling window returns above 75% → multiplier lifts

**Example**:
```
Days 1-30: efficiency 65, 64, 62, 66, 63, ... (all < 75%)
Rolling avg: 70% throughout

Cumulative loss multiplier: 0.5×
Capital impact: 50% reduction (dce = base × 0.5)

Days 31-45: efficiency improves (75, 76, 77...)
Rolling avg trend: 71%, 72%, 73%, 74%, 75% (crosses threshold on day 45)

Result: Multiplier lifts to 1.0×
Capital impact: Reduction removed, full capacity restored
```

**Integration**: Applied via `CapitalControls.cumulative_penalty(mill_id)` in compute_advance_rate()

**Data Source**: 30-day rolling average calculated from daily efficiency in ReconciliationRecord

### Layer 4: Suspicion Score System

**Mechanism**: Continuous accumulation and decay based on behavioral patterns  
**Triggers**:  
  - Variance deviation above 1.5% tolerance: `(variance% - 1.5) / 10.0` points/day  
  - Pattern anomaly detection (entropy, Z-score, breach): 0.5 points/day  
**Daily Decay**: `score × (1 - 0.1)` = 10% daily forgiveness  
**Penalty**: `dce = base_dce × 0.8` when `score ≥ 5.0` (20% capital reduction)  
**Recovery**: 10+ clean days of low variance + no anomalies

**Rationale**: Creates pressure from suspicious activity even without definitive proof. Operators "feel" cost of risky patterns while retaining recovery paths through consistent clean operations.

**Mechanics**:
```
daily_risk = (max(0, variance% - 1.5) / 10.0) + (0.5 if pattern_anomaly else 0)
suspicion_score = suspicion_score × 0.9 + daily_risk
suspicion_score = min(suspicion_score, 10.0)

penalty_multiplier = 0.8 if (suspicion_score ≥ 5.0) else 1.0
```

**Risk Table**:
| Variance | Daily Risk | Pattern | Total Risk | Notes |
|----------|-----------|---------|-----------|-------|
| 1.0% | 0.0 | No | 0.0 | Clean |
| 1.5% | 0.0 | No | 0.0 | At tolerance |
| 2.5% | 0.1 | No | 0.1 | Slight concern |
| 2.5% | 0.1 | Yes | 0.6 | Suspicious (pattern adds 0.5) |
| 3.5% | 0.2 | Yes | 0.7 | Highly concerning |

**Accumulation Example** (18 days suspicious, 12+ days recovery):
```
Days 1-18: variance 2.5%, pattern anomaly daily
Daily risk: 0.6 points/day
Day 1:  score = 0.0 × 0.9 + 0.6 = 0.60
Day 10: score ≈ 3.4
Day 18: score ≈ 5.1 → PENALTY ACTIVATES (0.8×)

Days 19-30: clean operations (variance < 1.5%, no anomalies)
Decay: score = score × 0.9 each day
Day 30: score ≈ 0.56 → PENALTY LIFTS (< 5.0)

Capital: $100k → $80k (day 18–30) → $100k (day 30+)
```

**Integration**: Applied via `CapitalControls.suspicion_penalty(mill_id)` in DCE calculation

**Database**: Persisted in `MillIntegrityState.suspicion_score` with timestamp; loads and decays on restart

### Penalty Stacking & Priority

**Execution Order** (in compute_advance_rate):

```
1. DEATH ZONE CHECK
   ├─ if efficiency < 50% → return 0.0 (BLOCKED)
   └─ continue if efficiency ≥ 50%

2. STARVATION ZONE CHECK
   ├─ if 50% ≤ efficiency < 65% → starvation_mult = 0.25
   └─ else → starvation_mult = 1.0

3. CUMULATIVE LOSS CHECK
   ├─ if rolling_avg < 75% → cumulative_mult = 0.5
   └─ else → cumulative_mult = 1.0

4. SUSPICION SCORE CHECK
   ├─ if score ≥ 5.0 → suspicion_mult = 0.8
   └─ else → suspicion_mult = 1.0

5. FINAL ADVANCE RATE
   rate = base × (trust/100) × (efficiency²) × starvation_mult
   rate = rate × cumulative_mult × suspicion_mult
```

**Example: Multiple Penalties Active**
```
Operator State:
  Efficiency: 58% (in starvation zone)
  Rolling avg: 70% (< 75%, triggers cumulative loss)
  Suspicion score: 4.0 (< 5.0, no suspicion penalty)

Calculation:
  base_rate = 0.50
  starvation_mult = 0.25      (50–65% zone)
  cumulative_mult = 0.5       (rolling < 75%)
  suspicion_mult = 1.0        (score < 5.0)
  
  rate = 0.50 × trust_factor × (0.58²) × 0.25 × 0.5 × 1.0
  rate = 0.50 × 0.80 × 0.3364 × 0.25 × 0.5
  rate = 0.0168 (1.68% of base)

Capital: 96.8% reduction from starvation + cumulative loss combined
```

**Example: All Four Penalties Active** (most severe case)
```
Operator State:
  Efficiency: 58% (starvation zone)
  Rolling avg: 60% (< 75%, cumulative loss active)
  Suspicion score: 6.0 (triggers penalty)

Calculation:
  starvation_mult = 0.25
  cumulative_mult = 0.5
  suspicion_mult = 0.8
  
  Final multiplier = 0.25 × 0.5 × 0.8 = 0.1 (90% reduction)
```

**Recovery Sequence** (from most severe state):
```
Initial: 1.68% rate (starvation + cumulative)
         ↓ (accumulate 12+ clean days)
Suspicion Cleared: varies (still starvation + cumulative)
         ↓ (improve efficiency to 65%+)
Starvation Lifted: varies (only cumulative remains, ~3× better)
         ↓ (rolling avg improves > 75%)
Full Recovery: normal rate (no penalties)
```

### Testing & Validation

**Starvation Zone Test Coverage** (10 tests):
- Death zone (< 50%): blocks entirely ✅
- Starvation lower boundary (50%): 25% multiplier ✅
- Starvation middle (57.5%): 25% multiplier ✅
- Starvation upper boundary (64.99%): 25% multiplier ✅
- Normal zone boundary (65%): no multiplier ✅
- Starvation vs normal ratio: 4.3× improvement at boundary ✅
- Starvation + cumulative loss: stacks multiplicatively ✅
- High efficiency zone (80%+): full scaling ✅
- Economic impact: confirms unsustainability ✅
- Boundary precision: exact at 50% and 65% ✅

**Integration Test Coverage** (7 tests):
- Hard floor priority: blocks even with high suspicion ✅
- Cumulative loss alone: 50% reduction verified ✅
- Suspicion alone: 20% reduction verified ✅
- Combined penalties: 60% reduction (0.5 × 0.8) ✅
- Recovery sequence: $40k → $50k → $100k ✅
- Hard floor override: blocks even if other penalties lift ✅
- DCE calculation: all multipliers applied correctly ✅

**Result**: 17/17 tests passing (10 starvation + 7 integration)

**Documentation**:
- Comprehensive reference: `KILL_THE_FLOOR_SURFERS.md`
- Quick reference: `KILL_THE_FLOOR_SURFERS_QUICK_REF.md`
- Starvation zone tests: `test_starvation_zone.py`
- Integration tests: `test_penalty_integration.py`
- Suspicion score docs: `SUSPICION_SCORE.md`, `SUSPICION_SCORE_QUICK_REF.md`

---


## 5. Data flow summary

Step 1: event submission  
- operator submits signed payload

Step 2: validation pipeline  
- identity verification (Layer 1)  
- continuity check (Layer 2)  
- economic constraint check (Layer 3.1 - capital controls & DCE)

Step 3: reconciliation  
- physical comparison (Layer 3.2)  
- Merkle window anchoring
- EAR tier classification (Layer 3.3.2 - Bounded Imperfection Doctrine)

Step 4: forensic analysis  
- statistical evaluation (Layer 3.3)
- baseline verification (Layer 3.3.1 - Forensic Baseline Standardization)

Step 5: credit assessment & financial controls
- Dynamic Credit Envelope (DCE) calculation
- Capital at Risk (CAR) enforcement
- Trust Scorecard generation

---

## 5.5 Trust Scorecard: Creditworthiness Synthesis

**Purpose**: Aggregate technical audit data (reconciliation, consistency, governance) into a single 0–100 investor-grade metric for credit decisions. Outputs a financing recommendation (APPROVE / CONDITIONAL / DECLINE) based on aggregate integrity.

**Definition**: The Trust Integrity Score synthesizes three audit components with fixed weights:

1. **Reconciliation Score (50% weight, 0–100)**: Physical vs. Ledger integrity. Derived from daily variance: `score = 100 − (variance_pct × 10)`
2. **Consistency Score (30% weight, 0–100)**: Statistical anomaly detection. Flagged events indicate suspicious patterns: `score = 100 − (flagged_events_pct)`
3. **Governance Score (20% weight, 0–100)**: Signature/RBAC enforcement. Rejected signatures penalize governance trust: `score = 100 − (rejected_count × 10)`

**Aggregate Trust Score**:
```
trust_score = (recon_score × 0.50) + (consistency_score × 0.30) + (governance_score × 0.20)
```

Result: 0–100, where 100 = maximum integrity and transparency, 0 = critical breach.

**KPI Outputs** (included for forensic visibility, not recommendation gating):
- `energy_accountability_ratio` (EAR): reported_kwh ÷ metered_kwh
- `reconciliation_variance_pct`: |reported − metered| ÷ metered × 100
- `verified_throughput_kwh`: metered energy (physical anchor)
- `fraud_risk_level`: LOW / MEDIUM / HIGH (derived from trust_score and consistency_score thresholds)

**API Endpoint**:

```json
GET /api/v1/mills/{mill_id}/scorecard

{
  "metadata": {
    "mill_id": "NABIWI_MKWINDA",
    "mill_name": "Mkwinda Solar",
    "date": "2026-03-14",
    "generated_at": "2026-03-14T09:15:00Z",
    "sovereign_anchor": "0x82b3a2c7..."
  },
  "components": {
    "reconciliation_score": 92.1,
    "consistency_score": 88.5,
    "governance_score": 95.0
  },
  "kpis": {
    "trust_integrity_score": 91.3,
    "reconciliation_variance_pct": 0.79,
    "energy_accountability_ratio": 0.92,
    "verified_throughput_kwh": 4104.3,
    "fraud_risk_level": "LOW",
    "event_count": 48,
    "flagged_events": 2
  },
  "capital_impact": {
    "financing_rate_adjustment_bps": -500,
    "financing_rate_adjustment_pct": -5.0,
    "audit_efficiency": "60% Reduction (SOVEREIGN: minimal onsite audits required)",
    "risk_classification": "INSTITUTIONAL GRADE",
    "capital_tier": "Tier 1",
    "max_leverage_ratio": 3.5,
    "recommendation": "APPROVE: Prioritize for growth capital. Lock in favorable terms while SOVEREIGN status holds."
  },
  "investor_verdict": "🟢 SOVEREIGN: Maximum transparency and integrity. Minor discrepancies acceptable under bounded imperfection doctrine."
}
```

Implementation: `backend/trust_scorecard.py`

### 5.5.1 Trust Score vs. EAR Tier Decision Logic

**Architectural Clarification**: The Trust Scorecard recommendation is **NOT gated by EAR tier alone**. Instead, the aggregate trust score (weighted composite of reconciliation, consistency, and governance) drives the credit recommendation. EAR is a forensic KPI that contributes to—but does not unilaterally determine—the final decision.

**Relationship to EAR Tiers (Section 3.3.2)**:

- **EAR Tier Classification** (3.3.2): Categorizes energy accountability into risk bands: TIER 1 (≥95%), TIER 2 (90–95%), TIER 3 (<90%)
- **EAR's Role**: Contributes to reconciliation_score, which is 50% of the aggregate trust_score
- **EAR's Weight in Recommendation**: Indirect — a mill with EAR = 0.88 (TIER 3) can still achieve trust_score ≥ 75 (APPROVE) if reconciliation shows low absolute variance % and consistency_score + governance_score are strong

**Example Scenarios** (illustrating non-gating behavior):

**Scenario A: Low EAR, High Overall Trust (Approved Despite TIER 3)**
```
Mill: NABIWI_MKWINDA
EAR: 0.88 (TIER 3 — below 90% threshold)
variance: 1.2% (low absolute variance, indicating controlled reporting)
flagged_events: 0
rejected_signatures: 0

reconciliation_score = 100 − (1.2 × 10) = 88
consistency_score = 100 − 0 = 100
governance_score = 100 − 0 = 100
trust_score = (88 × 0.50) + (100 × 0.30) + (100 × 0.20) = 89

Recommendation: APPROVE (standard commercial terms)
Rationale: Low absolute variance signals controlled, consistent reporting. EAR 0.88 reflects 
equipment characteristic (not manipulation) under bounded imperfection doctrine. Other integrity 
signals (zero flagged events, perfect governance) offset TIER 3 classification.
```

**Scenario B: Respectable EAR, Low Overall Trust (Declined Despite TIER 2)**
```
Mill: HYPOTHETICAL_OPERATOR
EAR: 0.92 (TIER 2 — 90–95% range)
variance: 8.5% (high absolute variance, indicating inconsistent reporting)
flagged_events: 15 (statistical anomalies detected)
rejected_signatures: 2 (governance failures)

reconciliation_score = 100 − (8.5 × 10) = 15
consistency_score = 100 − 15 = 85
governance_score = 100 − (2 × 10) = 80
trust_score = (15 × 0.50) + (85 × 0.30) + (80 × 0.20) = 48

Recommendation: DECLINE
Rationale: High absolute variance and consistency flags indicate systematic manipulation risk. 
Despite respectable TIER 2 EAR ratio, the operational pattern (inconsistency + governance 
failures) exceeds lending appetite. EAR cannot override integrity concerns.
```

**Decision Thresholds** (based on trust_score alone):

| Trust Score | Recommendation | Monitoring | Collateral | Rationale |
|---|---|---|---|---|
| ≥ 90 | APPROVE (Sovereign) | Minimal audits | Standard | Maximum transparency; favorable capital terms |
| 75–89 | APPROVE (Commercial) | Quarterly | Standard | Standard commercial terms; monitor trends |
| 60–74 | CONDITIONAL | Monthly | Elevated/Escrow | Lender defines monitoring, term adjustments, remediation window |
| < 60 | DECLINE | N/A | N/A | Risk exceeds institutional appetite; remediation required before reapplication |

**Implementation Note**: Each lender may layer additional EAR-based portfolio policies (e.g., "maximum 30% TIER 3 mills in portfolio"), but the Trust Scorecard recommendation itself applies no hard EAR gate.

**State Transitions**:

- **VERIFIED**: trust_score ≥ 90, recon_score ≥ 95 → eligible for maximum advance rate and minimal auditing
- **UNDER_REVIEW**: trust_score 75–89 → standard commercial terms; quarterly monitoring  
- **COMPROMISED**: trust_score 60–74 → manual review required; elevated monitoring; possible collateral/escrow
- **SUSPENDED**: trust_score < 60 → no new credit; remediation required before re-application

---

## 6. System guarantees

GridLedger guarantees:

- tamper-evident records (Layer 1)
- detection of discontinuities (Layer 2)
- detection of economically impossible production (Layer 3.1 - DCE/Token Gap enforcement)
- long-term anomaly detection (Layer 3.3)
- credit tier classification based on operational realism (Layer 3.3.2 - EAR Tiers)
- forensic baseline standardization for credit defensibility (Layer 3.3.1 - Verified Baselines)
- automated capital preservation when integrity fails (Layer 3.1a - Capital at Risk)
- transparent creditworthiness assessment (Trust Scorecard)

GridLedger does **not** guarantee:

- real-time fraud prevention
- independent physical measurement
- immediate detection of consistent spoofing

---

## 7. Positioning statement

GridLedger is not a monitoring system. It is a **constraint-based verification protocol for energy-constrained infrastructure**.

Functional shift:

From: “Is this data accurate?”  
To: “Could this data be true under known constraints?”

---

## 8. Strategic implication

By combining:

- identity (Layer 1)
- continuity (Layer 2)
- economic constraint (Layer 3.1)
- physical & forensic anchors (Layer 3.2 / 3.3)

GridLedger creates a system where false reporting is not prevented, but becomes economically, physically, and statistically unsustainable over time.

---

## 9. Enforcement & response model

Detection without consequence is theater. GridLedger is designed to **detect, classify, escalate, and penalize** integrity failures in a way that maps to operational and financial controls.

This section defines:

- breach severity levels
- mill/node state transitions
- enforcement actions (operational + economic)
- audit trigger logic

### 9.1 Breach severity classification

#### Level 1 — Informational

Examples:

- minor variance within tolerance band
- isolated low-signal anomalies

System response:

- logged only
- no change to mill/node operating state

#### Level 2 — Warning

Examples:

- repeated small inconsistencies over a short period
- approaching an economic ceiling (future Token Gap “near-threshold” alert)
- elevated statistical suspicion that does not cross a hard block threshold

System response:

- flag operator / mill for increased scrutiny
- increase audit frequency (see 9.4)
- tighten tolerances for review workflows (policy-controlled)

#### Level 3 — Breach

Examples:

- any gap breach (Layer 2 continuity violation)
- variance beyond tolerance (Layer 3.2)

System response:

- mark the affected reconciliation window / period as **compromised**
- require external verification to restore “verified” status (photo + supervisor, or site visit)
- increase governance scrutiny for subsequent submissions from the same operator/mill

#### Level 4 — Critical breach (**future: Token Gap hard enforcement**)

Examples:

- energy deficit breach: reported kWh exceeds purchased kWh beyond tolerance (Layer 3.1)
- repeated Level 3 breaches within a bounded horizon

System response:

- freeze validation status (no “verified” outputs until resolved)
- flag operator/mill as **high risk**
- trigger financial review (credit committee / lender-side controls)

### 9.2 Mill/node state transitions

Each mill/node is treated as a state machine. States are designed to be understandable by auditors and actionable by lenders.

States:

- **Verified**
- **Under Review**
- **Compromised**
- **Suspended**

Example transition chain:

`Verified → Under Review → Compromised → Suspended`

Recommended transition logic (policy):

- **Verified → Under Review**
  - 2× Level 2 warnings within 7 days, or 1× Level 3 breach
- **Under Review → Compromised**
  - any gap breach, or 2× variance breaches within 7 days
- **Compromised → Suspended**
  - repeated breaches without remediation, or any Level 4 critical breach (future)
- **Compromised/Suspended → Verified**
  - requires documented remediation + external verification evidence for the affected periods

Implementation note:

- The repository currently encodes some outcomes as statuses (e.g., reconciliation status `SOVEREIGN` / `UNDER_REVIEW`, ingestion statuses like `FLAGGED_SUSPICION`) and purchase gating. A full state-transition engine is the planned consolidation of these signals into explicit mill states.

### 9.2.1 Mapping to current implementation (signals → states/actions)

This table maps the enforcement model to concrete signals already present in the repository.

| Model concept | Current signal(s) in repo | Where it comes from | Notes |
|---|---|---|---|
| **Gap breach (Level 3)** | `GapBreachError` raised | `backend/authority_engine.py` → `check_gap_breach_event()` | Triggered by `previous meter_close != current meter_open` in sequential `EventLog` payloads. |
| **Variance breach (Level 3)** | reconciliation status `UNDER_REVIEW` | `backend/reconciliation_engine.py` → `run_daily_recon()` | Driven by `variance_pct > tolerance_pct`; depends on externally sourced `physical_reading`. |
| **Verified state (target)** | reconciliation status `SOVEREIGN` | `backend/reconciliation_engine.py` | “Verified” in this model corresponds to consistently low-variance physical anchoring plus no severe governance flags. |
| **Under Review (state)** | reconciliation status `UNDER_REVIEW` | `backend/reconciliation_engine.py` | Today this is the closest explicit state marker; a full mill state machine is not yet persisted. |
| **Warning (Level 2)** | `EventLog.status == "FLAGGED_SUSPICION"` | `backend/cycle_manager.py` → `ingest_event()` + `backend/consistency_engine.py` | Set when suspicion scoring crosses threshold during ingestion. |
| **Governance failures** | `EventLog.status in {"REJECTED_SIGNATURE","REJECTED_REPLAY"}` | `backend/cycle_manager.py` → `ingest_event()` + `backend/identity_manager.py` | These are integrity/identity failures; in enforcement terms they should accelerate escalation. |
| **Token gating (economic control surface)** | `can_purchase_token(mill_id) == False` | `backend/cycle_manager.py` → `can_purchase_token()` / `reconcile_cycle()` | Current “teeth”: blocks token purchase when the cycle is `BLOCKED`. Not the same as Token Gap feasibility enforcement. |
| **Energy deficit breach (Level 4)** | `EventLog.status == "FLAGGED_ECONOMIC_DEFICIT"` | `backend/enforcement_engine.py` → `check_economic_ceiling()` | Triggered when reported kWh exceeds purchased kWh units + tolerance. |
| **Audit trigger outputs** | human-readable alerts / operational prompts | `backend/ingest_report.py` | Currently emits text prompts (e.g., “AUDIT ALERT… Code 003”) but not a structured audit-workflow engine. |

### 9.3 Pre-PXE Conceptual Model (Deprecated)

⚠️ **Deprecation Notice**: This section describes the previous interpretive enforcement model. It has been superseded by Policy Execution Engine (Section 10), which provides deterministic, non-negotiable capital enforcement.

The old model relied on human-in-the-loop interpretation:
- Breach detection → financial consequence (interpretive, lender-discretionary)
- State transitions → policy adjustments (manual, subjective)
- Outcome execution → variable implementation (drift across lenders)

PXE (Section 10) replaces this with:
- Detection → Classification → Deterministic Policy Execution → Immutable Capital Action
- No interpretation layer
- No manual override
- Identical inputs → Identical financial outcomes

**Legacy Reference** (retained for historical context):

The old consequence levers that informed PXE design:
- Creditworthiness score adjustment on breach events
- Token financing eligibility caps in Under Review state
- Collateral/escrow requirements for Compromised state
- Manual audit sign-off before credit release in Suspended state

All of these are now encoded as deterministic rules in PXE policies.

---

### 9.3a CONDITIONAL Enforcement Bridge

**Current State**: CONDITIONAL recommendations are not auto-enforced; lender policy fills the gap.

**⚠️ Gap Acknowledged**: For sophisticated capital providers, discretionary enforcement is a known limitation — it means outcomes are not fully reproducible across lenders. This is the only point in the system where determinism breaks.

**Committed Delivery**: The Lender Policy Module encoding CONDITIONAL as executable deterministic rules is targeted for delivery within **90 days of first Glass Box certification at NABIWI**. Until that date, lenders must implement CONDITIONAL rules manually in their credit policy framework.

**Interim Lender Protocol**:

```
Rule: CONDITIONAL_COMMERCIAL
IF (score >= 60 AND score < 75) OR state = "Under Review"
THEN {
  monitoring: "monthly",
  tenor_adjustment: "-60_days",
  advance_rate_cap: "0.50",
  collateral_ratio: "1.35",
  remediation_window: "90_days"
}
```

### 9.3b Portfolio-Level Anomaly Detection

**Status: Evidentially demonstrated; implementation in active development.**

> **This is not a theoretical specification. The system already has evidence that portfolio-level signals exist and are operationally significant.**

**The June 2025 Event (NABIWI, six-meter cluster)**:

In June 2025, a synchronised six-hour blackout was recorded across four Nabiwi meters simultaneously. Evaluated per-meter, this is coincidence. Evaluated at portfolio level, it is a coordinated signal. No single-meter analysis layer in the current architecture would have surfaced this pattern. It was identified through manual cross-meter review — which is precisely the gap this module closes.

This event is the evidential basis for portfolio anomaly detection. It is not a hypothetical. It happened.

**Portfolio Trigger**:
```
IF 2+ meters show (same event type, overlapping time window, similar magnitude)
  AND NOT EXISTS (known_outage_event covering window)
THEN raise_portfolio_anomaly_flag(operator_id, correlation_score)
```

**False-Positive Suppression**: Cross-reference against ESCOM outage registry before escalating. Missing registry entry → Level 2 flag (human review), not auto-escalation.

**Implementation**: `backend/portfolio_engine.py` — active development, target completion Phase 2.

### 9.4 Audit trigger logic

Audit triggers define when the system forces out-of-band verification.

**Recommended triggers**:

**Layer-based**:
- any gap breach (Layer 2) — missing or reordered events
- any variance breach (Layer 3.2) beyond tolerance — metered ≠ reported mismatch
- 2× variance breaches within 7 days — repeated physical inconsistencies
- 2× Level 2 warnings within 7 days — consistency anomalies
- any energy deficit breach (Layer 3.1) — reported > purchased + tolerance
- any event completeness breach (Layer 3.4) — metered energy with zero production events

**Temporal/Operator**:
- temporal integrity warnings (Layer 3.5) — clock drift > 1 hour or timestamp ordering anomaly
- portfolio-level anomaly (Section 9.3b) — coordinated multi-meter pattern

**Trust Scorecard**:
- state transition to UNDER_REVIEW or Compromised
- score decline > 15 points within 30 days
- CONDITIONAL or DECLINE recommendation

**Required actions**:
- physical inspection OR supervisor verification
- timestamped meter photo capture (opening/closing faces, meter ID, dial reading)
- seal integrity check — broken/missing seal triggers Level 4 critical breach
- temporary data hold (no new credit decisions until cleared)
- operator interview (document system outages, technical issues, explanations)

---

## 10. Policy Execution Engine (PXE) — Layer 4

**Position in Architecture**:
```
Layer 1: Identity (Ed25519 signatures)
Layer 2: Continuity (event ordering & gaps)
Layer 3: Verification (economic, physical, forensic constraints)
Layer 4: Policy Execution (PXE) ← Deterministic Capital Enforcement
```

**System Purpose**:

PXE converts verified system state into irreversible financial actions.

It is the execution layer that binds capital behavior to constraint-verified reality.

**Core Principle: Deterministic Capital Mapping**

```
Financial Outcome = f(Verified State)

Where:
  f = policy function (pure, no side effects)
  inputs = fully auditable and signed
  outputs = non-negotiable, immutable Capital Action Objects
```

**Design Absolutes**:

- ✅ Inputs must originate from Layer 1–3 (signed, timestamped, Merkle-anchored)
- ✅ All policies expressed as pure deterministic functions (no fuzzy language, no discretion)
- ✅ Identical inputs → Identical outputs (reproducible, auditable)
- ✅ No human interpretation allowed inside execution
- ✅ No manual override of policy outcomes

### 10.1 Per-Cycle Token Allocation (Block 8) — Adherence-Based Capital Enforcement

---

## 11. API Reference (Phase 1 – April 2026)

All owner endpoints require the `X-API-Key` header for authentication.

### 11.1 GET /api/owner/decision-feed

**Purpose**: Actionable feed of mills sorted by economic urgency.

**Request**:
```bash
curl -X GET http://localhost:8000/api/owner/decision-feed \
  -H "X-API-Key: owner-secret"
```

**Response** (200 OK):
```json
[
  {
    "mill_id": "NABIWI_01",
    "issue": "PENDING_NEAR_TIMEOUT",
    "urgency": "HIGH",
    "capital_at_risk_mwk": 80865.00,
    "time_weighted_risk_mwk": 121297.50,
    "remaining_hours": 4.5,
    "priority": 42.7,
    "action": "Review pending allocation; operator should submit receipt"
  }
]
```

**Sorting**: Hybrid log-linear priority (combines log component for scale-insensitivity with linear component for extreme values).

---

### 11.2 GET /api/owner/mills/{mill_id}/decision

**Purpose**: Individual mill decision basis (includes effective_rate forensic metric).

**Request**:
```bash
curl -X GET http://localhost:8000/api/owner/mills/NABIWI_01/decision \
  -H "X-API-Key: owner-secret"
```

**Response** (200 OK):
```json
{
  "allowed": true,
  "reason": null,
  "decision_basis": {
    "mill_id": "NABIWI_01",
    "cycle_state": "PENDING",
    "trust_score": 95,
    "adherence": 100.1,
    "lag_hours": 12.3,
    "capital_at_risk": "80865.00",
    "time_weighted_risk": "94208.25",
    "exposure_used": "80865.00",
    "exposure_limit": "500000.00",
    "effective_rate_per_kwh": "1350.3",
    "decision_timestamp": "2026-04-14T10:30:45Z"
  }
}
```

**Key Fields**:
- `effective_rate_per_kwh`: Forensic metric derived from previous cycle's cash receipt. Reveals operator bucket mix behavior. Compared against mill-specific observation band (e.g., Nabiwi: 1,340–1,360).
- `time_weighted_risk`: Capital at risk adjusted for allocation age. Stale cycles have higher risk multiplier.
- `cycle_state`: "IDLE" (ready for new allocation), "PENDING" (awaiting receipt), or "MISSING" (overdue).

---

### 11.3 POST /api/owner/mills/{mill_id}/allocate-token

**Purpose**: Create new token allocation (59.9 kWh) with idempotency guarantee.

**Required Header**: `Idempotency-Key`
- UUID format (e.g., `550e8400-e29b-41d4-a716-446655440000`)
- Identical Idempotency-Key + same mill_id = guaranteed identical response
- Safe to retry indefinitely without creating duplicate allocations

**Request**:
```bash
curl -X POST http://localhost:8000/api/owner/mills/NABIWI_01/allocate-token \
  -H "X-API-Key: owner-secret" \
  -H "Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json"
```

**Response** (200 OK):
```json
{
  "allowed": true,
  "allocation_id": 12345,
  "allocated_kwh": 59.9,
  "expected_revenue_mwk": 80865.00,
  "decision_basis": {
    "mill_id": "NABIWI_01",
    "cycle_state": "IDLE",
    "capital_at_risk": "80865.00",
    "time_weighted_risk": "80865.00",
    "effective_rate_per_kwh": "1350.3",
    "decision_timestamp": "2026-04-14T10:31:00Z"
  }
}
```

**Idempotency Behavior**:

*First request*:
```bash
curl -X POST http://localhost:8000/api/owner/mills/NABIWI_01/allocate-token \
  -H "Idempotency-Key: 550e8400-..."
# → Creates allocation ID 12345, stores response
```

*Retry (within 24 hours with same header)*:
```bash
curl -X POST http://localhost:8000/api/owner/mills/NABIWI_01/allocate-token \
  -H "Idempotency-Key: 550e8400-..."
# → Returns cached response, allocation ID still 12345, no duplicate
```

*Different Idempotency-Key*:
```bash
curl -X POST http://localhost:8000/api/owner/mills/NABIWI_01/allocate-token \
  -H "Idempotency-Key: 660f9511-..." 
# → Creates new allocation ID 12346 (different key = new allocation)
```

**Error Response** (400 Bad Request):
```json
{
  "allowed": false,
  "reason": "CYCLE_PENDING",
  "detail": "Mill NABIWI_01 already has pending allocation (ID 12345). Previous cycle must be completed before next allocation."
}
```

---

### 11.4 POST /api/owner/mills/{mill_id}/record-cash-receipt

**Purpose**: Record operator's cash remittance (closes current cycle).

**Request**:
```bash
curl -X POST http://localhost:8000/api/owner/mills/NABIWI_01/record-cash-receipt \
  -H "X-API-Key: owner-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "allocation_id": 12345,
    "amount_mwk": 80955.00,
    "notes": "SMS from operator: pa 14.4.26 Open 60 Close 0 Ndagayil 60 Units Amount 80955 Late 1350"
  }'
```

**Response** (200 OK):
```json
{
  "receipt_id": 987654,
  "allocation_id": 12345,
  "status": "CLOSED",
  "variance_percent": 0.11,
  "effective_rate_per_kwh": 1350.3,
  "resolution_needed": false,
  "decision_basis": {
    "mill_id": "NABIWI_01",
    "effective_rate_per_kwh": "1350.3",
    "decision_timestamp": "2026-04-14T10:35:22Z"
  }
}
```

**Effective Rate Calculation** (in response):
```
effective_rate_per_kwh = 80955.00 / 59.9 = 1350.3 MWK/kWh
```

This is logged in the next cycle's `decision_basis` for forensic tracking.

---

### 11.5 Effective Rate Observation (Phase 1)

**Key Principle**: Effective rate is logged but NOT enforced in Phase 1. It's a forensic window.

**Expected Behavior: Nabiwi** (calibrated for observation band 1,340–1,360):

```
Cycle 1: effective_rate_per_kwh = 1,350.1 ✅ Within band
Cycle 2: effective_rate_per_kwh = 1,349.8 ✅ Within band
Cycle 3: effective_rate_per_kwh = 1,350.5 ✅ Within band
Cycle 4: effective_rate_per_kwh = 1,290.0 ⚠️ Below band (anomaly, review)
Cycle 5: effective_rate_per_kwh = 1,350.2 ✅ Back to normal
```

**Action**: No blocking in Phase 1. Anomalies are flagged in audit trail and reported in decision_feed.

**After 5–10 cycles**: Move to enforcement (add decision rule: if effective_rate outside band → REDUCE allocation or flag for review).

---

### 11.6 Authentication & Configuration

**Environment Variables**:

```bash
export OWNER_API_KEY="owner-secret"              # Required for /api/owner/* endpoints
export SYSTEM_ALLOCATION_ENABLED="true"           # Enable token allocation logic
export GRIDLEDGER_API_KEY="letmein123"            # Optional fallback for other endpoints
```

**Headers**:

| Header | Required | Example | Purpose |
|--------|----------|---------|---------|
| `X-API-Key` | Yes | `owner-secret` | Authentication (matches OWNER_API_KEY env var) |
| `Idempotency-Key` | For allocate-token | `550e8400-e29b-41d4-a716-446655440000` | Deduplication; safe retries |
| `Content-Type` | Optional | `application/json` | Request format |

---

### 11.7 Lifecycle Example: One Complete Cycle

**Day 1, 10:00 AM — Allocation**:
```bash
curl -X POST http://localhost:8000/api/owner/mills/NABIWI_01/allocate-token \
  -H "X-API-Key: owner-secret" \
  -H "Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000"
# → allocation_id: 12345, expected_revenue: 80,865 MWK
```

**Day 1, 6:00 PM — Operator produces and sends SMS with cash amount**:

*Operator SMS* (via WhatsApp):
```
Pa 1.4.26 Open 60 Close 0 Ndagayil 60 Units Amount 80955 Late 1350 Ma Units Atha
```

**Day 1, 6:15 PM — Record Receipt**:
```bash
curl -X POST http://localhost:8000/api/owner/mills/NABIWI_01/record-cash-receipt \
  -H "X-API-Key: owner-secret" \
  -d '{"allocation_id": 12345, "amount_mwk": 80955, "notes": "SMS receipt"}'
# → receipt_id: 987654, status: CLOSED, variance: +0.11%, effective_rate: 1350.3
```

**Day 2, 10:00 AM — Next Allocation Decision**:
```bash
curl -X GET http://localhost:8000/api/owner/mills/NABIWI_01/decision
# → decision_basis includes effective_rate_per_kwh: 1350.3 (from prior cycle)
# → Compared against Nabiwi observation band [1,340–1,360]: ✅ In band
# → Next allocation: ALLOWED
```

---

This completes the Phase 1 system architecture: identity + continuity + effective rate forensics + per-mill observation protocol, enabled by idempotency and time-weighted risk.


**Component Overview**:

The per-cycle allocation system implements deterministic capital rationing based on historical cycle adherence, enforcing conservative advance rates on mills with payment delays or disputes.

See [PER_CYCLE_ALLOCATION_REFERENCE.md](PER_CYCLE_ALLOCATION_REFERENCE.md) for complete operational documentation (state machine, integration checklist, configuration constants).

**Architecture Layers** (Block Components):

| Block | Component | Purpose | Location |
|-------|-----------|---------|----------|
| 1-2 | Latency Penalty | Transform hours-since-allocation into stepwise multiplier (1.00 → 0.85) | `policy_execution_engine.py:241-389` |
| 3 | Configuration | Centralize boundaries, timeouts, penalty thresholds | `config.py:27-34` |
| 4 | Schema | Define TokenAllocation lifecycle + CashReceipt + partial unique index | `init_db.py:290-342` |
| 5 | Helpers | Query historical adherence & lag; apply dispute penalty | `revenue_engine.py:1161-1250` |
| 6 | Background Job | Detect & mark stale PENDING allocations MISSING (48h timeout) | `cycle_manager.py:320-375` |
| 7 | Admin Endpoint | Resolve DISPUTED allocations to CLOSED with verified receipt | `main.py:104-151` + `cycle_manager.py:378-490` |
| 8 | Orchestrator | Call adherence + lag + rate function; return advance rate for capital decision | `cycle_manager.py:33-98` |

**Integration Point** (Future Deployment):

Call `evaluate_mill_capital(mill_id, trust_score, session)` from `issue_token()` to compute per-cycle advance rate:

```python
# In token_gateway.py or similar (NOT YET WIRED)
rate = evaluate_mill_capital(mill_id, trust_score, db_session)
allocation = TokenAllocation(mill_id=mill_id, status='PENDING', expected_cash=rate*capital_available)
```

**State Machine** (TokenAllocation.status):

```
PENDING (newly allocated)
  ├─ [timer > 48h] → MISSING (stale allocation, no receipt)
  ├─ [receipt received] → CLOSED (success)
  └─ [admin flags] → DISPUTED (inconsistent receipt, under review)

DISPUTED (human review)
  └─ [admin resolves] → CLOSED (receipt verified)

MISSING/CLOSED (terminal)
```

**Race Condition Defenses** (3 layers):

1. **Application Guard** (cycle_manager.py:43-52): Fail if `get_last_cycle_adherence()` encounters dual allocation
2. **Database Guard** (init_db.py:327): Partial unique index `ix_one_pending_per_mill` on `(mill_id) WHERE status='PENDING'`
3. **Consistency Check** (token_allocations table): `CHECK (status IN ('PENDING','CLOSED','MISSING','DISPUTED'))`

**Configuration Constants** (config.py — critical for operations):

- `BASE_ADVANCE_RATE = 0.5`: Maximum default advance (50%)
- `MISSING_CYCLE_TIMEOUT_HOURS = 48`: Hours before PENDING → MISSING transition
- `DISPUTED_ADHERENCE_PENALTY = 0.0`: Zero advance on disputed allocations
- `CONSERVATIVE_LAG_HOURS = 72.0`: Fallback lag assumption for disputed/missing cycles
- `LATENCY_BOUNDARIES`: Step function thresholds (24h→1.0, 48h→0.95, 72h→0.90, ∞→0.85)

**Execution Formula** (compute_per_cycle_advance_rate):

$$\text{advance\_rate} = \text{base\_rate} \times \frac{\text{trust\_score}}{100} \times \text{adherence}^2 \times \text{latency\_penalty}(\text{lag\_hours})$$

Where:
- `trust_score`: 0–100 (from trust_scorecard)
- `adherence`: 0–1 (historic cash / expected cash, clamped)
- `lag_hours`: Hours from allocation receipt time (or CONSERVATIVE_LAG_HOURS if disputed/missing)
- `latency_penalty()`: Step function returning 1.00–0.85 based on lag thresholds

**Testing Status**:

- ✅ Syntax validation passed on all 6 modified files (pylance)
- ✅ Partial index verified in SQLite database
- ✅ `detect_missing_cycles()` runtime test: 49-hour allocation correctly marked MISSING
- ✅ Timezone-aware datetime handling confirmed in queries
- ⚠️ Scheduler integration: Not yet wired (recommend APScheduler every 24-48h)
- ⚠️ Live code path: Not yet called from `issue_token()` or capital decision logic

**Deployment Checklist**:

- [x] Wire `detect_missing_cycles()` to scheduler trigger (24h interval in main.py)
- [x] Call `evaluate_mill_capital()` in capital allocation flow (wired into issue_token)
- [x] Update capital calculation logic to use per-cycle rate instead of static rate
- [x] All syntax validated (pylance passes all 6 modified files)
- [x] Gate threshold safe from floating-point errors: `advance_rate <= 0.0` (not `== 0.0`)
- [x] All import paths consistent: `scripts.init_db` (not `backend.init_db`)
- [x] All query helpers have required imports (select() imported where used)
- ⚠️ **BUSINESS DECISION REQUIRED**: Confirm 72-hour maximum grace period acceptable
  - Current: Scheduler runs every 24h, timeout is 48h → worst-case detection 72h
  - Alternative: Run scheduler every 6h → detection within ~30h
  - See [PER_CYCLE_ALLOCATION_REFERENCE.md: Scheduler Timing](PER_CYCLE_ALLOCATION_REFERENCE.md#scheduler-timing--missing-cycle-detection)
- [ ] Monitor first 30 days of MISSING/DISPUTED rate distribution
- ✅ No exception committees, no lender discretion inside the execution boundary

### 10.1 Input Contract (Immutable)

PXE only accepts verified upstream outputs.

**Required Inputs**:
```
mill_id
timestamp
trust_score (0–100)
reconciliation_score (0–100)
consistency_score (0–100)
governance_score (0–100)
EAR (0–1, ratio)
EAR_tier (TIER_1 | TIER_2 | TIER_3)
DCE (numeric, $/unit)
risk_penalty (0–1, decimal)
mill_state (VERIFIED | UNDER_REVIEW | COMPROMISED | SUSPENDED)
breach_flags: {
  gap_breach: bool
  variance_breach: bool
  economic_deficit: bool
  completeness_breach: bool
}
event_metadata_hash (Merkle root reference)
policy_id (identifier of policy to apply)
```

**Input Integrity Guarantee**:
- All inputs must be signed by upstream Layer 1–3 engines
- All inputs must be timestamped
- All inputs must reference Merkle roots for audit trail
- Tampered or unsigned inputs: PXE rejects execution, logs error, emits no CAO

### 10.2 Output Contract (Capital Action Object)

PXE produces a **Capital Action Object (CAO)** — a lock-step financial directive:

```json
{
  "mill_id": "NABIWI_MKWINDA",
  "timestamp": "2026-03-29T10:00:00Z",
  "policy_id": "STANDARD_COMMERCIAL",
  "policy_version": "1.0",
  "policy_hash": "0xabc123def456...",
  "input_hash": "0x789ghi101112...",
  
  "credit_decision": "APPROVE | CONDITIONAL | DECLINE",
  "approved_credit_limit": 125000,
  "advance_rate": 0.60,
  "tenor_days": 45,
  "escrow_ratio": 0.10,
  "collateral_requirement": "STANDARD | ELEVATED | FULL",
  "audit_frequency": "NONE | QUARTERLY | MONTHLY | IMMEDIATE",
  
  "capital_state": "OPEN | CONSTRAINED | FROZEN",
  "auto_adjustment": {
    "step_up_enabled": true,
    "step_down_enabled": true,
    "review_cycle_days": 7,
    "stability_threshold_cycles": 2
  },
  
  "enforcement_actions": [
    "NONE | ESCALATE_MONITORING | REQUIRE_AUDIT | FREEZE_CREDIT"
  ],
  
  "execution_trace": {
    "breach_overrides_applied": boolean,
    "policy_rules_applied": string,
    "auto_adjustment_triggered": boolean,
    "final_state": object
  }
}
```

**CAO Binding**:
- This object is final
- External capital systems must consume it as-is
- No re-interpretation, no adjustment, no discretion

### 10.3 Execution Order (Non-Negotiable)

PXE execution happens in this strict sequence:

**1. Input Validation**
- Check signatures
- Verify timestamps
- Confirm Merkle references
- Reject if any input fails validation

**2. Breach Override Logic** ← FIRST AUTHORITY
```
IF economic_deficit == TRUE:
  THEN capital_state = FROZEN
       enforcement_actions = [FREEZE_CREDIT, REQUIRE_AUDIT]
       
IF gap_breach == TRUE:
  THEN audit_frequency = IMMEDIATE
       enforcement_actions = [REQUIRE_AUDIT]
       
IF variance_breach == TRUE:
  THEN capital_state = CONSTRAINED
```

Breach logic is **sovereign over policy rules**. Breaches cannot be mitigated by high trust scores.

**3. Policy Rule Evaluation** ← SECOND AUTHORITY

Apply selected policy's rules in priority order. Each rule is a pure function:
```
RULE: IF conditions THEN actions PRIORITY n
```

Example (STANDARD_COMMERCIAL policy):
```
RULE SOVEREIGN_UNLOCK:
  IF trust_score >= 90 AND mill_state == VERIFIED
  THEN credit_decision = APPROVE
       advance_rate = 0.60
       tenor_days = 45
       capital_state = OPEN
  PRIORITY 1

RULE COMMERCIAL_APPROVE:
  IF trust_score >= 75 AND trust_score < 90
  THEN credit_decision = APPROVE
       advance_rate = 0.50
       tenor_days = 30
       capital_state = OPEN
  PRIORITY 2

RULE CONDITIONAL_CONTROL:
  IF trust_score >= 60 AND trust_score < 75
  THEN credit_decision = CONDITIONAL
       advance_rate = 0.45
       tenor_days = 21
       capital_state = CONSTRAINED
  PRIORITY 3

RULE DECLINE:
  IF trust_score < 60 OR mill_state == SUSPENDED
  THEN credit_decision = DECLINE
       advance_rate = 0.00
       capital_state = FROZEN
  PRIORITY 4
```

Conflicts resolved by PRIORITY (lowest number = highest authority).

**4. Auto-Adjustment Engine** ← THIRD AUTHORITY (Stateful)

This is the only stateful component of PXE.

Maintains per-mill state:
```
mill_credit_profile: {
  last_n_scores: [score_day1, score_day2, ..., score_dayN]
  stability_counter: int
  last_adjustment: timestamp
  auto_adjustment_state: DORMANT | QUEUED | ACTIVE
}
```

Step-Up Logic:
```
IF trust_score >= 90 for consecutive 2-3 cycles
   AND no Level 3+ breaches in window
   AND auto_adjustment_enabled
THEN advance_rate += delta (default: +0.05, capped at 0.65)
     update_timestamp()
```

Step-Down Logic:
```
IF trust_score drops >= 15 points
   OR breach_flags contains TRUE
THEN advance_rate -= delta (default: -0.10, floor: 0.25)
     capital_state = CONSTRAINED or FROZEN
     update_immediately()
```

Step-down is immediate; step-up requires stability (no false recoveries).

**5. Emit CAO**

Package all decisions into Capital Action Object.

### 10.4 Hashing & Audit Trail (Critical)

Every PXE execution generates two immutable hashes:

**input_hash**:
```
SHA256(
  mill_id || timestamp ||
  trust_score || reconciliation_score || consistency_score || governance_score ||
  EAR || EAR_tier || DCE || risk_penalty ||
  mill_state || stringify(breach_flags) ||
  event_metadata_hash ||
  policy_id
)
```

**policy_hash**:
```
SHA256(
  policy_id || policy_version ||
  full_policy_DSL_text ||
  effective_timestamp
)
```

Both hashes embedded in CAO.

**Auditability Guarantee**:

An auditor can reproduce the entire decision:
1. Retrieve CAO from capital ledger
2. Extract input_hash and policy_hash
3. Retrieve raw inputs and full policy definition from archive
4. Recompute PXE(inputs, policy)
5. Verify: output matches CAO exactly

If output doesn't match: policy was tampered, inputs were falsified, or engine was corrupted.

### 10.5 Policy Registry & Versioning

PXE does not hard-code policies. It consumes them from a policy registry.

**Policy Registry Structure**:
```
policies/
  STANDARD_COMMERCIAL/
    v1.0/
      policy.yaml (full DSL definition)
      hash: 0xabc123...
      effective_timestamp: 2026-03-29
      status: ACTIVE
    v0.9/
      policy.yaml
      hash: 0xdef456...
      effective_timestamp: 2026-03-01
      status: ARCHIVED
      
  CREDIT_UNION_CONSERVATIVE/
    v1.0/
      policy.yaml
      hash: 0x789ghi...
      status: ACTIVE
```

**Policy Layering** (Authority Model):

Policies operate in layers:

| Layer | Authority | Power | Examples |
|-------|-----------|-------|----------|
| **L0** | GridLedger Core | Breach overrides (sovereign) | Gap breach → IMMEDIATE audit, economic deficit → FROZEN |
| **L1** | Capital Provider (Lender) | Policy rules (can constrain L0, never override) | STANDARD_COMMERCIAL, CONSERVATIVE, AGGRESSIVE |
| **L2** | Regulator (optional) | Veto rules (can override L0/L1 if invoked) | Rare; e.g., "if borrower linked to sanctions list" |

**Fundamental Rule**: Lower layers can only constrain, never override higher layers.

Example:
- Breach override (L0) can enforce FROZEN
- Lender policy (L1) cannot un-freeze a FROZEN capital state
- Lender policy can add additional constraints (e.g., "no Tier 3 mills above portfolio 20%")

**Policy Versioning Requirement**:

Every policy must include:
```
policy_id: STANDARD_COMMERCIAL
version: 1.0
hash: 0xabc123def456xyz...
effective_timestamp: 2026-03-29T00:00:00Z
created_timestamp: 2026-03-15T14:30:00Z
status: ACTIVE | ARCHIVED | DRAFT | DEPRECATED
```

No mutable policies. Period.

Changes require new versions. All past decisions remain auditable against their original policies.

### 10.6 Policy DSL (Domain Specific Language) — Strict

Policies are expressed in a deterministic DSL. No fuzzy language allowed.

**Forbidden Keywords** (instantly reject if found):
- may, might, could, should
- subject to, at discretion, recommended
- reasonable, prudent, believed
- shall consider, may opt
- any comparative not bound by specific numeric thresholds

**Allowed Keywords**:
- IF (condition)
- THEN (action)
- AND, OR, NOT
- ==, !=, <, >, <=, >=
- IS, IN

**Example Policy DSL**:
```yaml
POLICY STANDARD_COMMERCIAL:
  VERSION: 1.0
  RULES:
    - name: SOVEREIGN_UNLOCK
      IF:
        - trust_score >= 90
        - mill_state == VERIFIED
      THEN:
        credit_decision: APPROVE
        advance_rate: 0.60
        tenor_days: 45
        capital_state: OPEN
      PRIORITY: 1
      
    - name: COMMERCIAL_APPROVE
      IF:
        - trust_score >= 75
        - trust_score < 90
      THEN:
        credit_decision: APPROVE
        advance_rate: 0.50
        tenor_days: 30
        capital_state: OPEN
      PRIORITY: 2
      
    - name: DECLINE
      IF:
        - trust_score < 60
        - OR mill_state == SUSPENDED
      THEN:
        credit_decision: DECLINE
        advance_rate: 0.00
        capital_state: FROZEN
      PRIORITY: 99
```

### 10.7 System Boundaries

PXE does **NOT**:
- Source capital or own funds
- Execute bank transfers or payment rails
- Hold collateral or escrow accounts
- Modify lender credit agreements
- Generate legal documents

PXE **DOES**:
- Compute financial decisions from verified state
- Define what must happen (via CAO)
- Emit audit-traceable directives
- Guarantee determinism and reproducibility

External systems (banks, payment processors, escrow agents, lender ops) must implement the CAO outputs.

### 10.8 Adversarial Input Risk (Critical)

⚠️ **Fundamental Vulnerability**: PXE executes perfectly on false inputs.

Example:
- Meter is tampered
- Energy is bypassed
- False data enters Layer 1–3

PXE will still execute deterministically and with perfect audit trail.

The system is **only as strong as Layer 1–3 integrity under adversarial conditions**.

PXE cannot detect fraud at Layer 1 (identity), Layer 2 (event continuity), or Layer 3 (physical measurement).

It can only enforce consequences **after fraud is detected and classified**.

**Mitigation**: Physical seals, tamper detection, unannounced audits, operator identity scrutiny, statistical anomaly detection.

**Resolution**: Phase 2 clamp integration converts probabilistic physical defence to verified determinism. This is the engineered solution to the adversarial input problem.

---

## 10.9 Recovery Time Objective (RTO) — Formal Statement

> **This section is a design choice explicitly stated, not a gap to be discovered during due diligence.**

**Purpose**: Define the maximum time between a fraud or breach event occurring and the system detecting, classifying, and acting on it. This is a commitment, not an estimate.

### RTO by Breach Type

| Breach Type | Detection Layer | Detection Window | Capital Action |
|---|---|---|---|
| Gap breach (continuity) | Layer 2 | Immediate on next event submission | Allocation blocked within same cycle |
| Variance breach | Layer 3.2 | Within reconciliation cycle (daily) | UNDER_REVIEW within 24h |
| Missing cycle (no remittance) | PXE / Scheduler | 48h timeout + scheduler interval | MISSING state, allocation blocked |
| Energy deficit breach | Layer 3.1 | Immediate on event ingestion | FLAGGED_ECONOMIC_DEFICIT |
| Suspicion accumulation | Layer 3.3 | Daily scoring cycle | Penalty applies within 24h of threshold crossing |
| Portfolio anomaly | §9.3b | Daily cross-meter review | Level 2 flag within 24h of detection run |

### Worst-Case Detection: MISSING Cycle

**Current configuration**:
- Scheduler runs every 24h
- MISSING_CYCLE_TIMEOUT_HOURS = 48h
- Worst-case detection: 72h (48h timeout + 24h scheduler lag)

**This is an explicit design choice**. The 72h worst-case window was selected to:
- Accommodate operator operational realities (payment collection, mobile connectivity)
- Avoid false-positive MISSING flags from transient network issues
- Balance fraud detection speed against operator relationship stability

**Alternative available**: Scheduler at 6h intervals → worst-case detection ~54h. Business decision deferred pending first 30 days of live MISSING/DISPUTED distribution data.

**Business Decision Required**: Confirm 72h maximum grace period acceptable, or trigger scheduler cadence review after Phase 1 live data.

### Residual Risk Window (Pre-Phase 2)

Between current deployment and Phase 2 clamp integration:

- Consistent spoofing (Shadow Meter) is not detectable within any RTO
- Detection relies on statistical accumulation (Layer 3.3) and physical audit scheduling
- This is acknowledged, not concealed
- Phase 2 clamp sensors close this window by converting assumed determinism to verified determinism

**Phase 2 Target**: Within 6 months of first Glass Box certification at NABIWI.

### RTO Communication for Capital Markets

For $1bn-level institutional investors, the honest statement is:

> "GridLedger detects and acts on most breach types within 24–48 hours. The worst-case detection window for a missing payment cycle is 72 hours by design. Consistent meter spoofing is the acknowledged residual risk, mitigated by statistical forensics and unannounced audits, and resolved architecturally by Phase 2 sensor integration."

That statement is more credible than a claim of real-time fraud prevention. It is also true.

---

## 11. External Capital Interfaces

PXE emits Capital Action Objects. External systems must consume and execute them.

### 11.1 Capital Action Consumption

**Who consumes CAO?**

External capital systems:
- Lender credit management platforms
- Escrow / collateral management systems
- Token issuance engines
- Bank settlement processors
- Audit/compliance record systems

**How to consume CAO?**

Via API:
```
POST /capital/execute

{
  CAO (complete Capital Action Object)
}

Response:
{
  "status": "accepted | rejected",
  "execution_id": "UUID",
  "reason": "string (if rejected)",
  "timestamp": "ISO-8601"
}
```

CAO is **semantic requirement**, not suggestion.

If external system rejects CAO: escalate to policy review, don't modify CAO.

### 11.2 Capital Ledger (Immutable Log)

Every executed CAO is recorded in a capital ledger:

```json
{
  "execution_id": "UUID",
  "cap_action_object": {...},
  "external_system_acknowledgment": {
    "system_id": "LENDER_CMS_001",
    "acknowledged_timestamp": "2026-03-29T10:05:00Z",
    "executed_actions": ["advance_rate_updated", "audit_scheduled"]
  },
  "ledger_timestamp": "2026-03-29T10:00:00Z"
}
```

This is the system of record for capital decisions.

### 11.3 Feedback Loop (State Update)

When external systems execute CAO actions, they report back:

```
POST /pxe/capital-executed

{
  "execution_id": "UUID",
  "mill_id": "NABIWI_MKWINDA",
  "actions_completed": ["advance_rate_changed_from_0.50_to_0.60"],
  "timestamp": "2026-03-29T10:05:15Z"
}
```

PXE records this for audit trail. Does not modify (read-only confirmation).

---

## Final Note (Executive Reality)

This version (v2.9) does five critical things:

1. **Protects legally**: No hidden assumptions. Adversarial input risk, RTO, and CONDITIONAL gap are explicitly named.
2. **Signals maturity to institutions**: Explicit trust boundaries, committed delivery dates, and acknowledged residual risks.
3. **Forces the roadmap**: Phase 2 clamp integration and Lender Policy Module have committed delivery anchors.
4. **Elevates real evidence**: The June 2025 six-meter portfolio event is named, dated, and positioned as proof-of-concept, not theory.
5. **Bridges to capital markets**: §0 Signal-to-Signature chain translates the full protocol into seven investor-grade steps.

The system does not claim to be perfect. It claims to be the most verifiable accountability infrastructure available for this asset class. That claim is defensible. Perfect is not.
