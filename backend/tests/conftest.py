"""Test helpers for the revenue dashboard.

Run inside the backend container (it can reach the seeded Postgres):
    docker compose exec backend pip install -q -r requirements-dev.txt
    docker compose exec backend python -m pytest -q

DB-backed tests only read the seed data. Redis is replaced by an in-memory
fake so the tests never touch the real cache.
"""
import asyncio

import pytest

from app.core.database_pool import db_pool


class FakeRedis:
    """Just enough of redis.asyncio for services/cache.py."""

    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def setex(self, key, ttl, value):
        self.store[key] = value


class User:
    """Stand-in for the AuthenticatedUser the auth dependency returns."""

    def __init__(self, tenant_id):
        self.tenant_id = tenant_id


@pytest.fixture(autouse=True)
def fresh_pool():
    # Each test runs its own event loop (asyncio.run) and asyncpg connections
    # belong to the loop that opened them, so every test starts with no engine.
    db_pool.engine = None
    db_pool.session_factory = None
    yield
    db_pool.engine = None
    db_pool.session_factory = None


def run(coro_factory):
    """Run an async test body, then dispose the engine on the same loop."""

    async def go():
        try:
            return await coro_factory()
        finally:
            await db_pool.close()

    return asyncio.run(go())


@pytest.fixture
def fake_redis(monkeypatch):
    from app.services import cache

    fake = FakeRedis()
    monkeypatch.setattr(cache, "redis_client", fake)
    return fake
