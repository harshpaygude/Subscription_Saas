# Governance, Alerts & Analytics Service

Owns renewal & operational alerts (`/alerts/*`), portfolio analytics & compliance audit export (`/analytics/*`), and idempotent domain event ingestion (`POST /internal/events`).

- **Database**: `governance_db` (`alerts`, `audit_logs`, `processed_events`)
- **Port**: `8006`
- **Health**: `GET /health`, `GET /ready`
