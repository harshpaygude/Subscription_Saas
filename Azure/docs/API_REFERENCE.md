# API reference

Development authentication uses `X-Platform-User-ID`; production must use the receiving platform session. Errors use `{"detail":"..."}`.

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/providers` | Provider metadata |
| GET | `/api/azure/oauth/start` | Microsoft redirect; writes a ten-minute HttpOnly state cookie and durable state record |
| GET | `/api/azure/oauth/callback?code=...&state=...` | One-time callback; requires matching state cookie |
| GET | `/api/azure/connection` | Current connection status |
| POST | `/api/azure/subscriptions/discover` | Discover subscriptions |
| POST | `/api/azure/subscriptions` | Body `{ "subscription_ids": ["sub-id"] }`; verify and save selection |
| GET | `/api/azure/subscriptions/{id}/resources` | ARM inventory |
| GET | `/api/azure/subscriptions/{id}/cost?start=2026-01-01&end=2026-02-01` | Actual daily cost query |
| DELETE | `/api/azure/connection` | Disconnect and delete token cache |
| POST | `/api/dev/session` | Development-only local identity cookie; body `{ "user_id": "developer-a" }` |
| DELETE | `/api/dev/session` | Clear development-only local identity cookie |
| POST | `/api/azure/dev/manual-token` | Development-only in-memory ARM token; requires explicit enable setting |
| DELETE | `/api/azure/dev/manual-token` | Clear development-only in-memory ARM token |

All routes are user-scoped. Dates are ISO dates with `start < end`; ARM list calls follow `nextLink`. Resource data is read-only. Expired access tokens are renewed server-side when a refresh token is available; otherwise the connection becomes `reauthorization_required`. Planned: metrics beyond Cost Management, per-subscription disconnect, durable background refresh, and tenant enumeration UI.
