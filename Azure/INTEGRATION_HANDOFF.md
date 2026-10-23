# Azure integration handoff

This package contains the Azure provider, FastAPI development shell, React UI, migrations, configuration template, tests, and documentation. It is implemented but not verified against a real Azure tenant.

Read [README.md](README.md), then [docs/AZURE_ACCOUNT_SETUP.md](docs/AZURE_ACCOUNT_SETUP.md), [docs/INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md), and [docs/API_REFERENCE.md](docs/API_REFERENCE.md). Supply a real Entra app, exact callback URI, server-side secret/certificate, encryption key, PostgreSQL, and the receiving platform's user identity. The exact authentication integration point is `backend/app/api/routes.py:platform_user()`; replace it with the receiving platform's verified-user dependency. Keep `APP_ENV` out of development. Real login, billing, renewal, and tenant behavior remain unverified.

For local-only API testing, an explicit development identity cookie can be created through `/api/dev/session`. The optional manual ARM token path requires `ENABLE_MANUAL_AZURE_TOKEN_INPUT=true`, keeps the token in process memory only, and is rejected outside development. It is not a substitute for the receiving platform's authentication or Microsoft OAuth.
