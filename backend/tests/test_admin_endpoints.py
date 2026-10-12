"""Operational endpoints that change shared state need an admin login."""
import asyncio

import pytest
from fastapi.testclient import TestClient

from app.api.v1.login import LoginRequest, login
from app.main import app

ADMIN_ONLY = [
    "/api/v1/circuit-breaker/reset",
    "/api/v1/circuit-breaker/configure",
    "/api/v1/fallback/clear-cache",
]


@pytest.mark.parametrize("path", ADMIN_ONLY)
def test_admin_endpoints_refuse_anonymous_and_client_users(path):
    client = TestClient(app)
    assert client.post(path, json={}).status_code in (401, 403)

    token = asyncio.run(login(LoginRequest(email="ocean@propertyflow.com", password="client_b_2024"))).access_token
    response = client.post(path, json={}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
