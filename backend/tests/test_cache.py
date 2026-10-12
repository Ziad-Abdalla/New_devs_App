"""Client B: "numbers that look like they belong to another company" on refresh.

prop-001 exists for both tenants (Sunset's Beach House Alpha, Ocean's Mountain
Lodge Beta, which has no bookings). Whoever loads it first must not decide what
the other tenant sees.
"""
from app.services import cache

from conftest import run


def _load_both(first, second):
    async def go():
        results = {}
        for tenant in (first, second):
            results[tenant] = await cache.get_revenue_summary("prop-001", tenant)
        return results

    return run(go)


def test_prop_001_is_isolated_per_tenant_in_both_orders(fake_redis):
    for first, second in (("tenant-a", "tenant-b"), ("tenant-b", "tenant-a")):
        fake_redis.store.clear()
        results = _load_both(first, second)

        assert results["tenant-a"]["tenant_id"] == "tenant-a"
        assert results["tenant-a"]["count"] == 4
        assert results["tenant-b"]["tenant_id"] == "tenant-b"
        assert results["tenant-b"]["count"] == 0
        assert len(fake_redis.store) == 2  # one entry per tenant


class DeadRedis:
    async def get(self, key):
        raise ConnectionError("redis is down")

    async def setex(self, key, ttl, value):
        raise ConnectionError("redis is down")


def test_redis_down_falls_back_to_the_database(monkeypatch):
    monkeypatch.setattr(cache, "redis_client", DeadRedis())

    result = run(lambda: cache.get_revenue_summary("prop-001", "tenant-a"))

    assert result["tenant_id"] == "tenant-a"
    assert result["count"] == 4
