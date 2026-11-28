# IT Asset Management Service

Owns IT hardware asset inventory, 1-to-many custody assignments, returns, maintenance records, and bulk CSV/XLSX imports (`/assets/*`).

- **Database**: `asset_db` (`assets`, `asset_assignments`, `asset_maintenance`, `outbox_events`)
- **Port**: `8003`
- **Health**: `GET /health`, `GET /ready`
