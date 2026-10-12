"""Only the two assignment clients, with their passwords, get a token."""
import asyncio

import pytest
from fastapi import HTTPException

from app.api.v1.login import LoginRequest, login


def do_login(email, password):
    return asyncio.run(login(LoginRequest(email=email, password=password)))


@pytest.mark.parametrize(
    "email, password",
    [
        ("candidate@propertyflow.com", "anything"),  # mock user: used to get a tenant-a token
        ("sunset@propertyflow.com", "wrong-password"),
    ],
)
def test_other_logins_are_rejected(email, password):
    with pytest.raises(HTTPException) as exc:
        do_login(email, password)
    assert exc.value.status_code == 401


def test_client_login_still_works():
    response = do_login("sunset@propertyflow.com", "client_a_2024")
    assert response.user["tenant_id"] == "tenant-a"
    assert response.access_token
