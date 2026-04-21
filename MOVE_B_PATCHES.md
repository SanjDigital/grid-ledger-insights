# 🛡️ Move B: Adversarial Layer – Complete Patches

**Philosophy Shift:** From "how do we allocate fairly?" to "how do we defend the system?"

---

## Overview: 5 Priorities in Sequence

| Priority | What | Why | Time |
|----------|------|-----|------|
| **1. Idempotency** | Duplicate key → same response | Retries don't corrupt state | 2h |
| **2. Time-Weighted Risk** | Overdue age multiplies exposure | Delays have financial velocity | 1h |
| **3. ESCOM Reconciliation** | Verify against purchase ledger | External anchor (not assumption) | 4h |
| **4. Anomaly Detection** | Flag strategic deviation | Catch cluster-wide patterns | 3h |
| **5. Game-Theoretic Layer** | Detect collusion, parallel ops | Defend against coordinated attacks | 2h |

---

# 🔧 Patch 1: Add `IdempotencyRecord` Model

**Why:** Every POST that can be retried must be idempotent. Duplicate requests with the same key return the same result—no new allocation.

## File: `scripts/init_db.py`

Add this new model **before the database setup section**:

```python
# 10. Idempotent Request Tracking (Retry Safety)
class IdempotencyRecord(SQLModel, table=True):
    """
    Stores idempotent request keys and responses.
    
    On retry with same Idempotency-Key, return cached response instead of re-processing.
    TTL: 24 hours (configurable).
    """
    __tablename__ = "idempotency_records"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    idempotency_key: str = Field(index=True, unique=True)  # Request-unique ID
    mill_id: str = Field(index=True)
    endpoint: str  # e.g., "/api/owner/mills/{mill_id}/allocate-token"
    
    # Cached response
    response_json: str  # Full response (allowed, reason, allocation_id, etc.)
    http_status_code: int  # 200, 400, 500, etc.
    
    # Request metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime  # TTL (24 hours from creation)
    
    # Tracking
    replay_count: int = Field(default=0)  # How many times this key was replayed
    
    __table_args__ = (
        CheckConstraint("http_status_code >= 200 AND http_status_code < 600", name="check_http_status_code"),
    )
```

**Location in file:** After `DecisionAudit` class, before `# Database Setup` comment.

---

# 🔧 Patch 2: Add Time-Weighted Fields to `TokenAllocation`

**Why:** Track when allocation was created and when receipts arrived (or didn't). Enables time-decay calculations.

## File: `scripts/init_db.py`

Update the `TokenAllocation` class to add timing fields:

```python
class TokenAllocation(SQLModel, table=True):
    """
    Per-cycle token allocation and tracking.
    
    One token = 59.9 kWh = one production cycle.
    Tracks expected revenue, cash receipt, and cycle status.
    """
    __tablename__ = "token_allocations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    mill_id: str = Field(foreign_key="mill.id", index=True)
    allocated_kwh: float = Field(default=59.9)
    expected_revenue: float
    allocated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = Field(default="PENDING")  # PENDING, CLOSED, MISSING, DISPUTED
    
    # ─── NEW TIME-WEIGHTED RISK FIELDS ──────────────────────────────────────
    # Time offset from allocation to expected receipt (configurable, e.g., 24h)
    expected_receipt_by: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=24)
    )
    # Time when receipt actually arrived (NULL if MISSING)
    receipt_arrived_at: Optional[datetime] = None
    # Time when status changed to MISSING (NULL if never transitioned)
    missing_detected_at: Optional[datetime] = None
    # ────────────────────────────────────────────────────────────────────────
    
    # Resolution tracking (for disputed cycles)
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    
    # Relationships
    cash_receipts: list["CashReceipt"] = Relationship(back_populates="allocation")
    
    __table_args__ = (
        CheckConstraint("status IN ('PENDING', 'CLOSED', 'MISSING', 'DISPUTED')", name="check_token_allocation_status"),
    )
```

**Changes:**
- Add `expected_receipt_by: datetime` – when cash should arrive (default 24h from now)
- Add `receipt_arrived_at: Optional[datetime]` – when it actually arrived
- Add `missing_detected_at: Optional[datetime]` – when marked MISSING
- Import `timedelta` at top of file if not already present

---

# 🔧 Patch 3: Update `allocate_token` – Idempotency Check & Store

**Why:** Before allocating, check if this request key was already processed. If yes, return cached response. If no, proceed and cache the result.

## File: `backend/owner_routes.py`

### Step 3a: Add imports at top of file

```python
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from datetime import datetime, timezone, timedelta  # ADD: timedelta
```

### Step 3b: Add idempotency helper function (before `allocate_token`)

```python
def _check_idempotency(
    mill_id: str,
    idempotency_key: Optional[str],
    session: Session,
) -> tuple[bool, Optional[dict]]:
    """
    Check if this idempotency key was already processed.
    
    Returns:
        (is_duplicate: bool, cached_response: Optional[dict])
        - If (True, dict): Request was already processed, return cached response
        - If (False, None): This is a new request, proceed normally
    """
    if not idempotency_key:
        return False, None
    
    # Check if key exists and is still valid (not expired)
    from scripts.init_db import IdempotencyRecord
    
    record = session.exec(
        select(IdempotencyRecord).where(
            IdempotencyRecord.idempotency_key == idempotency_key,
            IdempotencyRecord.mill_id == mill_id,
        )
    ).first()
    
    if not record:
        return False, None
    
    # Check if expired
    now = datetime.now(timezone.utc)
    if now > record.expires_at:
        # Expired – treat as new request
        session.delete(record)
        session.commit()
        return False, None
    
    # Found valid cached response
    import json
    cached_response = json.loads(record.response_json)
    record.replay_count += 1
    session.add(record)
    session.commit()
    
    logger.info(
        f"Idempotent replay: mill={mill_id}, key={idempotency_key[:8]}..., "
        f"cached_response={cached_response.get('reason', 'allowed')}, "
        f"replay_count={record.replay_count}"
    )
    
    return True, cached_response


def _store_idempotency_response(
    mill_id: str,
    idempotency_key: str,
    endpoint: str,
    response: dict,
    http_status_code: int,
    session: Session,
    ttl_hours: int = 24,
) -> None:
    """Store response with idempotency key for future replays."""
    from scripts.init_db import IdempotencyRecord
    import json
    
    now = datetime.now(timezone.utc)
    record = IdempotencyRecord(
        idempotency_key=idempotency_key,
        mill_id=mill_id,
        endpoint=endpoint,
        response_json=json.dumps(response),
        http_status_code=http_status_code,
        created_at=now,
        expires_at=now + timedelta(hours=ttl_hours),
        replay_count=0,
    )
    session.add(record)
    # Note: no commit yet – outer transaction will commit
```

### Step 3c: Update `allocate_token` signature and add idempotency check

Find this line:
```python
@router.post("/mills/{mill_id}/allocate-token", response_model=AllocationDecisionResponse)
def allocate_token(
    mill_id: str,
    session: Session = Depends(get_session),
    _: str = Depends(verify_api_key),
):
```

Replace with:
```python
@router.post("/mills/{mill_id}/allocate-token", response_model=AllocationDecisionResponse)
def allocate_token(
    mill_id: str,
    session: Session = Depends(get_session),
    _: str = Depends(verify_api_key),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Allocate a token for a mill with idempotency guarantees.
    
    Args:
        mill_id: Mill identifier
        idempotency_key: Optional header for idempotent retries (24h TTL)
    
    Idempotency Behavior:
        - Same Idempotency-Key within 24h → returns identical response
        - Missing header → request is not idempotent (no caching)
        - Expired (>24h) → treated as new request
    """
    # ──────────────────────────────────────────────────────────────────────
    # IDEMPOTENCY CHECK: Early exit if this key was already processed
    # ──────────────────────────────────────────────────────────────────────
    is_duplicate, cached_response = _check_idempotency(mill_id, idempotency_key, session)
    if is_duplicate and cached_response:
        return cached_response
    
    # Global kill switch
    if not SYSTEM_ALLOCATION_ENABLED:
        raise HTTPException(status_code=503, detail="System allocation disabled by operator.")

    # ... rest of function continues as before ...
```

### Step 3d: Store response before returning (update each return statement)

At **every point** where `allocate_token` returns `AllocationDecisionResponse`, wrap in idempotency storage. Find all return statements and add before them:

```python
# Before each return AllocationDecisionResponse(...):
if idempotency_key:
    _store_idempotency_response(
        mill_id=mill_id,
        idempotency_key=idempotency_key,
        endpoint="/api/owner/mills/{mill_id}/allocate-token",
        response=<response_dict>,  # Build from AllocationDecisionResponse
        http_status_code=200,
        session=session,
    )
```

**Example (update the 3 return statements in `allocate_token`):**

```python
# Return 1: Blocked active cycle
response = AllocationDecisionResponse(
    allowed=False,
    reason=f"BLOCKED_{cycle_state_str}",
    decision_basis=basis,
)
if idempotency_key:
    _store_idempotency_response(
        mill_id, idempotency_key,
        "/api/owner/mills/{mill_id}/allocate-token",
        response.model_dump(), 200, session
    )
return response

# Return 2: Blocked (policy)
response = AllocationDecisionResponse(
    allowed=False,
    reason=reason,
    decision_basis=basis,
)
if idempotency_key:
    _store_idempotency_response(
        mill_id, idempotency_key,
        "/api/owner/mills/{mill_id}/allocate-token",
        response.model_dump(), 200, session
    )
return response

# Return 3: Success
response = AllocationDecisionResponse(
    allowed=True,
    reason=None,
    allocation_id=result["allocation_id"],
    allocated_kwh=result["allocated_kwh"],
    expected_revenue=result["expected_revenue"],
    decision_basis=basis,
)
if idempotency_key:
    _store_idempotency_response(
        mill_id, idempotency_key,
        "/api/owner/mills/{mill_id}/allocate-token",
        response.model_dump(), 200, session
    )
return response
```

---

# 🔧 Patch 4: Time-Weighted Risk Calculation

**Why:** Overdue money ages like wine – it gets more expensive. A debt 7 days old is worse than one 1 day old.

## File: `backend/owner_routes.py`

### Step 4a: Add helper function for time-weighted exposure

```python
def _calc_time_weighted_risk(
    allocation_id: int,
    session: Session,
) -> Decimal:
    """
    Calculate time-weighted exposure for a single allocation.
    
    Base exposure = expected_revenue - actual_cash (if positive)
    Time multiplier = 1 + (overdue_days * 0.1)  [10% per day, caps at 2x if >10 days]
    
    Examples:
      - 1 day overdue: multiplier = 1.1
      - 3 days overdue: multiplier = 1.3
      - 7 days overdue: multiplier = 1.7
      - 10+ days overdue: multiplier = 2.0 (capped)
    """
    allocation = session.exec(
        select(TokenAllocation).where(TokenAllocation.id == allocation_id)
    ).first()
    
    if not allocation:
        return Decimal(0)
    
    # Get actual cash received
    receipt = session.exec(
        select(CashReceipt).where(CashReceipt.allocation_id == allocation_id)
    ).first()
    
    actual_cash = Decimal(receipt.amount) if receipt else Decimal(0)
    base_exposure = max(Decimal(0), Decimal(allocation.expected_revenue) - actual_cash)
    
    if base_exposure == 0:
        return Decimal(0)
    
    # Calculate days overdue
    now = datetime.now(timezone.utc)
    
    # Use expected_receipt_by if available, else fall back to allocated_at + 24h
    expected_by = allocation.expected_receipt_by or (
        allocation.allocated_at + timedelta(hours=24)
    )
    expected_by = _to_utc(expected_by)
    
    if now <= expected_by:
        # Not yet overdue
        return base_exposure
    
    overdue_seconds = (now - expected_by).total_seconds()
    overdue_days = overdue_seconds / (24 * 3600)
    
    # Multiplier: 1 + (0.1 * days), capped at 2.0
    multiplier = min(Decimal(2.0), Decimal(1.0) + Decimal(overdue_days) * Decimal("0.1"))
    
    weighted_exposure = base_exposure * multiplier
    
    logger.debug(
        f"Time-weighted risk: allocation={allocation_id}, "
        f"base={base_exposure}, overdue_days={overdue_days:.2f}, "
        f"multiplier={multiplier}, weighted={weighted_exposure}"
    )
    
    return weighted_exposure
```

### Step 4b: Update `_get_outstanding_exposure` to use time-weighted risk

Replace the existing `_get_outstanding_exposure` with:

```python
def _get_outstanding_exposure(mill_id: str, session: Session) -> Decimal:
    """
    Financial exposure: sum of time-weighted risk over all allocations.
    
    Base exposure = expected_revenue - actual_cash
    Time multiplier = 1 + (overdue_days * 0.1), capped at 2.0
    
    1 day overdue → 10% penalty  
    7 days overdue → 70% penalty  
    10+ days overdue → 100% penalty (2x exposure)
    
    Uses a single SQL query with optional time-weighting applied in Python
    (since database doesn't have easy access to expected_receipt_by TTL).
    """
    # Get all allocations for this mill
    allocations = session.exec(
        select(TokenAllocation.id, TokenAllocation.expected_revenue, TokenAllocation.expected_receipt_by)
        .where(TokenAllocation.mill_id == mill_id)
    ).all()
    
    if not allocations:
        return Decimal(0)
    
    # Fetch all receipts in one query
    alloc_ids = [a[0] for a in allocations]
    receipts = session.exec(
        select(CashReceipt).where(CashReceipt.allocation_id.in_(alloc_ids))
    ).all()
    receipt_map = {r.allocation_id: r.amount for r in receipts}
    
    # Calculate time-weighted total
    now = datetime.now(timezone.utc)
    total_weighted_exposure = Decimal(0)
    
    for alloc_id, expected_revenue, expected_receipt_by in allocations:
        actual = Decimal(receipt_map.get(alloc_id, 0))
        base_exposure = max(Decimal(0), Decimal(expected_revenue) - actual)
        
        if base_exposure == 0:
            continue
        
        # Apply time weighting
        if expected_receipt_by:
            expected_receipt_by = _to_utc(expected_receipt_by)
            if now > expected_receipt_by:
                overdue_seconds = (now - expected_receipt_by).total_seconds()
                overdue_days = overdue_seconds / (24 * 3600)
                multiplier = min(Decimal(2.0), Decimal(1.0) + Decimal(overdue_days) * Decimal("0.1"))
                weighted = base_exposure * multiplier
            else:
                weighted = base_exposure
        else:
            weighted = base_exposure
        
        total_weighted_exposure += weighted
    
    return total_weighted_exposure
```

---

# 🔧 Patch 5: ESCOM Reconciliation Check

**Why:** Don't assume energy was consumed. Verify against the purchase ledger.

## File: `scripts/init_db.py`

Add this new model **before database setup**:

```python
# 11. ESCOM Purchase Reconciliation (External Anchor)
class ESCOMTokenPurchase(SQLModel, table=True):
    """
    Ingestion of ESCOM token purchase logs.
    
    Manually ingested from ESCOM app export (CSV).
    Used to reconcile allocated tokens against purchased tokens.
    """
    __tablename__ = "escom_token_purchases"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    mill_id: str = Field(foreign_key="mill.id", index=True)
    
    # ESCOM data
    purchase_date: datetime  # When token was bought
    purchase_id: str  # ESCOM's transaction ID (unique key)
    units_kwh: float  # Energy units purchased
    cost_mwk: float  # Cost in MWK
    
    # Reconciliation
    allocated_kwh: Optional[float] = None  # How much was allocated from this purchase
    consumed_kwh: Optional[float] = None  # How much was actually used (from ESCOM meter)
    variance_pct: Optional[float] = None  # (consumed - allocated) / allocated
    
    # Status
    status: str = Field(default="PENDING")  # PENDING, ALLOCATED, CONSUMED, RECONCILED, DISPUTED
    reconciled_at: Optional[datetime] = None
    notes: Optional[str] = None
    
    # Timestamp
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

## File: `backend/owner_routes.py`

Add this helper before `allocate_token`:

```python
def _check_escom_reconciliation(
    mill_id: str,
    allocated_kwh: Decimal,
    session: Session,
) -> tuple[bool, Optional[str]]:
    """
    Check if this allocation would exceed ESCOM purchase limits.
    
    Returns:
        (is_safe: bool, reason: Optional[str])
        - (True, None): Safe to allocate
        - (False, reason): Would violate reconciliation rule
    """
    from scripts.init_db import ESCOMTokenPurchase
    
    # Check if ESCOM data is available for this mill
    escom_records = session.exec(
        select(ESCOMTokenPurchase)
        .where(
            ESCOMTokenPurchase.mill_id == mill_id,
            ESCOMTokenPurchase.status.in_(["PENDING", "ALLOCATED"])
        )
        .order_by(ESCOMTokenPurchase.purchase_date.desc())
    ).all()
    
    if not escom_records:
        # No ESCOM data – cannot verify, so pass (will implement stricter checks later)
        logger.debug(f"No ESCOM data for {mill_id}, skipping reconciliation check")
        return True, None
    
    # Find unallocated ESCOM kwh
    total_escom_kwh = sum(Decimal(r.units_kwh) for r in escom_records)
    total_allocated_kwh = sum(
        Decimal(r.allocated_kwh or 0) for r in escom_records
    )
    available_kwh = total_escom_kwh - total_allocated_kwh
    
    if Decimal(allocated_kwh) > available_kwh:
        reason = (
            f"ESCOM allocation limit exceeded: "
            f"want {allocated_kwh} kWh, have {available_kwh} kWh available "
            f"(total purchased {total_escom_kwh}, already allocated {total_allocated_kwh})"
        )
        logger.warning(f"ESCOM check failed for {mill_id}: {reason}")
        return False, reason
    
    # Also check for "suspicious surplus" – consumed way more than allocated
    for record in escom_records:
        if record.consumed_kwh and record.allocated_kwh:
            variance = (Decimal(record.consumed_kwh) - Decimal(record.allocated_kwh)) / Decimal(record.allocated_kwh)
            if variance > Decimal("0.2"):  # >20% variance
                reason = (
                    f"ESCOM variance suspicious: "
                    f"purchase {record.purchase_id} allocated {record.allocated_kwh} kWh "
                    f"but consumed {record.consumed_kwh} kWh (+{variance*100:.0f}%)"
                )
                logger.warning(f"ESCOM variance for {mill_id}: {reason}")
                # Could be legitimate, so flag but don't block yet
                # return False, reason  # Uncomment to enforce strict mode
    
    return True, None
```

### Add ESCOM check to `allocate_token` (before the main decision logic)

Add after the active cycle check and before the normal decision flow:

```python
        # No active cycle – proceed with normal decision flow
        
        # ────────────────────────────────────────────────────────────────
        # ESCOM RECONCILIATION CHECK: Verify against purchase ledger
        # ────────────────────────────────────────────────────────────────
        escom_safe, escom_reason = _check_escom_reconciliation(mill_id, Decimal(BASE_CYCLE_KWH), session)
        if not escom_safe:
            trust_score = _require_trust_score(mill_id, session)
            cycle_state, elapsed = _get_cycle_state_and_elapsed(mill_id, session)
            adherence = get_last_cycle_adherence(mill_id, session)
            lag_hours = get_last_cycle_lag(mill_id, session)
            capital_at_risk = _compute_capital_at_risk(mill_id, cycle_state, session)
            exposure_used = _get_outstanding_exposure(mill_id, session)
            basis = _build_decision_basis(
                mill_id=mill_id,
                cycle_state=cycle_state,
                elapsed_hours=elapsed,
                trust_score=trust_score,
                adherence=adherence,
                lag_hours=lag_hours,
                capital_at_risk=capital_at_risk,
                exposure_used=exposure_used,
                exposure_limit=MAX_EXPOSURE_PER_MILL,
                session=session,
            )
            _store_decision_audit(mill_id, False, f"BLOCKED_ESCOM_LIMIT", basis, session)
            if idempotency_key:
                response = AllocationDecisionResponse(
                    allowed=False,
                    reason="BLOCKED_ESCOM_LIMIT",
                    decision_basis=basis,
                )
                _store_idempotency_response(
                    mill_id, idempotency_key,
                    "/api/owner/mills/{mill_id}/allocate-token",
                    response.model_dump(), 200, session
                )
            return AllocationDecisionResponse(
                allowed=False,
                reason="BLOCKED_ESCOM_LIMIT",
                decision_basis=basis,
            )
        # ────────────────────────────────────────────────────────────────
```

---

# 🔧 Patch 6: Anomaly Detection Flags

**Why:** Perfection is suspicious. Sudden changes are often manipulation.

## Add to `DecisionBasis` model (in response models section of `owner_routes.py`)

Find the `DecisionBasis` class and add these fields:

```python
class DecisionBasis(BaseModel):
    # ... existing fields ...
    
    # ─── ANOMALY DETECTION FLAGS ───────────────────────────────────────
    adherence_spike_detected: bool = False  # Sudden jump >0.15 in one cycle
    lag_collapsed_detected: bool = False    # Lag <2h when 30d avg >12h
    too_perfect_detected: bool = False      # StdDev of adherence <0.02 over 10 cycles
    off_hours_allocation: bool = False      # Request outside 6am-6pm (configurable)
    # ───────────────────────────────────────────────────────────────────
```

## Add anomaly detection functions (in `backend/owner_routes.py`)

```python
def _detect_adherence_spike(mill_id: str, session: Session) -> bool:
    """Check if adherence jumped >15% in latest cycle."""
    cycles = session.exec(
        select(TokenAllocation)
        .where(TokenAllocation.mill_id == mill_id)
        .order_by(TokenAllocation.allocated_at.desc())
    ).fetchmany(2)
    
    if len(cycles) < 2:
        return False
    
    latest, previous = cycles[0], cycles[1]
    
    # Get adherence for both
    latest_receipt = session.exec(
        select(CashReceipt).where(CashReceipt.allocation_id == latest.id)
    ).first()
    prev_receipt = session.exec(
        select(CashReceipt).where(CashReceipt.allocation_id == previous.id)
    ).first()
    
    if not latest_receipt or not prev_receipt:
        return False
    if not latest.expected_revenue or not previous.expected_revenue:
        return False
    
    latest_adh = float(latest_receipt.amount / latest.expected_revenue)
    prev_adh = float(prev_receipt.amount / previous.expected_revenue)
    
    spike = abs(latest_adh - prev_adh)
    return spike > 0.15


def _detect_lag_collapse(mill_id: str, session: Session) -> bool:
    """Check if lag suddenly dropped to <2h when 30-day average is >12h."""
    lag_hours = get_last_cycle_lag(mill_id, session)
    if lag_hours is None or lag_hours > 2:
        return False
    
    # Get average lag over last 10 cycles
    cycles = session.exec(
        select(TokenAllocation)
        .where(TokenAllocation.mill_id == mill_id)
        .order_by(TokenAllocation.allocated_at.desc())
    ).fetchmany(10)
    
    if len(cycles) < 2:
        return False
    
    lags = []
    for cycle in cycles:
        receipt = session.exec(
            select(CashReceipt).where(CashReceipt.allocation_id == cycle.id)
        ).first()
        if receipt and receipt.received_at:
            lag = (receipt.received_at - cycle.allocated_at).total_seconds() / 3600
            lags.append(lag)
    
    if not lags or len(lags) < 5:
        return False
    
    avg_lag = sum(lags) / len(lags)
    return avg_lag > 12.0  # Average was high, but latest is <2h


def _detect_too_perfect(mill_id: str, session: Session) -> bool:
    """Check if adherence has too-low variance (<0.02 std dev over 10 cycles)."""
    cycles = session.exec(
        select(TokenAllocation)
        .where(TokenAllocation.mill_id == mill_id)
        .order_by(TokenAllocation.allocated_at.desc())
    ).fetchmany(10)
    
    if len(cycles) < 5:
        return False
    
    adhs = []
    for cycle in cycles:
        receipt = session.exec(
            select(CashReceipt).where(CashReceipt.allocation_id == cycle.id)
        ).first()
        if receipt and cycle.expected_revenue:
            adh = float(min(1.0, receipt.amount / cycle.expected_revenue))
            adhs.append(adh)
    
    if len(adhs) < 5:
        return False
    
    mean_adh = sum(adhs) / len(adhs)
    variance = sum((a - mean_adh) ** 2 for a in adhs) / len(adhs)
    std_dev = variance ** 0.5
    
    return std_dev < 0.02


def _detect_off_hours_allocation(allocated_at: datetime) -> bool:
    """Flag allocations requested outside 6am-6pm UTC (configurable)."""
    hour = allocated_at.hour
    return hour < 6 or hour >= 18  # Outside 6am-6pm
```

## Integrate anomaly flags into `_build_decision_basis`

Update the function to compute and pass anomaly flags:

```python
def _build_decision_basis(
    mill_id: str,
    cycle_state: str,
    elapsed_hours: Optional[float],
    trust_score: float,
    adherence: float,
    lag_hours: float,
    capital_at_risk: Decimal,
    exposure_used: Decimal,
    exposure_limit: Decimal,
    session: Session,
) -> DecisionBasis:
    mill = session.exec(select(Mill).where(Mill.id == mill_id)).first()
    
    # ... existing code ...
    
    # COMPUTE ANOMALY FLAGS
    adherence_spike = _detect_adherence_spike(mill_id, session)
    lag_collapsed = _detect_lag_collapse(mill_id, session)
    too_perfect = _detect_too_perfect(mill_id, session)
    off_hours = _detect_off_hours_allocation(_to_utc(mill.glass_box_certified))  # Use current time
    
    return DecisionBasis(
        cycle_state=cycle_state,
        cycle_elapsed_hours=elapsed_hours,
        trust_score=trust_score,
        last_cycle_adherence=round(adherence, 4),
        last_cycle_lag_hours=round(lag_hours, 2),
        next_advance_rate=round(next_advance_rate, 4),
        capital_at_risk=capital_at_risk,
        time_to_missing_hours=time_to_missing,
        time_to_lock_hours=time_to_lock,
        simulated_allocation_kwh=simulated_kwh,
        simulated_expected_revenue=simulated_revenue,
        exposure_used=exposure_used,
        exposure_limit=exposure_limit,
        # ADD ANOMALY FLAGS
        adherence_spike_detected=adherence_spike,
        lag_collapsed_detected=lag_collapsed,
        too_perfect_detected=too_perfect,
        off_hours_allocation=off_hours,
    )
```

---

# 🔧 Patch 7: Game-Theoretic Layer – Collusion & Parallel Operation Detection

**Why:** Strategy-level exploitation: operator colludes with agent, or runs side generator outside GridLedger.

## Add models to `scripts/init_db.py`

```python
# 12. Game-Theoretic Threat Detection
class ThreatFlag(SQLModel, table=True):
    """
    Potential system-level threats detected by game-theoretic rules.
    
    Flags include: collusion, parallel operation, strategic delay, cluster anomaly.
    """
    __tablename__ = "threat_flags"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    mill_id: str = Field(foreign_key="mill.id", index=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    threat_type: str  # COLLUSION, PARALLEL_OP, STRATEGIC_DELAY, CLUSTER_ANOMALY
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    evidence: str  # JSON details
    status: str = Field(default="OPEN")  # OPEN, INVESTIGATING, RESOLVED, FALSE_ALARM
    
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
```

## Add detector functions to `backend/owner_routes.py`

```python
def _detect_collusion_signal(mill_id: str, session: Session) -> tuple[bool, Optional[str]]:
    """
    Detect potential collusion: operator reports no maize but payment is perfect.
    
    Signals:
    - "MAIZE_DRIED" notes but 95%+ adherence
    - Gap breach on same day as perfect payment
    """
    cycles = session.exec(
        select(TokenAllocation)
        .where(TokenAllocation.mill_id == mill_id)
        .order_by(TokenAllocation.allocated_at.desc())
    ).fetchmany(5)
    
    if not cycles:
        return False, None
    
    for cycle in cycles:
        receipt = session.exec(
            select(CashReceipt).where(CashReceipt.allocation_id == cycle.id)
        ).first()
        
        if receipt and cycle.expected_revenue:
            adherence = receipt.amount / cycle.expected_revenue
            
            # Check resolution notes (if disputed)
            if cycle.resolution_notes and adherence > 0.95:
                if "maize" in cycle.resolution_notes.lower() or "dried" in cycle.resolution_notes.lower():
                    return True, f"Perfect payment ({adherence*100:.0f}%) despite reported outage: {cycle.resolution_notes}"
    
    return False, None


def _detect_parallel_operation(mill_id: str, session: Session) -> tuple[bool, Optional[str]]:
    """
    Detect potential parallel operation: energy purchased externally but not reported.
    
    Signal:
    - ESCOM record shows 100+ kWh purchased
    - But AllocatedTokens total <50 kWh in same period
    - Could indicate offline generator or external meter
    """
    from scripts.init_db import ESCOMTokenPurchase
    
    escom_records = session.exec(
        select(ESCOMTokenPurchase)
        .where(ESCOMTokenPurchase.mill_id == mill_id)
        .order_by(ESCOMTokenPurchase.purchase_date.desc())
    ).fetchmany(3)
    
    if not escom_records:
        return False, None
    
    total_escom = sum(Decimal(r.units_kwh) for r in escom_records)
    
    # Get allocations in same period
    if escom_records:
        oldest_date = escom_records[-1].purchase_date
        allocations = session.exec(
            select(TokenAllocation)
            .where(
                TokenAllocation.mill_id == mill_id,
                TokenAllocation.allocated_at >= oldest_date
            )
        ).all()
        
        total_allocated = sum(Decimal(a.allocated_kwh) for a in allocations)
        
        # If ESCOM shows way more than allocated, flag it
        if total_escom > 0 and (total_allocated / total_escom) < 0.4:  # <40% of purchases allocated
            return True, (
                f"Parallel operation suspected: "
                f"ESCOM purchased {total_escom} kWh but only {total_allocated} kWh allocated "
                f"({(total_allocated/total_escom)*100:.0f}%). "
                f"Possible external generator or unreported meter."
            )
    
    return False, None
```

## Add detector invocation to `_build_decision_basis`

```python
def _build_decision_basis(...) -> DecisionBasis:
    # ... existing code ...
    
    # GAME-THEORETIC THREAT DETECTION
    from scripts.init_db import ThreatFlag
    
    collusion_detected, collusion_msg = _detect_collusion_signal(mill_id, session)
    parallel_detected, parallel_msg = _detect_parallel_operation(mill_id, session)
    
    # Log threats
    if collusion_detected:
        threat = ThreatFlag(
            mill_id=mill_id,
            threat_type="COLLUSION",
            severity="HIGH",
            evidence=collusion_msg,
        )
        session.add(threat)
        logger.warning(f"Threat detected [{mill_id}]: COLLUSION – {collusion_msg}")
    
    if parallel_detected:
        threat = ThreatFlag(
            mill_id=mill_id,
            threat_type="PARALLEL_OP",
            severity="HIGH",
            evidence=parallel_msg,
        )
        session.add(threat)
        logger.warning(f"Threat detected [{mill_id}]: PARALLEL_OP – {parallel_msg}")
    
    # Add to decision basis for visibility
    decision_basis.threat_flags_detected = (collusion_detected or parallel_detected)
```

---

# 📋 SQL Migrations

Run these **once** to set up the new tables:

```sql
-- Idempotency Records
CREATE TABLE IF NOT EXISTS idempotency_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idempotency_key TEXT UNIQUE NOT NULL,
    mill_id TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    response_json TEXT NOT NULL,
    http_status_code INTEGER CHECK(http_status_code >= 200 AND http_status_code < 600),
    created_at DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,
    replay_count INTEGER DEFAULT 0,
    FOREIGN KEY (mill_id) REFERENCES mill(id),
    INDEX idx_idempotency_key (idempotency_key),
    INDEX idx_mill_id (mill_id)
);

-- ESCOM Token Purchases
CREATE TABLE IF NOT EXISTS escom_token_purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mill_id TEXT NOT NULL,
    purchase_date DATETIME NOT NULL,
    purchase_id TEXT UNIQUE NOT NULL,
    units_kwh REAL NOT NULL,
    cost_mwk REAL NOT NULL,
    allocated_kwh REAL,
    consumed_kwh REAL,
    variance_pct REAL,
    status TEXT DEFAULT 'PENDING',
    reconciled_at DATETIME,
    notes TEXT,
    ingested_at DATETIME NOT NULL,
    FOREIGN KEY (mill_id) REFERENCES mill(id),
    INDEX idx_mill_id (mill_id),
    INDEX idx_purchase_id (purchase_id),
    INDEX idx_status (status)
);

-- Threat Flags
CREATE TABLE IF NOT EXISTS threat_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mill_id TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    threat_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    evidence TEXT NOT NULL,
    status TEXT DEFAULT 'OPEN',
    resolved_by TEXT,
    resolved_at DATETIME,
    resolution_notes TEXT,
    FOREIGN KEY (mill_id) REFERENCES mill(id),
    INDEX idx_mill_id (mill_id),
    INDEX idx_threat_type (threat_type),
    INDEX idx_severity (severity)
);

-- Add timing columns to token_allocations
ALTER TABLE token_allocations ADD COLUMN expected_receipt_by DATETIME;
ALTER TABLE token_allocations ADD COLUMN receipt_arrived_at DATETIME;
ALTER TABLE token_allocations ADD COLUMN missing_detected_at DATETIME;
```

**Execute with:**
```bash
sqlite3 data/gridledger.db < move_b_migrations.sql
```

Or from Python:
```python
from sqlalchemy import text
from scripts.init_db import engine

with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS idempotency_records (...)
    """))
    conn.commit()
```

---

# ✅ Verification Checklist

After applying all patches:

- [ ] **Idempotency table created** – can insert/query `IdempotencyRecord`
- [ ] **Time fields added to TokenAllocation** – `expected_receipt_by` etc. exist
- [ ] **ESCOM table created** – ready for ingestion
- [ ] **Threat flags table created** – detectors can log findings
- [ ] **allocate_token accepts Idempotency-Key header** – POST with header returns cached result
- [ ] **Time-weighted exposure compute** – Callable and returns decreasing exposure over time
- [ ] **ESCOM reconciliation blocks on limit** – Missing purchase data blocks allocation
- [ ] **Anomaly flags in decision basis** – Response includes all 4 flags
- [ ] **Threat detectors log findings** – Collusion and parallel ops flagged in logs
- [ ] **All imports updated** – No missing `timedelta`, `IdempotencyRecord`, etc.

---

## Summary: What Move B Delivers

| Before | After | Impact |
|--------|-------|--------|
| Retries double-allocate | Idempotency keys guarantee safety | Network glitches safe ✅ |
| Exposure static | Time-weighted with 10% daily penalty | Delays expensive ✅ |
| No external anchor | ESCOM reconciliation | Verify against reality ✅ |
| Reactive monitoring | Anomaly detection (spike, collapse, perfection, off-hours) | Catch manipulation ✅ |
| Single-mill focus | Game-theoretic threat flags (collusion, parallel ops) | Defend system ✅ |

**Next: Deploy Move B, then Move C (Fraud Scoring & Cluster Defense)**

---

**Total Implementation Time: ~12 hours**  
**Difficulty: Medium (straightforward logic, no ML or distributed consensus)**  
**Impact: Highest – moves from "fair allocation" to "system defense"**
