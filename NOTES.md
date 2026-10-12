# Notes: revenue dashboard bugs

## The three complaints, and what caused them

- **Client A, "March totals don't match"**: the dashboard never read the database. Every request fell into an `except` that returned a hard-coded table. Its prop-001 value, 1000.00 / 3, is what you get if you count March in UTC, which drops one booking (`res-tz-1`, 23:30 UTC on 29 Feb = 00:30 on 1 March in Paris). The real figure is 2250.00 / 4.
- **Client B, "another company's numbers on refresh"**: the Redis key was `revenue:{property_id}` with no tenant. `prop-001` exists for both companies, so whoever loaded it first decided what the other saw for 5 minutes. The mock table also ignored the tenant.
- **Finance, "a few cents off"**: I couldn't reproduce a wrong total with the seed data, because every total is already whole cents. The code path was still wrong: the sum went out unrounded, got turned into a float, and was then rounded in the browser with `Math.round(x*100)/100`. That gets 1.005 wrong (shows 1.00), and rounding each booking first turns 333.333 x 3 into 999.99.

## What I changed (one commit per fix, see `git log`)

1. DB pool connects: four faults (greenlet missing, non-existent settings fields, sync pool class on an async engine, `async def get_session`). The engine is created once, not per request.
2. No mock data: errors become a 503, the real cause is logged, and nothing is cached.
3. DB timeouts: a stuck DB gives a 503 in about 5 s instead of hanging.
4. Cache key is `revenue:{tenant_id}:{property_id}`.
5. If Redis is down, the dashboard reads from the DB instead of failing. The cache fails open because it's only an optimisation; tenant and auth checks fail closed.
6. Money: sum exactly in SQL, round once at the end, half-up, to cents (`to_cents`). The API still returns a number; the browser only formats it.
7. Auth: a token that fails verification gets a 401. Before, it fell through to a mock client that accepted the literal `mock-token-123` and unsigned JWTs.
8. Login: only the two client accounts get tokens. Before, `candidate@propertyflow.com` with any password got a token for Sunset's tenant.
9. Unknown users get no tenant and a 403, enforced in auth for every endpoint.
10. Another tenant's property, or an unknown id, gets a 404, and nothing is cached.
11. Month view: `?month=3&year=2024` on the summary endpoint. The month bounds are converted into the property's timezone in SQL. The dashboard has a Period picker for it (default: All time), and the card says which period it shows.
12. Property dropdown comes from a new tenant-scoped `/api/v1/dashboard/properties`. The frontend's existing `getProperties()` calls `/api/v1/properties`, which this backend doesn't have.
13. RevenueSummary ignores stale responses when you switch property, and clears old errors.
14. Logs never include the DB URL/password or token text.
15. Removed the unused WebSocket auth helper: it trusted tokens without checking the signature.
16. The frontend no longer sends an `X-Simulated-Tenant` header. The tenant only comes from the verified token.
17. Removed the hard-coded "12%" trend badge (it was a constant, shown as a real trend). Totals use one number format for every browser.

**March rule (my assumption, to confirm with finance):** a booking counts in full in the month of its check-in date, in the property's local time. If finance books revenue night by night, that's their call.

## Numbers (match psql)

| | all time | March 2024 (local) |
|---|---|---|
| Sunset prop-001 Beach House Alpha | 2250.00 / 4 | 2250.00 / 4 (UTC would give 1000.00 / 3) |
| Sunset prop-002 / prop-003 | 4975.50 / 4, 6100.50 / 2 | same |
| Ocean prop-001 Mountain Lodge Beta | 0.00 / 0 | 0.00 / 0 |
| Ocean prop-004 / prop-005 | 1776.50 / 4, 3256.00 / 3 | same |

## Tests

```bash
docker compose up --build -d
docker compose exec backend pip install -q -r requirements-dev.txt
docker compose exec backend python -m pytest -q        # all pass
```
The tests use the seeded Postgres (read-only) and a fake Redis. Run against the original code, almost all of them fail (the money file can't even import); the few that pass are deliberate controls (the real logins still work).

## Questions for the business

- `res-dec-1/2/3` are three bookings at Beach House Alpha with overlapping dates (15-18, 16-19, 17-20 March). Are those real stays, or a double booking? There's no status column, so I can't tell. I counted all three.
- Which month does a stay belong to: check-in, nightly, or check-out?
- Is everything really USD? Paris properties are stored with the default currency.

## Seen but not fixed

- RLS is enabled with no policies, and the app connects as the `postgres` superuser, so isolation depends on every query's `WHERE tenant_id`. The fix would be a non-superuser role plus policies.
- Hard-coded `SECRET_KEY`; the challenge passwords are compared in plain text.
- Currency is hard-coded to "USD".
- No cache invalidation when bookings change: TTL only, and there's no write path in this repo.
