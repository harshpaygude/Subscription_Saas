# Deployment & Verification Guide

## Docker Compose Deployment

All services run behind the API Gateway on an isolated internal network (`unisora_internal`). Only the API Gateway (`${BACKEND_PORT:-8000}`), Frontend (`${FRONTEND_PORT:-3000}`), and optional PostgreSQL port (`${POSTGRES_PORT:-5432}`) bind to host ports.

### 1. Configure Environment Variables
```bash
cp .env.example .env
# Populate JWT_SECRET_KEY and INTERNAL_SERVICE_SECRET (plus provider credentials as needed)
```

### 2. Existing PostgreSQL Data Initialization
If reusing an existing `unisora-production-postgres-data` volume where `/docker-entrypoint-initdb.d/` already ran previously, execute [`infra/postgres/init-databases.sql`](../infra/postgres/init-databases.sql) manually once against Postgres:
```bash
docker compose exec -T postgres psql -U postgres -d subscription_saas < infra/postgres/init-databases.sql
```
Then run `docker compose up -d --build` and follow [`DATABASE_OWNERSHIP.md`](./DATABASE_OWNERSHIP.md) to copy data from `subscription_saas` into the six service databases.

### 3. Build & Start Stack
```bash
docker compose up -d --build
```

Verify aggregated readiness:
```bash
curl http://127.0.0.1:8000/ready
```

## Local Development & Test Suites

### Run All Backend Service & Migration Tests
```bash
backend/.venv/bin/python scripts/run_all_tests.py
```

### Run Frontend Type-Check & Production Build
```bash
cd frontend
npx tsc --noEmit
npm run build
```

## Legacy Monolith Notice
[`backend/`](../backend/README.md) is preserved only for rollback reference and local `.venv` reuse; active traffic flows exclusively through `services/gateway` and the six domain microservices.
