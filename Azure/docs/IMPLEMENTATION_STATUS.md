# Implementation status

## Implemented and statically reviewed

Entra OAuth + PKCE, database-backed expiring/single-use state with atomic conditional consumption and HttpOnly cookie binding, encrypted token storage, access-token renewal with row-locked refresh updates, ownership-scoped models/migrations, ARM subscription/resource pagination, Cost Management query client, selection verification, Azure UI, and documentation.

Added an explicit development identity cookie/session (no shared default user), an opt-in backend-memory manual ARM-token path, typed frontend API boundaries, and small provider protocols.

Subscription rediscovery updates `last_seen_at` and marks previously known subscriptions that are no longer returned by Azure as `inaccessible` and unselected.

## Implemented, not tested against a real Azure account

Consent, tenant claims, token renewal, real subscriptions/resources, billing permissions, and multitenant behavior require credentials and were not run here.

## Runtime verification

`python -m compileall -q backend/app backend/migrations backend/tests` passed. Targeted hardening coverage was added in `backend/tests/test_azure_hardening.py` for encryption, state single-use, concurrent callbacks, cookie/state matching, refresh-token preservation, connection-scoped subscription selection, and production header rejection. These tests were not executable here because pytest, SQLAlchemy, and cryptography are unavailable.

## Blocked

Python dependencies were not installed because `PIP_NO_INDEX=1` and the pip cache contains none of the required project packages. The permitted npm offline install was attempted and failed with `ENOTCACHED` because the Vite package metadata is unavailable. pytest, Alembic, Ruff, npm lint, npm build, Docker/PostgreSQL, and real Azure verification are blocked, not passed.

## Limitations

The development user header is not production authentication. The receiving platform must supply a verified principal. Usage metrics, background synchronization, and per-subscription disconnect are not implemented. Migration execution and real Azure verification remain unverified.

The optional manual token path is not a production authentication mechanism and has not been tested against a real Azure token in this environment.
