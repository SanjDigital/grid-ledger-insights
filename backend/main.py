from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel
from backend.api_reports import (
    get_mill_status,
    get_mill_performance_summary,
    get_mill_credit_metrics,
    get_mill_credit_history,
    get_capital_tier_recommendation,
)
from typing import Optional
import os

app = FastAPI()

API_KEY = os.getenv('GRIDLEDGER_API_KEY', 'letmein123')

def validate_api_key(x_api_key: Optional[str] = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail='Invalid API Key')
    return True


class ResolveDisputeRequest(BaseModel):
    """Request body for admin dispute resolution endpoint."""
    resolved_by: str
    resolution_notes: str


@app.get("/api/v1/mills/{mill_id}/status")
def mill_status(mill_id: str, authorized: bool = Depends(validate_api_key)):
    return get_mill_status(mill_id)


@app.get("/api/v1/mills/{mill_id}/performance")
def mill_performance(mill_id: str, authorized: bool = Depends(validate_api_key)):
    return get_mill_performance_summary(mill_id)


@app.get("/api/v1/mills/{mill_id}/credit/dce")
def mill_credit_envelope(mill_id: str, authorized: bool = Depends(validate_api_key)):
    """Get Dynamic Credit Envelope (DCE) and capital control metrics."""
    return get_mill_credit_metrics(mill_id)


@app.get("/api/v1/mills/{mill_id}/credit/history")
def mill_credit_history(mill_id: str, days: int = 30, authorized: bool = Depends(validate_api_key)):
    """Get historical DCE calculations."""
    return get_mill_credit_history(mill_id, days=days)


@app.get("/api/v1/mills/{mill_id}/credit/tier")
def mill_capital_tier(mill_id: str, authorized: bool = Depends(validate_api_key)):
    """Get financing tier recommendation based on DCE and trust metrics."""
    return get_capital_tier_recommendation(mill_id)


@app.get("/api/v1/operators/integrity")
def operators_integrity(authorized: bool = Depends(validate_api_key)):
    from backend.api_reports import get_operator_integrity
    return get_operator_integrity()


@app.get("/api/v1/mills/{mill_id}/capital/exposure")
def mill_capital_exposure(mill_id: str, authorized: bool = Depends(validate_api_key)):
    """Get capital at risk exposure summary for a mill."""
    from backend.api_reports import get_capital_exposure_summary
    return get_capital_exposure_summary(mill_id)


@app.get("/api/v1/mills/{mill_id}/capital/events")
def mill_capital_events(
    mill_id: str,
    days: int = 30,
    action_type: str = None,
    authorized: bool = Depends(validate_api_key),
):
    """Get capital control events (cash sweep, credit compression, pricing escalation)."""
    from backend.api_reports import get_capital_events
    return get_capital_events(mill_id, days=days, action_type=action_type)


@app.get("/api/v1/mills/{mill_id}/accountability/ear")
def mill_ear_accountability(mill_id: str, authorized: bool = Depends(validate_api_key)):
    """Get Energy Accountability Ratio (EAR) status and tier classification."""
    from backend.api_reports import get_ear_accountability_status
    return get_ear_accountability_status(mill_id)


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN ENDPOINTS — REQUIRES AUTHENTICATION & AUTHORIZATION
# ─────────────────────────────────────────────────────────────────────────────
# ⚠️  WARNING: These endpoints modify operational state and require:
#     - API key authentication (currently API key header validation)
#     - Role-based access control (TODO: implement admin role verification)
#     - Audit logging (TODO: implement operation audit trail)
#
# Phase 1: Basic API key protection.
# Phase 2: Implement OAuth2/JWT with role-based access control (RBAC)
#          and detailed audit logging for all admin operations.
# ─────────────────────────────────────────────────────────────────────────────


@app.post("/admin/resolve-dispute/{allocation_id}")
def admin_resolve_dispute(
    allocation_id: int,
    request: ResolveDisputeRequest,
    authorized: bool = Depends(validate_api_key)
):
    """
    [ADMIN] Mark a cycle allocation as DISPUTED pending manual review.
    
    A cycle becomes disputed when:
    - Cash remitted doesn't match expected revenue (variance beyond tolerance)
    - Cash receipt arrives late (past MISSING_CYCLE_TIMEOUT_HOURS)
    - Operator challenges allocation decision
    
    Once marked DISPUTED:
    - get_last_cycle_adherence() returns 0.0 (penalty on next advance rate)
    - Admin notes are recorded with operator and timestamp
    - Mill faces reduced capital allocation in next cycle
    
    Request body:
    {
        "resolved_by": "admin-id",
        "resolution_notes": "Discrepancy: expected 50000, received 45000"
    }
    
    Returns:
        {
            "status": "SUCCESS|ERROR",
            "allocation_id": int,
            "allocation_status": "DISPUTED",
            "resolved_by": str,
            "resolved_at": ISO datetime,
            "resolution_notes": str
        }
    
    Raises:
        HTTP 401: Invalid API key
        HTTP 404: Allocation not found (via return status)
        HTTP 400: Allocation already CLOSED or DISPUTED
    """
    from backend.cycle_manager import resolve_dispute
    
    result = resolve_dispute(
        allocation_id=allocation_id,
        resolved_by=request.resolved_by,
        resolution_notes=request.resolution_notes
    )
    
    # If error retrieving, return 404; if state error, return 400
    if result["status"] == "ERROR":
        if "not found" in result.get("error", "").lower():
            raise HTTPException(status_code=404, detail=result["error"])
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    
    return result
