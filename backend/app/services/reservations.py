from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List, Optional

CENTS = Decimal("0.01")

def to_cents(amount) -> Decimal:
    """Round a money amount once, at the end, to cents (half-up, finance convention).

    Amounts are stored as NUMERIC(10,3). Sum the exact values first and call this on
    the total; rounding each row first drifts (333.333 x 3 -> 999.99 instead of 1000.00).
    """
    return Decimal(str(amount)).quantize(CENTS, rounding=ROUND_HALF_UP)

async def calculate_monthly_revenue(property_id: str, tenant_id: str, month: int, year: int) -> Optional[Dict[str, Any]]:
    """
    Calculates revenue for a specific month.

    Rule: a booking counts, in full, in the month of its check-in date in the
    property's local time (properties.timezone). A check-in at 2024-02-29 23:30 UTC
    is 1 March 00:30 in Paris, so it is March revenue for a Paris property.
    """
    # Local wall-clock month bounds (half-open); the query converts them to instants
    # in each property's own timezone.
    start_date = datetime(year, month, 1)
    if month < 12:
        end_date = datetime(year, month + 1, 1)
    else:
        end_date = datetime(year + 1, 1, 1)

    return await calculate_total_revenue(property_id, tenant_id, local_start=start_date, local_end=end_date)

async def calculate_total_revenue(
    property_id: str,
    tenant_id: str,
    local_start: Optional[datetime] = None,
    local_end: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    """
    Aggregates revenue from database: all time, or check-ins in [local_start, local_end)
    in the property's local time.

    Returns None when the tenant has no property with this id (unknown id, or
    another tenant's property), so the endpoint can answer 404.

    Errors are not caught here. The old handler swallowed them and returned a
    hard-coded, tenant-blind mock table; a failure must reach the endpoint as an error.
    """
    # Use the shared module-level pool (one engine per process, not one per request)
    from app.core.database_pool import db_pool
    
    # Initialize pool if needed (no-op after the first call)
    await db_pool.initialize()
    
    if db_pool.session_factory:
        async with db_pool.get_session() as session:
            # Use SQLAlchemy text for raw SQL
            from sqlalchemy import text
            
            # Month filter: `local midnight AT TIME ZONE p.timezone` is the UTC instant of
            # local midnight (DST-aware), so the column itself stays untouched and an index
            # on check_in_date can be used. Static SQL text only; values are bound params.
            month_filter = ""
            if local_start is not None:
                month_filter = """
                    AND r.check_in_date >= (CAST(:local_start AS timestamp) AT TIME ZONE p.timezone)
                    AND r.check_in_date <  (CAST(:local_end AS timestamp) AT TIME ZONE p.timezone)
                """

            # Start from the tenant's own property row: no row means unknown id or another
            # tenant's property. LEFT JOIN keeps properties with no bookings (0.00).
            # Join on (id, tenant_id): property ids repeat across tenants.
            query = text(f"""
                SELECT
                    COALESCE(SUM(r.total_amount), 0) as total_revenue,
                    COUNT(r.id) as reservation_count
                FROM properties p
                LEFT JOIN reservations r
                    ON r.property_id = p.id AND r.tenant_id = p.tenant_id
                    {month_filter}
                WHERE p.id = :property_id AND p.tenant_id = :tenant_id
                GROUP BY p.id
            """)

            params = {"property_id": property_id, "tenant_id": tenant_id}
            if local_start is not None:
                params.update(local_start=local_start, local_end=local_end)
            result = await session.execute(query, params)
            row = result.fetchone()
            
            if row is None:
                return None

            # SUM over NUMERIC is exact in Postgres; round only the final total
            total_revenue = to_cents(row.total_revenue)
            return {
                "property_id": property_id,
                "tenant_id": tenant_id,
                "total": str(total_revenue),
                "currency": "USD", 
                "count": row.reservation_count
            }
    else:
        raise Exception("Database pool not available")
