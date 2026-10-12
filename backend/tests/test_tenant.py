"""Users without a tenant mapping get no tenant and no data (fail closed)."""
import asyncio

import pytest
from fastapi import HTTPException

from app.api.v1 import dashboard
from app.core.tenant_resolver import TenantResolver

from conftest import User


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
