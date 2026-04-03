"""
Token Gateway: Token Allocation and Cash Receipt Management

Implements the per-cycle token allocation control system.
- allocate_token(): Create a token allocation (59.9 kWh)
- record_cash_receipt(): Record operator cash remittance
"""

import logging
from datetime import datetime, timezone, timedelta
from sqlmodel import Session, select
from scripts.init_db import TokenAllocation, CashReceipt, Mill
from backend.config import TOLERANCE_PERCENT, DISPUTED_ADHERENCE_PENALTY, MISSING_CYCLE_TIMEOUT_HOURS

logger = logging.getLogger(__name__)


class TokenGateway:
    """Control interface for per-cycle token allocation."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def allocate_token(self, mill_id: str) -> dict:
        """
        Allocate 59.9 kWh token to a mill.
        
        Expected revenue is computed using mill.revenue_rate_per_kwh (what operator charges customers),
        NOT ESCOM's energy cost tariff.
        
        Guards:
        - Reject if a PENDING allocation already exists for this mill
        - (Previous cycle must be CLOSED or MISSING before next allocation)
        
        Returns:
        {
            'allocation_id': int,
            'allocated_kwh': 59.9,
            'expected_revenue': float,
            'revenue_rate_per_kwh': float,
            'status': 'PENDING'
        }
        
        Raises:
        - ValueError: If PENDING allocation already exists, or if mill not found
        """
        # Check for existing pending allocation
        pending = self.session.exec(
            select(TokenAllocation).where(
                TokenAllocation.mill_id == mill_id,
                TokenAllocation.status == "PENDING"
            )
        ).first()
        
        if pending:
            raise ValueError(
                f"Mill {mill_id} already has a pending allocation (ID {pending.id}). "
                f"Previous cycle must be completed before next allocation."
            )
        
        # Get mill to retrieve revenue rate (what operator charges customers)
        mill = self.session.exec(
            select(Mill).where(Mill.id == mill_id)
        ).first()
        
        if not mill:
            raise ValueError(f"Mill {mill_id} not found")
        
        if not mill.revenue_rate_per_kwh:
            raise ValueError(f"Mill {mill_id} has no revenue_rate_per_kwh configured")
        
        allocated_kwh = 59.9
        expected_revenue = allocated_kwh * mill.revenue_rate_per_kwh
        
        allocation = TokenAllocation(
            mill_id=mill_id,
            allocated_kwh=allocated_kwh,
            expected_revenue=expected_revenue,
            status="PENDING"
        )
        
        self.session.add(allocation)
        self.session.commit()
        self.session.refresh(allocation)
        
        logger.info(
            f"Allocated token {allocation.id} to mill {mill_id}, "
            f"allocated_kwh={allocated_kwh}, revenue_rate={mill.revenue_rate_per_kwh}, expected_revenue={expected_revenue:.2f}"
        )
        
        return {
            "allocation_id": allocation.id,
            "allocated_kwh": allocated_kwh,
            "revenue_rate_per_kwh": mill.revenue_rate_per_kwh,
            "expected_revenue": expected_revenue,
            "status": allocation.status
        }
    
    def record_cash_receipt(self, allocation_id: int, amount: float) -> dict:
        """
        Record operator cash remittance for a cycle.
        
        Verifications:
        - Allocation exists and is PENDING
        - Variance within tolerance (±5%)
        
        Returns:
        {
            'receipt_id': int,
            'allocation_id': int,
            'status': 'CLOSED' (or 'DISPUTED'),
            'variance_percent': float,
            'resolution_needed': bool
        }
        
        Side effects:
        - Updates allocation status (CLOSED or DISPUTED)
        - Creates CashReceipt record
        
        Raises:
        - ValueError: If allocation not found or not in PENDING state
        """
        allocation = self.session.get(TokenAllocation, allocation_id)
        
        if not allocation:
            raise ValueError(f"Allocation {allocation_id} not found")
        
        if allocation.status == "MISSING":
            raise ValueError(
                f"Allocation {allocation_id} is MISSING. "
                f"Contact manager to resolve."
            )
        
        if allocation.status != "PENDING":
            raise ValueError(
                f"Allocation {allocation_id} is already {allocation.status}. "
                f"Cannot record receipt for non-PENDING allocation."
            )
        
        # Compute variance
        variance = amount - allocation.expected_revenue
        variance_percent = (variance / allocation.expected_revenue) * 100 if allocation.expected_revenue > 0 else 0
        
        # Determine status based on variance
        if abs(variance_percent) > TOLERANCE_PERCENT:
            new_status = "DISPUTED"
        else:
            new_status = "CLOSED"
        
        # Record receipt
        receipt = CashReceipt(
            allocation_id=allocation.id,
            amount=amount,
            notes=f"Variance {variance_percent:.2f}%"
        )
        
        self.session.add(receipt)
        
        # Update allocation status
        allocation.status = new_status
        self.session.add(allocation)
        
        self.session.commit()
        self.session.refresh(receipt)
        
        logger.info(
            f"Recorded cash receipt {receipt.id} for allocation {allocation_id}, "
            f"amount={amount:.2f}, variance_percent={variance_percent:.2f}%, "
            f"status={new_status}"
        )
        
        return {
            "receipt_id": receipt.id,
            "allocation_id": allocation.id,
            "status": new_status,
            "variance_percent": variance_percent,
            "resolution_needed": (new_status == "DISPUTED")
        }


# Module-level convenience functions
def allocate_token(session: Session, mill_id: str) -> dict:
    """
    Convenience wrapper for TokenGateway.allocate_token().
    
    Revenue rate is automatically fetched from the Mill's revenue_rate_per_kwh field.
    """
    gateway = TokenGateway(session)
    return gateway.allocate_token(mill_id)


def record_cash_receipt(session: Session, allocation_id: int, amount: float) -> dict:
    """Convenience wrapper for TokenGateway.record_cash_receipt()."""
    gateway = TokenGateway(session)
    return gateway.record_cash_receipt(allocation_id, amount)
