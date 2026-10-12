"""A database failure is an error (503), never invented numbers, and never cached."""
import pytest
from fastapi import HTTPException

from app.api.v1 import dashboard
from app.config import settings

from conftest import User, run

UNREACHABLE_DB = "postgresql://postgres:postgres@127.0.0.1:1/propertyflow"


def test_db_down_returns_503_and_caches_nothing(monkeypatch, fake_redis):
    monkeypatch.setattr(settings, "database_url", UNREACHABLE_DB)

    with pytest.raises(HTTPException) as exc:
        run(lambda: dashboard.get_dashboard_summary("prop-001", current_user=User("tenant-b")))

    assert exc.value.status_code == 503
    assert fake_redis.store == {}
