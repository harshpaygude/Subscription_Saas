# UniSora Microservices Refactoring Summary

This document records the architectural refactoring of the UniSora SaaS platform from a single-process FastAPI + SQLAlchemy monolith (`backend/`) into a modular, loosely coupled microservices architecture across `services/`, `packages/service-kit/`, `infra/postgres/`, and `frontend/`.

---

## 1. Transformation Overview

| Dimension | Previous Monolith (`backend/`) | Refactored Microservices Platform |
| --- | --- | --- |
| **Runtime Topology** | Single FastAPI process on port `8000` mounting 16 routers | API Gateway (`:8000`) + 6 independent domain microservices (`:8001`–`:8006`) |
| **Database Ownership** | Single shared SQLAlchemy `models.py` (14 tables) & raw `ALTER TABLE` startup script | 6 logical PostgreSQL databases (`identity_db`, `subscription_db`, `asset_db`, `lifecycle_db`, `integration_db`, `governance_db`), zero cross-DB foreign keys |
| **Layering & SOLID** | Tight coupling between HTTP routes, ORM queries, CSV parsing, and external SDKs | Strict 4-layer Clean Architecture per service (`domain/`, `application/`, `infrastructure/`, `api/`) with Protocol ports, DI, and OCP registries |
| **Inter-Service Communication** | Direct in-memory imports & cross-table SQL joins | Gateway HMAC-signed identity context (`X-Internal-Service-Token`), internal REST endpoints, and transactional outbox events (`outbox_events` -> `governance-service` `/internal/events`) |
| **Frontend API Layer** | Monolithic 979-line `frontend/lib/api.ts` + inline integration charts | Domain-scoped API modules (`frontend/lib/api/*.ts`), backwards-compatible `frontend/lib/api.ts` barrel, extracted `AnthropicCharts.tsx`, Gateway proxy target |

---

## 2. Architecture & Component Breakdown

### Shared Cross-Cutting Primitives ([`packages/service-kit`](../packages/service-kit))
Strictly non-domain infrastructure shared via `unisora_kit`:
- `config.py`: `BaseServiceSettings` environment configuration
- `logging.py`: structured JSON logging with `X-Request-ID` request correlation
- `errors.py`: normalized error envelope handlers
- `security.py`: JWT verification and HMAC `X-Internal-Service-Token` signing/validation (`require_user_context`, `require_internal_service`)
- `health.py`: `/health` and `/ready` endpoints
- `events.py`: event envelope, transactional outbox table/dispatcher with retries and dead-letter handling
- `http_client.py`: resilient internal HTTP client helpers

### API Gateway ([`services/gateway`](../services/gateway/README.md) — Port `8000`)
- Declarative route resolution in [`services/gateway/app/routing.py`](../services/gateway/app/routing.py), extensible without core edits via `EXTRA_ROUTES_JSON`.
- Edge JWT authentication verification and signed `X-Internal-Service-Token` propagation.
- Sliding-window rate limiting and aggregated downstream readiness at `GET /ready`.
- Explicitly blocks external requests to `/internal/*` (`403 Forbidden`).

### Domain Microservices (`services/`)

1. **[`identity-service`](../services/identity-service/README.md) (`:8001`, `identity_db`)**
   - Owns `organizations`, `users`, `departments`, `department_memberships`, `outbox_events`.
   - Handles authentication (`/auth/*`), organization onboarding & Excel parsing (`/organizations/*`), departments, and employees.
2. **[`subscription-service`](../services/subscription-service/README.md) (`:8002`, `subscription_db`)**
   - Owns `subscriptions`, `manual_spend_entries`, `subscription_licenses`, `subscription_assignments`, `outbox_events`.
   - Handles SaaS contracts, license pool capacity enforcement, Decimal cost interval math, assignments, and CSV import.
3. **[`asset-service`](../services/asset-service/README.md) (`:8003`, `asset_db`)**
   - Owns `assets`, `asset_assignments`, `asset_maintenance`, `outbox_events`.
   - Handles hardware inventory, assignment/return history, maintenance records, and wide-column/one-to-many Excel/CSV imports.
4. **[`lifecycle-service`](../services/lifecycle-service/README.md) (`:8004`, `lifecycle_db`)**
   - Owns `employee_lifecycles`, `lifecycle_tasks`, `outbox_events`.
   - Applies Interface Segregation (`IdentityPort`, `SubscriptionPort`, `AssetPort`, `AuditEventPort` in `app/domain/ports.py`) and Open/Closed strategy registration (`TaskCompletionVerifier` / `DEFAULT_TASK_VERIFIERS` in `app/application/task_verifiers.py`) to verify onboarding/offboarding clearance across service APIs.
5. **[`integration-service`](../services/integration-service/README.md) (`:8005`, `integration_db`)**
   - Owns `connections`, `azure_connections`, `azure_oauth_states`, `azure_subscriptions`, `gemini_usage_events`, `outbox_events`.
   - Uses encrypted credential storage and OCP connector registry (`GenericProviderRegistry` / `build_default_provider_registry()` in `app/infrastructure/providers/generic_adapters.py`) alongside dedicated AWS, Azure, OpenAI, Anthropic, and Gemini adapters.
6. **[`governance-service`](../services/governance-service/README.md) (`:8006`, `governance_db`)**
   - Owns `alerts`, `audit_logs`, `processed_events`.
   - Provides renewal/security alert deduplication, portfolio analytics summary (`/analytics/summary`), CSV audit exports (`/analytics/audit-export`, fixed to reference `next_renewal_date`), and idempotent `POST /internal/events` event ingestion.

---

## 3. Frontend Architecture Changes

- Split `frontend/lib/api.ts` into domain modules under [`frontend/lib/api/`](../frontend/lib/api/index.ts):
  `httpClient.ts`, `auth.ts`, `organizations.ts`, `departments.ts`, `employees.ts`, `subscriptions.ts`, `assets.ts`, `lifecycle.ts`, `integrations.ts`, `alerts.ts`, `analytics.ts`.
- Preserved [`frontend/lib/api.ts`](../frontend/lib/api.ts) as a re-export barrel (`export * from "./api/index"`).
- Pointed local Next.js dev proxy ([`frontend/next.config.ts`](../frontend/next.config.ts)) to `http://127.0.0.1:8000` and container build args ([`frontend/Dockerfile`](../frontend/Dockerfile)) to `http://gateway:8000`.
- Extracted reusable SVG chart components (`DonutPieChart`, `DailyTrendChart`) from `AnthropicIntegrationDetails.tsx` into [`frontend/components/integrations/AnthropicCharts.tsx`](../frontend/components/integrations/AnthropicCharts.tsx).

---

## 4. Database Ownership & Deployment

- [`infra/postgres/init-databases.sql`](../infra/postgres/init-databases.sql): idempotently creates the six logical databases inside PostgreSQL.
- [`infra/postgres/migrate_monolith_to_microservices.py`](../infra/postgres/migrate_monolith_to_microservices.py): supports `--dry-run` inspection and idempotent (`INSERT ... ON CONFLICT DO NOTHING`) non-destructive data copy + sequence synchronization from `subscription_saas` into the six service databases.
- [`docker-compose.yml`](../docker-compose.yml) & [`.env.example`](../.env.example): runs PostgreSQL, the 6 microservices on `unisora_internal`, the `gateway` entrypoint on `${BACKEND_PORT:-8000}`, and `frontend` on `${FRONTEND_PORT:-3000}` with health checks.
- [`backend/README.md`](../backend/README.md): documents deprecation of the legacy monolith directory while preserving `backend/.venv` for local test execution.

---

## 5. Verification Status

1. **Automated Python Test Suite** (`backend/.venv/bin/python scripts/run_all_tests.py`):
   - `packages/service-kit`: **2 tests passed**
   - `services/gateway`: **5 tests passed**
   - `services/identity-service`: **8 tests passed**
   - `services/subscription-service`: **3 tests passed**
   - `services/asset-service`: **4 tests passed**
   - `services/lifecycle-service`: **3 tests passed**
   - `services/integration-service`: **17 tests passed**
   - `services/governance-service`: **3 tests passed**
   - `infra/postgres`: **1 test passed**
   - **Total: 9 suites, 46 tests passed.**
2. **Frontend Verification** (`cd frontend && npx tsc --noEmit && npm run build`):
   - TypeScript type-check (`tsc --noEmit`): passed (`exit 0`).
   - Next.js 16.3.5 Turbopack production build: passed (`19/19` static routes generated).
3. **Related Documentation**:
   - [ARCHITECTURE.md](./ARCHITECTURE.md)
   - [SERVICES.md](./SERVICES.md)
   - [API_CONTRACTS.md](./API_CONTRACTS.md)
   - [DATABASE_OWNERSHIP.md](./DATABASE_OWNERSHIP.md)
   - [DEPLOYMENT.md](./DEPLOYMENT.md)
   - [EXTENDING_SERVICES.md](./EXTENDING_SERVICES.md)
