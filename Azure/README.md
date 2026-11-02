# Microsoft Azure service module

FastAPI + React/Vite Azure integration for a unified cloud platform. It implements Microsoft Entra authorization-code + PKCE, encrypted backend token persistence, subscription discovery, ARM resource inventory, Cost Management queries, subscription selection, and an integration UI.

## Status

Implemented but not tested against a real Azure tenant in this environment. The scaffold has no platform-auth middleware, so development uses `X-Platform-User-ID`; production rejects unauthenticated requests. The receiving platform must replace that dependency with its authenticated user context.

## Setup

Copy `.env.example` to `.env`, supply Entra credentials and a Fernet key. From `backend/`, create/activate a virtual environment, run `pip install -e ".[dev]"`, apply `alembic upgrade head`, then start `uvicorn app.main:app --reload`. From `frontend/`, run `npm install` and `npm run dev`.

See [docs/AZURE_ACCOUNT_SETUP.md](docs/AZURE_ACCOUNT_SETUP.md) and [docs/INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md). Backend checks are `pytest`, `ruff check app tests`, and `python -m compileall app migrations`; frontend checks are `npm run lint` and `npm run build`. The targeted security tests are in `backend/tests/test_azure_hardening.py`.

Cost access may require billing-scope permissions and can fail independently of resource discovery. Usage metrics beyond Cost Management are not implemented. OAuth state is stored in PostgreSQL with a ten-minute expiry, single-use consumption, and an HttpOnly browser-binding cookie. Local identity headers are development-only; the receiving platform must provide the authenticated user identity in production.

For local testing without an Entra app, the optional manual ARM-token path requires `ENABLE_MANUAL_AZURE_TOKEN_INPUT=true` and `APP_ENV=development`. It stores a pasted token only in backend memory and is disabled by default; it is not a production authentication mode.
