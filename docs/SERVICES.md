# Service Catalog & Responsibilities

| Service | Port | Owned Database | Primary Bounded Context |
| --- | --- | --- | --- |
| [`gateway`](../services/gateway/README.md) | `8000` | None | Edge routing, rate limiting, JWT validation, internal HMAC signing, readiness aggregation |
| [`identity-service`](../services/identity-service/README.md) | `8001` | `identity_db` | Auth (`/auth/*`), Organizations & onboarding (`/organizations/*`), Departments, Employees |
| [`subscription-service`](../services/subscription-service/README.md) | `8002` | `subscription_db` | Subscriptions, Spend entries, License pools, Assignments, CSV import |
| [`asset-service`](../services/asset-service/README.md) | `8003` | `asset_db` | IT Assets, Hardware assignments, Maintenance logs, Excel/CSV import |
| [`lifecycle-service`](../services/lifecycle-service/README.md) | `8004` | `lifecycle_db` | Onboarding/offboarding workflows & pluggable task completion verifiers |
| [`integration-service`](../services/integration-service/README.md) | `8005` | `integration_db` | AWS, Azure OAuth/SP, OpenAI, Anthropic, Gemini, and generic SaaS providers |
| [`governance-service`](../services/governance-service/README.md) | `8006` | `governance_db` | Renewal/security alerts, centralized audit logs, portfolio analytics, CSV audit export |

## Shared Infrastructure Package

- [`packages/service-kit`](../packages/service-kit): provides `unisora_kit` modules (`config`, `logging`, `errors`, `security`, `health`, `events`, `http_client`) imported by each service without introducing cross-domain coupling.

## Frontend Architecture

- Next.js App Router (`frontend/`) communicates exclusively with the API Gateway (`http://127.0.0.1:8000` locally via `next.config.ts`, `http://gateway:8000` inside Docker).
- Domain-scoped API modules live under [`frontend/lib/api/`](../frontend/lib/api/index.ts):
  - `httpClient.ts` (shared token handling, error normalization, FormData/download helpers)
  - `auth.ts`, `organizations.ts`, `departments.ts`, `employees.ts`, `subscriptions.ts`, `assets.ts`, `lifecycle.ts`, `integrations.ts`, `alerts.ts`, `analytics.ts`
- `frontend/lib/api.ts` re-exports `./api/index` for backwards-compatible imports across existing pages.
- Heavy chart primitives in `AnthropicIntegrationDetails.tsx` are separated into [`AnthropicCharts.tsx`](../frontend/components/integrations/AnthropicCharts.tsx).
