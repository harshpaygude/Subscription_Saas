# Changelog

## 2026-10-16

Added Entra authorization-code + PKCE, encrypted token storage, ARM/Cost clients, Azure models and migration `0002_azure_connections`, discovery/selection/resource/cost/status/disconnect routes, Azure UI, and integration documentation.

- Hardened OAuth state with migration `0003_azure_oauth_states`, database persistence, expiry, single-use consumption, and cookie binding. Added server-side access-token renewal and production rejection of local identity headers.
- Made OAuth state consumption atomic under concurrent callbacks, added callback-cookie cleanup and database rollback handling, and locked connection rows during token refresh.
- Moved the OAuth state commit ahead of verifier decryption so malformed state data cannot roll back single-use consumption.
- Removed the shared local identity fallback, added an explicit development identity cookie/session, added disabled-by-default in-memory manual ARM-token testing, and separated frontend API networking from React rendering.
- Added small provider protocols and documented the SOLID boundaries.
