# API Gateway & Inter-Service Contracts

## External Routing Table (API Gateway `:8000`)

The gateway resolves incoming paths using [`services/gateway/app/routing.py`](../services/gateway/app/routing.py):

| Prefix / Pattern | Auth Required | Target Service |
| --- | --- | --- |
| `POST /auth/login`, `POST /auth/register` | Public | `identity-service` |
| `/auth/*`, `/organizations/*`, `/departments/*`, `/employees/*` | JWT | `identity-service` |
| `/employees/{id}/(onboarding\|offboarding\|lifecycle)` | JWT | `lifecycle-service` |
| `/employee-lifecycle/*`, `/lifecycle-tasks/*` | JWT | `lifecycle-service` |
| `/subscriptions/*`, `/subscription-assignments/*` | JWT | `subscription-service` |
| `GET /assets/sample-template` | Public | `asset-service` |
| `/assets/*` | JWT | `asset-service` |
| `GET /integrations/azure/oauth/callback` | Public | `integration-service` |
| `/integrations/*` | JWT | `integration-service` |
| `/alerts/*`, `/analytics/*` | JWT | `governance-service` |
| `/internal/*` | **Blocked (`403`) at Gateway** | Not exposed externally |

Dynamic routes can be appended without code changes via the `EXTRA_ROUTES_JSON` gateway environment variable.

## Security & Identity Propagation

1. External clients send `Authorization: Bearer <jwt>`.
2. The API Gateway validates the JWT signature and claims at the edge, propagates `X-Request-ID`, and forwards an HMAC-signed `X-Internal-Service-Token` (`sub`, `org_id`, `email`, `role`, `service="api-gateway"`, `exp`).
3. Downstream microservices verify either a direct Bearer JWT or `X-Internal-Service-Token` via `unisora_kit.security` (`require_user_context` / `require_internal_service`).
4. Direct service-to-service endpoints under `/internal/*` require a valid `X-Internal-Service-Token` with caller service identity and are explicitly rejected at the public gateway.

## Asynchronous Domain Events (`/internal/events`)

Services write state changes atomically alongside an `outbox_events` row (`event_id`, `event_type`, `payload`, `schema_version`) and dispatch events with exponential retry via `unisora_kit.events`.

`governance-service` implements idempotent ingestion in `POST /internal/events` backed by a `processed_events` deduplication table (unique on `event_id`). Emitted events include audit log records (`audit.recorded`), renewal/lifecycle notifications, and resource creation events.
