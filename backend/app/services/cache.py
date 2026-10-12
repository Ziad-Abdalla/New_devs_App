import json
import logging
import redis.asyncio as redis
from typing import Dict, Any
import os

logger = logging.getLogger(__name__)

# Initialize Redis client (typically configured centrally).
# Short timeouts: the cache is an optimisation, so a slow or dead Redis should
# cost one second, not hang the dashboard.
redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    socket_connect_timeout=1,
    socket_timeout=1,
)

async def get_revenue_summary(property_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Fetches revenue summary, utilizing caching to improve performance.
    """
    # Property ids are only unique per tenant (PK is (id, tenant_id)), so the
    # tenant must be part of the key or tenants read each other's cached totals.
    cache_key = f"revenue:{tenant_id}:{property_id}"
    
    # Try to get from cache. If Redis is down, fall through to the database
    # (fail open for an optimisation; tenancy and auth checks fail closed).
    try:
        cached = await redis_client.get(cache_key)
    except Exception as e:
        logger.warning(f"Redis read failed for {cache_key}, using the database: {e.__class__.__name__}: {e}")
        cached = None
    if cached:
        return json.loads(cached)
    
    # Revenue calculation is delegated to the reservation service.
    from app.services.reservations import calculate_total_revenue
    
    # Calculate revenue
    result = await calculate_total_revenue(property_id, tenant_id)
    
    # Cache the result for 5 minutes (only reached on success, so errors are never cached)
    try:
        await redis_client.setex(cache_key, 300, json.dumps(result))
    except Exception as e:
        logger.warning(f"Redis write failed for {cache_key}: {e.__class__.__name__}: {e}")
    
    return result
