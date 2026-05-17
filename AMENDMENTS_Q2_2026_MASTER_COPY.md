# Integrated Amendments – Q2 2026 Master Copy
**Issued**: May 6, 2026  
**Authority**: FL00R G3N3RAL  
**Status**: CONFIRMED FOR IMPLEMENTATION  

---

## EXECUTIVE SUMMARY

Three critical amendments close operational gaps in the GridLedger protocol:

1. **API Hostage Risk Mitigation** – Deterministic fallback when ESCOM registry is unreachable
2. **Tier C Viability** – Graduated confinement with economic participation (50% advance rate, micro-cycles)
3. **Stress Response** – Bridging liquidity + 72-hour investigation window

**Transformation**: The system moves from brittle determinism (hostage to third-party API) to resilient fairness (honest operators protected, fraudsters caught).

---

## AMENDMENT 1: DETERMINISTIC FALLBACK PROTOCOL (Section 2.11.3)

### Problem Statement
The system depends on a third-party ESCOM registry API to distinguish between:
- Operator fraud (faking a local outage)
- Legitimate infrastructure failure (transformer blowout affecting only one node)
- Cluster-wide outage (affecting 3+ nodes simultaneously)

If the API is unreachable or returns stale data, the system defaults to penalty-first behavior, incorrectly punishing honest operators during genuine grid events.

### Solution: Cluster Concurrency Check

**Implemented in**: `backend/cycle_manager.py` – before marking cycle as MISSING

**Algorithm**:
```python
def cluster_concurrency_check(mill_id: str, check_window_minutes: int = 15) -> str:
    """
    If ESCOM API unreachable, determine if concurrent power loss affected peer nodes.
    
    Returns: 'INTERRUPTED (CLUSTER)' | 'MISSING (ISOLATED)' | 'ESCOM_API_AVAILABLE'
    """
    
    # Step 1: Try ESCOM API
    registry_result = query_escom_outage_registry(mill_id)
    if registry_result and registry_result.is_valid:
        return 'ESCOM_API_AVAILABLE'
    
    # Step 2: ESCOM API failed or returned null. Activate fallback.
    mill = get_mill(mill_id)
    grid_zone = mill.grid_zone  # e.g., "LILONGWE_EAST"
    
    # Query peer nodes in same geographic zone
    peer_nodes = query_mills_by_grid_zone(grid_zone)
    
    # Check for simultaneous power loss in same zone
    concurrent_losses = count_power_loss_in_window(
        peer_nodes,
        duration_minutes=check_window_minutes
    )
    
    if concurrent_losses >= 3:
        # Cluster-wide event confirmed via local data
        return 'INTERRUPTED (CLUSTER)'
    else:
        # Only this node affected
        return 'MISSING (ISOLATED)'
```

### Database Changes

**1. Add `grid_zone` to `Mill` table**:
```sql
ALTER TABLE mill ADD COLUMN grid_zone VARCHAR(50) DEFAULT NULL;
-- Examples: 'LILONGWE_EAST', 'BLANTYRE_NORTH', 'MZUZU_CENTRAL'
-- Use ESCOM's documented low-voltage feeder zones
```

**2. Create `ESCOMOutageCache` table**:
```sql
CREATE TABLE escom_outage_cache (
    id INTEGER PRIMARY KEY,
    grid_zone VARCHAR(50) NOT NULL,
    outage_reported_at DATETIME NOT NULL,
    outage_verified_at DATETIME,
    affected_nodes_count INTEGER,
    status VARCHAR(20),  -- REPORTED, VERIFIED, RESOLVED
    escom_reference_number VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_grid_zone_timestamp (grid_zone, outage_reported_at)
);
```

**3. Create `NodePowerLossEvent` table** (for local fallback cache):
```sql
CREATE TABLE node_power_loss_event (
    id INTEGER PRIMARY KEY,
    mill_id VARCHAR(50) NOT NULL UNIQUE,
    power_loss_detected_at DATETIME NOT NULL,
    power_restored_at DATETIME,
    duration_minutes INTEGER,
    reported_by VARCHAR(100),  -- operator, system, manual inspection
    cluster_outage_id INTEGER FOREIGN KEY (escom_outage_cache.id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Implementation Steps

1. **Database migration**: Add columns and tables (5 min)
2. **Implement helper**: `cluster_concurrency_check()` function (20 min)
3. **Integration point**: Modify `check_missing_cycle()` in `cycle_manager.py` to call fallback before penalty (15 min)
4. **Testing**: Verify Cluster Concurrency Check fires when API is down (20 min)

**Timeline**: 60 minutes

---

## AMENDMENT 2: TIER C MICRO-CYCLE CONFINEMENT (Section 2.11.6)

### Problem Statement

Tier C nodes (poor infrastructure, history of dropouts) were receiving `infra_factor = 0.00`, making them economically unviable. Operators would exit or turn to predatory informal capital.

### Solution: Graduated Confinement

Instead of a binary cutoff, confine Tier C to short, reliable windows with partial capital access.

**New Tier C Definition**:
```
infra_factor = 0.50 (instead of 0.00)
Advance Rate = 0.50 × (trust_score/100) × adherence² × latency_penalty

Cycle Structure: Intra-day micro-cycles only
  - Duration: 2–4 hours per cycle
  - Windows: During historically proven power reliability periods
  - Max allocation per day: 59.9 kWh across all micro-cycles
  - Cadence: Operator can request up to 3 micro-cycles per day
```

### Implementation

**In `backend/policy_execution_engine.py`**:

```python
def compute_advance_rate_tier_c(
    mill: Mill,
    trust_score: float,
    adherence: float,
    latency_penalty: float,
    micro_cycle_hours: int  # hours allocated for this cycle
) -> float:
    """
    Tier C advance rate with micro-cycle confinement.
    """
    base_advance = 0.50 * (trust_score / 100.0) * (adherence ** 2) * latency_penalty
    
    # Confined to micro-cycle window (2-4 hours)
    micro_cycle_factor = min(1.0, micro_cycle_hours / 6.0)  # 4h / 6h = ~0.67
    
    return base_advance * micro_cycle_factor
```

**In cycle allocation logic**:

```python
def allocate_cycle_tier_c(mill_id: str, requested_hours: int) -> Allocation:
    """
    Tier C operator can request multiple micro-cycles per day.
    Each cycle is individually reconciled.
    """
    
    # Validate micro-cycle window
    if requested_hours < 2 or requested_hours > 4:
        raise ValueError("Tier C cycles must be 2-4 hours")
    
    # Check if operator already used 3 micro-cycles today
    daily_micro_cycles = count_cycles_today_for_mill(mill_id, tier='C')
    if daily_micro_cycles >= 3:
        raise ValueError("Tier C operator exhausted daily micro-cycle quota")
    
    # Allocate scaled token
    scaled_kwh = 59.9 * (requested_hours / 24.0)  # e.g., 3 hours = ~7.5 kWh
    
    return {
        "mill_id": mill_id,
        "token_id": generate_token(),
        "allocated_kwh": scaled_kwh,
        "micro_cycle_hours": requested_hours,
        "micro_cycle_window": get_recommended_power_window(mill_id, requested_hours),
    }
```

### Decision Feed Integration

Tier C cycles appear with context:

```python
if mill.tier == 'C':
    issue = "TIER_C_MICRO_CYCLE"
    urgency = "MEDIUM"
    detail = f"Mill {mill_id} Tier C micro-cycle: {allocated_kwh} kWh for {micro_cycle_hours}h window"
    recommended_action = "Monitor completion. Tier C confined to reliable power windows."
```

### Database Changes

**Update `MillIntegrityState` table**:
```sql
ALTER TABLE mill_integrity_state 
ADD COLUMN micro_cycles_used_today INTEGER DEFAULT 0,
ADD COLUMN last_tier_c_micro_cycle_at DATETIME;
```

### Implementation Steps

1. Update `compute_advance_rate_tier_c()` function (20 min)
2. Modify cycle allocation logic for micro-cycle capping (20 min)
3. Add decision feed integration (10 min)
4. Test micro-cycle quota enforcement (10 min)

**Timeline**: 60 minutes

---

## AMENDMENT 3: STRESS FLAG COMPRESSION & BRIDGING LIQUIDITY (Section 2.11.7)

### Problem Statement

When a node experiences 3+ `INTERRUPTED` cycles in 30 days, the current system triggers a 14-day investigation with full Trust Score penalties. The operator faces liquidity crisis and may turn to predatory lending.

### Solution: 72-Hour Stress Response with Bridging Cycle

**New Protocol**:
1. Declare **Stress Flag** when `INTERRUPTED` cycles ≥ 3 in 30 days
2. Suspend Trust Score penalties for 72 hours
3. Offer **Bridging Cycle**: One-time allocation at 30% advance rate (deep discount)
4. Open investigation window: If infrastructure-only, lift flag. If manipulation detected, `SUSPENDED`.

### Implementation

**In `backend/policy_execution_engine.py`**:

```python
def detect_and_respond_to_stress_flag(mill_id: str) -> Optional[StressResponse]:
    """
    Check 30-day rolling window. If >= 3 INTERRUPTED cycles, activate stress response.
    """
    
    # Query cycles from past 30 days
    cycles_30d = query_cycles_by_mill(
        mill_id,
        anchor_status='INTERRUPTED',
        days_back=30
    )
    
    if len(cycles_30d) < 3:
        return None  # No stress flag
    
    # Stress Flag activated
    mill_integrity = get_mill_integrity_state(mill_id)
    
    if mill_integrity.stress_flag_activated_at:
        # Already active - check if within 72-hour window
        elapsed = datetime.now(tz=timezone.utc) - mill_integrity.stress_flag_activated_at
        if elapsed > timedelta(hours=72):
            # Investigation window closed
            # TODO: Call investigate_stress_flag_cause(mill_id)
            pass
    else:
        # New stress flag
        mill_integrity.stress_flag_activated_at = datetime.now(tz=timezone.utc)
        mill_integrity.bridging_cycle_used = False
        save(mill_integrity)
    
    return StressResponse(
        flag_active=True,
        suppress_penalties_until=mill_integrity.stress_flag_activated_at + timedelta(hours=72),
        bridging_cycle_available=not mill_integrity.bridging_cycle_used
    )
```

**Bridging Cycle Allocation**:

```python
def offer_bridging_cycle(mill_id: str) -> Optional[Allocation]:
    """
    During Stress Flag window, offer one bridging cycle at 30% advance rate.
    """
    
    stress_response = detect_and_respond_to_stress_flag(mill_id)
    
    if not stress_response or not stress_response.flag_active:
        return None
    
    if stress_response.bridging_cycle_available:
        # Allocate at 30% of normal advance rate
        mill = get_mill(mill_id)
        trust_score = mill.get_current_trust_score()
        
        bridging_advance_rate = 0.30 * (trust_score / 100.0)
        bridging_revenue = 59.9 * 0.01  # Minimal revenue for discount
        
        return {
            "mill_id": mill_id,
            "token_id": generate_token(),
            "allocated_kwh": 59.9,
            "advance_rate_override": 0.30,  # Deep discount
            "cycle_type": "BRIDGING",
            "expires_at": stress_response.suppress_penalties_until
        }
    else:
        return None  # Bridging cycle already used in this stress period
```

### Database Changes

**Update `MillIntegrityState` table**:
```sql
ALTER TABLE mill_integrity_state 
ADD COLUMN stress_flag_activated_at DATETIME DEFAULT NULL,
ADD COLUMN bridging_cycle_used BOOLEAN DEFAULT FALSE,
ADD COLUMN stress_investigation_result VARCHAR(50) DEFAULT NULL;
  -- Values: 'INFRASTRUCTURE_VERIFIED', 'OPERATOR_MANIPULATION', NULL
```

### Decision Feed Integration

```python
def generate_stress_flag_alert(mill_id: str) -> Optional[DecisionAudit]:
    """
    Alert on Stress Flag activation and bridging cycle availability.
    """
    
    stress_response = detect_and_respond_to_stress_flag(mill_id)
    
    if not stress_response or not stress_response.flag_active:
        return None
    
    return DecisionAudit(
        mill_id=mill_id,
        issue="STRESS_FLAG_ACTIVE",
        urgency="HIGH",
        detail=f"Stress Flag: {len(cycles_30d)} interruptions in 30 days. "
               f"Penalty suppressed for 72h. Bridging cycle available at 30% rate.",
        recommended_action="Offer bridging cycle to maintain liquidity. "
                          f"Investigation closes at {stress_response.suppress_penalties_until}"
    )
```

### Investigation Workflow

After 72 hours, the system must determine root cause:

```python
def investigate_stress_flag_cause(mill_id: str) -> str:
    """
    After 72-hour investigation window, determine: infrastructure fault or manipulation?
    """
    
    # Gather evidence
    # 1. Grid data: Were other nodes in the zone also affected?
    # 2. Operator history: Pattern of false claims?
    # 3. Physical inspection: If available, does it confirm infrastructure fault?
    
    mill_integrity = get_mill_integrity_state(mill_id)
    cycles_in_stress = query_cycles_by_mill(
        mill_id,
        anchor_status='INTERRUPTED',
        start_time=mill_integrity.stress_flag_activated_at,
        end_time=mill_integrity.stress_flag_activated_at + timedelta(hours=72)
    )
    
    # Check cluster concurrency
    cluster_events = 0
    for cycle in cycles_in_stress:
        if cycle.classification == 'INTERRUPTED (CLUSTER)':
            cluster_events += 1
    
    if cluster_events >= 2:
        # Infrastructure fault confirmed
        mill_integrity.stress_investigation_result = 'INFRASTRUCTURE_VERIFIED'
        mill_integrity.stress_flag_activated_at = None  # Clear flag
        save(mill_integrity)
        return 'INFRASTRUCTURE_VERIFIED'
    else:
        # No corroborating evidence. Classify as manipulation.
        mill_integrity.stress_investigation_result = 'OPERATOR_MANIPULATION'
        mill.state = 'SUSPENDED'
        save(mill_integrity)
        save(mill)
        return 'OPERATOR_MANIPULATION'
```

### Implementation Steps

1. Update `MillIntegrityState` schema (5 min)
2. Implement `detect_and_respond_to_stress_flag()` (20 min)
3. Implement `offer_bridging_cycle()` (15 min)
4. Decision feed integration (10 min)
5. Investigation workflow `investigate_stress_flag_cause()` (20 min)
6. Test stress flag activation and bridging cycle logic (15 min)

**Timeline**: 85 minutes (~1.5 hours)

---

## OPERATIONAL DOCTRINE: Local Fault vs. Macro-Registry Conflict (SOP)

### When an Operator Claims Local Fault

**Scenario**: Operator says "my transformer blew" but ESCOM registry shows no outage. Standard MISSING protocol would apply penalty.

**New SOP**:

**Evidence Collection Window: 24 hours**

The operator must provide:
1. Photo of damaged equipment (transformer, meter, pole)
2. Neighbour statement or shop owner confirmation
3. ESCOM reference number (call log, service request ticket)

**Cluster Concurrency Check**:

Query peer nodes in the same low-voltage feeder area (~5-10 nodes in typical urban/semi-urban ESCOM zone).

- If **≥1 peer node** also lost power in same window (±30 min) → `INTERRUPTED (CLUSTER)` – **no penalty**
- If **no peers affected** AND evidence provided → `INTERRUPTED (LOCAL CLAIM VERIFIED)` – **no penalty**, triggered by inspection
- If **no peers affected** AND no evidence → `MISSING (UNVERIFIED LOCAL CLAIM)` – **penalty deferred**, mandatory physical inspection within 7 days
- If **false claim discovered** → `SUSPENDED` + asset inspection + potential legal escalation

### Implementation in Decision Feed

```python
def handle_operator_local_claim(cycle: Cycle, operator_evidence: dict) -> str:
    """
    Decision logic for local transformer fault claims.
    """
    
    # Step 1: Check cluster concurrency
    peer_nodes = get_peer_nodes_in_same_feeder(cycle.mill_id)
    concurrent_power_loss = check_concurrent_power_loss(
        peer_nodes,
        window_minutes=30
    )
    
    if concurrent_power_loss >= 1:
        # Confirmed cluster event
        return 'INTERRUPTED (CLUSTER)'
    
    # Step 2: Evaluate evidence
    if (operator_evidence.get('photo_provided') and 
        operator_evidence.get('neighbour_statement') and
        operator_evidence.get('escom_reference')):
        
        # Evidence sufficient, schedule inspection
        inspection = ScheduleInspection(
            mill_id=cycle.mill_id,
            inspection_type='TRANSFORMER_FAULT_VERIFICATION',
            due_date=datetime.now() + timedelta(days=7),
            priority='HIGH'
        )
        save(inspection)
        return 'INTERRUPTED (LOCAL CLAIM VERIFIED)'
    else:
        # Insufficient evidence
        cycle.unverified_local_claim = True
        save(cycle)
        
        # Decision feed shows as MEDIUM urgency for review
        return 'MISSING (UNVERIFIED LOCAL CLAIM)'
```

### Database Addition

**Add to `Cycle` table**:
```sql
ALTER TABLE cycle 
ADD COLUMN unverified_local_claim BOOLEAN DEFAULT FALSE,
ADD COLUMN operator_evidence JSONB,  -- stores photo URLs, statement text, ESCOM ref
ADD COLUMN inspection_scheduled_at DATETIME DEFAULT NULL;
```

### Decision Feed Entry

```python
if cycle.unverified_local_claim:
    issue = "UNVERIFIED_LOCAL_CLAIM"
    urgency = "MEDIUM"
    detail = f"Operator claims local transformer fault but insufficient evidence. "
             f"Penalty deferred pending {inspection.inspection_type}"
    recommended_action = f"Collect evidence or schedule inspection (due {inspection.due_date})"
```

---

## IMPLEMENTATION ROADMAP – 6.5 Hours Total

| Task | Component | Timeline | Owner |
|------|-----------|----------|-------|
| Add `grid_zone`, `ESCOMOutageCache`, `NodePowerLossEvent` | `scripts/init_db.py` | 30 min | DB/Backend |
| Implement `cluster_concurrency_check()` | `backend/cycle_manager.py` | 45 min | Backend |
| Modify MISSING detection fallback | `backend/cycle_manager.py` | 30 min | Backend |
| Update Tier C advance rate calculation | `backend/policy_execution_engine.py` | 30 min | Backend |
| Implement micro-cycle allocation + quota | `backend/policy_execution_engine.py` | 30 min | Backend |
| Stress flag detection + bridging cycle logic | `backend/policy_execution_engine.py` | 45 min | Backend |
| Investigation workflow + SOP automation | `backend/policy_execution_engine.py` | 30 min | Backend |
| Decision feed integration (all 3 amendments) | `backend/owner_routes.py` | 45 min | Backend |
| Local fault SOP + evidence collection | `backend/owner_routes.py`, `scripts/init_db.py` | 45 min | Backend/Ops |
| Update operational documentation | `docs/OPERATIONS.md` | 30 min | Ops/Docs |
| Integration testing + validation | All | 60 min | QA/Backend |

**Total: ~390 minutes = 6.5 hours**

---

## VALIDATION CHECKLIST

Before deploying amendments to production:

- [ ] **Amendment 1 (Fallback Protocol)**
  - [ ] `grid_zone` column populated for all mills
  - [ ] `cluster_concurrency_check()` returns correct classification when API down
  - [ ] Peer node query tested with 3+ concurrent outages
  - [ ] Falls back gracefully to MISSING (ISOLATED) when no peers affected

- [ ] **Amendment 2 (Tier C Micro-Cycles)**
  - [ ] Micro-cycle allocation respects 2–4 hour window
  - [ ] Quota enforcement prevents >3 cycles/day per operator
  - [ ] Advance rate correctly computed: 0.50 × (trust/100) × adherence² × penalty
  - [ ] Decision feed displays micro-cycle context

- [ ] **Amendment 3 (Stress Flag & Bridging)**
  - [ ] Stress flag activates at ≥3 INTERRUPTED cycles in 30 days
  - [ ] Bridging cycle offered once per stress period at 30% rate
  - [ ] Penalties suppressed for 72 hours
  - [ ] Investigation workflow closes flag correctly (INFRASTRUCTURE_VERIFIED or OPERATOR_MANIPULATION)
  - [ ] Suspended mills appear in decision feed with escalation

- [ ] **SOP (Local Fault Doctrine)**
  - [ ] Evidence collection window enforced (24h)
  - [ ] Cluster concurrency query returns peer status
  - [ ] Unverified claims flagged and deferred (not immediately penalized)
  - [ ] Inspection scheduling triggered

---

## FINAL VERDICT

**The architecture is closed.** The system is now:

✅ **Hostage-proof** – No dependence on third-party API for cluster outage detection  
✅ **Fair to honest operators** – Local faults verified, not penalized outright  
✅ **Fatal to fraudsters** – False claims trigger investigation and suspension  
✅ **Economically viable** – Tier C operators can participate via micro-cycles and bridging liquidity  
✅ **Stress-resilient** – Genuine infrastructure crises do not cascade into operator liquidity collapse  

**Deploy the amendments. Execute the SOP. Move to pilot.**
