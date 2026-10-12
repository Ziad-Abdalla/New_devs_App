"""Only tokens signed with the server's key get in."""
import asyncio
from datetime import datetime, timedelta

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.config import settings
from app.core.auth import authenticate_request


def authenticate(token):
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    return asyncio.run(authenticate_request(creds))


def make_token(email, key):
    payload = {
        "id": "x",
        "email": email,
        "aud": "authenticated",
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    return jwt.encode(payload, key, algorithm="HS256")


@pytest.mark.parametrize(
    "token",
    [
        "mock-token-123",  # static dev token the mock client used to accept as a tenant-a admin
        make_token("candidate@propertyflow.com", "not-the-server-key"),  # forged signature
    ],
    ids=["mock-token-123", "forged-signature"],
)
def test_unverified_tokens_are_rejected(token):
    with pytest.raises(HTTPException) as exc:
        authenticate(token)
    assert exc.value.status_code == 401


def test_properly_signed_client_token_still_works():
    user = authenticate(make_token("ocean@propertyflow.com", settings.secret_key))
    assert user.tenant_id == "tenant-b"


def test_signed_token_for_unmapped_user_is_forbidden():
    # Valid signature, but the email maps to no tenant: stop at auth, for every endpoint
    with pytest.raises(HTTPException) as exc:
        authenticate(make_token("stranger@example.com", settings.secret_key))
    assert exc.value.status_code == 403
