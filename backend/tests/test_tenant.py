"""Users without a tenant mapping get no tenant and no data (fail closed)."""
import asyncio

import pytest
from fastapi import HTTPException

from app.api.v1 import dashboard
from app.core.tenant_resolver import TenantResolver

from conftest import User, run


def test_unknown_user_gets_no_tenant_and_a_403(monkeypatch):
    tenant = asyncio.run(TenantResolver.resolve_tenant_id(user_id="x", user_email="stranger@example.com"))
    assert tenant is None  # used to be "tenant-a"

    calls = []

    async def spy(*args, **kwargs):
        calls.append(args)

    monkeypatch.setattr(dashboard, "get_revenue_summary", spy)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(dashboard.get_dashboard_summary("prop-001", current_user=User(tenant)))
    assert exc.value.status_code == 403
    assert calls == []  # never reached the data layer


@pytest.mark.parametrize(
    "property_id, tenant",
    [
        ("prop-002", "tenant-b"),  # Sunset's property, asked for by Ocean
        ("prop-999", "tenant-a"),  # does not exist
    ],
)
def test_other_tenants_or_unknown_property_is_404_and_not_cached(property_id, tenant, fake_redis):
    with pytest.raises(HTTPException) as exc:
        run(lambda: dashboard.get_dashboard_summary(property_id, current_user=User(tenant)))
    assert exc.value.status_code == 404
    assert fake_redis.store == {}


def test_property_list_is_scoped_to_the_tenant():
    a = run(lambda: dashboard.get_dashboard_properties(current_user=User("tenant-a")))
    b = run(lambda: dashboard.get_dashboard_properties(current_user=User("tenant-b")))
    assert [p["name"] for p in a] == ["Beach House Alpha", "City Apartment Downtown", "Country Villa Estate"]
    assert [p["name"] for p in b] == ["Mountain Lodge Beta", "Lakeside Cottage", "Urban Loft Modern"]

    with pytest.raises(HTTPException) as exc:
        run(lambda: dashboard.get_dashboard_properties(current_user=User(None)))
    assert exc.value.status_code == 403
