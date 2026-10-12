import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from app.services.cache import get_revenue_summary
from app.core.auth import authenticate_request as get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        # No tenant means no data, never a guessed/default tenant
        raise HTTPException(status_code=403, detail="User is not assigned to a tenant")
    
    try:
        revenue_data = await get_revenue_summary(property_id, tenant_id)
    except Exception:
        # Log the real cause, then fail loudly: no made-up numbers on a finance screen.
        # Nothing was cached, because cache.py only stores successful results.
        logger.exception(f"Revenue summary failed for {property_id} (tenant {tenant_id})")
        raise HTTPException(status_code=503, detail="Revenue data temporarily unavailable")

    if revenue_data is None:
        # Unknown id or another tenant's property: same answer for both, so a
        # client can't probe which ids exist in other tenants
        raise HTTPException(status_code=404, detail="Property not found")
    
    # 'total' is already rounded to cents as a Decimal string (reservations.to_cents).
    # A 2-decimal amount survives the trip through a JSON number unchanged, so the
    # response keeps its existing numeric shape and the frontend only formats it.
    total_revenue_float = float(revenue_data['total'])
    
    return {
        "property_id": revenue_data['property_id'],
        "total_revenue": total_revenue_float,
        "currency": revenue_data['currency'],
        "reservations_count": revenue_data['count']
    }
