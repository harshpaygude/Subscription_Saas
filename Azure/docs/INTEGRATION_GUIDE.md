# Integration guide

`backend/app/providers/azure` is provider code; `backend/app/api/routes.py` and `frontend/` are the development shell. The receiving platform supplies authenticated user identity, database lifecycle, secret management, gateway/CORS, and production OAuth state/session behavior.

Microsoft authentication is not platform authentication. Microsoft tokens authorize ARM calls; the platform session identifies the owner. Never return provider tokens to the browser. Install the backend dependencies, apply migrations `0002_azure_connections` and `0003_azure_oauth_states`, include the router, and replace `platform_user()` with the platform principal. Preserve ownership filters and encrypted token storage. OAuth state requires PostgreSQL (or an equivalent shared store if the adapter is replaced); it is no longer process-local.

The exact handoff point is `backend/app/api/routes.py:platform_user()`. Replace that FastAPI dependency with an adapter that reads the already-verified user identity from the receiving platform's request context and returns a stable, non-email platform user ID. Do not pass an email, Microsoft tenant ID, or browser-supplied header as proof of identity. Every Azure route already depends on this function; no Azure route should bypass it.

Required backend configuration is `DATABASE_URL`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT`, `AZURE_REDIRECT_URI`, `AZURE_SCOPES`, and `AZURE_TOKEN_ENCRYPTION_KEY`. `ALLOW_LOCAL_PLATFORM_USER_HEADER=true` is for development only and is ignored outside `APP_ENV=development`. The implemented callback is `/api/azure/oauth/callback` and must exactly match the Entra registration.

For local API testing only, set `ENABLE_MANUAL_AZURE_TOKEN_INPUT=true` while `APP_ENV=development`. Use the UI's password-style temporary-token field or `POST /api/azure/dev/manual-token`. The token is held in backend process memory, never persisted, and cleared by the clear action or process restart. This path is disabled by default and rejected outside development; it must not be integrated into production authentication.

Configure the exact callback, client credentials, tenant, scope, and encryption key. The API routes are documented in [API_REFERENCE.md](API_REFERENCE.md). Test denied consent, expired state, revoked access, empty subscriptions, ARM resources, and billing denial with a developer tenant. Real Azure verification was not possible in this workspace.

The current test suite includes targeted cases for encrypted token storage, state replay/concurrency, state-cookie matching, token refresh behavior, connection-scoped subscription selection, and production rejection of the local identity header. Run `pytest` only after installing the declared backend dependencies in an authorized environment.
