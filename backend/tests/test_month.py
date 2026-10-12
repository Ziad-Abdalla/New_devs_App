"""Client A: "different totals for March".

res-tz-1 checks in 2024-02-29 23:30 UTC = 2024-03-01 00:30 in Paris. Rule: a
booking counts in the month of its check-in in the property's local time.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1 import dashboard
from app.core.auth import authenticate_request

from conftest import User, run


def summary(property_id, tenant, month, year):
    return run(lambda: dashboard.get_dashboard_summary(
        property_id, current_user=User(tenant), month=month, year=year))


def test_paris_march_includes_the_leap_day_check_in(fake_redis):
    march = summary("prop-001", "tenant-a", 3, 2024)
    assert (march["total_revenue"], march["reservations_count"]) == (2250.0, 4)  # UTC bounds: 1000.0 / 3

    february = summary("prop-001", "tenant-a", 2, 2024)
    assert (february["total_revenue"], february["reservations_count"]) == (0.0, 0)  # UTC bounds: 1250.0 / 1

    # Ocean's prop-001 shares the id but has no bookings
    assert summary("prop-001", "tenant-b", 3, 2024)["reservations_count"] == 0


def test_month_and_year_are_validated():
    app = FastAPI()
    app.include_router(dashboard.router, prefix="/api/v1")
    app.dependency_overrides[authenticate_request] = lambda: User("tenant-a")
    client = TestClient(app)

    url = "/api/v1/dashboard/summary?property_id=prop-001"
    assert client.get(url + "&month=3").status_code == 400  # month without year
    assert client.get(url + "&year=2024").status_code == 400  # year without month
    assert client.get(url + "&month=13&year=2024").status_code == 422
