"""The dashboard reads real numbers from Postgres, through one shared engine."""
from app.core.database_pool import db_pool
from app.services import reservations

from conftest import run


def test_revenue_comes_from_the_database():
    # Seed: Sunset prop-001 has 4 bookings totalling 2250.000 (the old mock said 1000.00 / 3)
    result = run(lambda: reservations.calculate_total_revenue("prop-001", "tenant-a"))
    assert result["count"] == 4
    assert result["total"] == "2250.00"


def test_engine_is_created_once_not_per_request():
    async def two_requests():
        await reservations.calculate_total_revenue("prop-001", "tenant-a")
        first = db_pool.engine
        await reservations.calculate_total_revenue("prop-002", "tenant-a")
        return first, db_pool.engine

    first, second = run(two_requests)
    assert first is not None
    assert first is second
