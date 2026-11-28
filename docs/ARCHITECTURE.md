# UniSora Architecture Overview

UniSora has been refactored from a single-process FastAPI + SQLAlchemy monolith into a **modular, loosely coupled microservices architecture** with strict per-service data ownership, Clean Architecture layering, SOLID abstractions, and an API Gateway entrypoint.

## System Topology

```mermaid
flowchart LR
  FE["Next.js Frontend (:3000)"] -->|"REST /api/* proxy"| GW["API Gateway (:8000)"]

  GW -->|"JWT + HMAC Identity Context"| ID["identity-service (:8001)"]
  GW --> SUB["subscription-service (:8002)"]
  GW --> AST["asset-service (:8003)"]
  GW --> LFC["lifecycle-service (:8004)"]
  GW --> INT["integration-service (:8005)"]
  GW --> GOV["governance-service (:8006)"]

  ID --> DB1[("identity_db")]
  SUB --> DB2[("subscription_db")]
  AST --> DB3[("asset_db")]
  LFC --> DB4[("lifecycle_db")]
  INT --> DB5[("integration_db")]
  GOV --> DB6[("governance_db")]

  ID -.->|"Outbox Events /internal/events"| GOV
  SUB -.->|"Outbox Events /internal/events"| GOV
  AST -.->|"Outbox Events /internal/events"| GOV
  LFC -.->|"Outbox Events /internal/events"| GOV
  INT -.->|"Outbox Events /internal/events"| GOV
```

## Architectural Principles

1. **Domain-Driven Service Boundaries**
   Each microservice owns one cohesive bounded context:
   - `identity-service`: authentication, organizations, onboarding orchestration, departments, employees.
   - `subscription-service`: SaaS contracts, license pools, user assignments, manual spend entries, CSV import.
   - `asset-service`: IT hardware inventory, employee assignments, maintenance tickets, CSV import.
   - `lifecycle-service`: onboarding/offboarding workflows and extensible completion verification strategies.
   - `integration-service`: external SaaS/cloud connectors (AWS, Azure, OpenAI, Anthropic, Gemini, and generic SaaS providers via a registry).
   - `governance-service`: alerts, audit logs, portfolio analytics, CSV audit exports, idempotent event consumer.

2. **Clean Architecture Inside Every Service**
   Every service separates responsibilities across four layers:
   - `app/domain/`: pure domain logic, entities/enums, calculation rules, strategy interfaces (`Protocol` / ABCs) without framework imports.
   - `app/application/`: use-case orchestration depending only on repository/client/publisher abstractions (Dependency Inversion).
   - `app/infrastructure/`: SQLAlchemy models, repository implementations, HTTP service clients, external provider SDK adapters, outbox publisher.
   - `app/api/`: FastAPI routers, Pydantic DTOs, request validation, HTTP exception translation.

3. **Zero Cross-Service Database Coupling**
   Services never share ORM models or query another service's tables. Cross-service interactions happen over explicit internal REST APIs (authenticated via signed HMAC `X-Internal-Service-Token` headers) or durable transactional outbox events delivered to `governance-service`.

4. **Shared Cross-Cutting Kit Without Domain Coupling**
   `packages/service-kit` (`unisora_kit`) contains strictly non-domain infrastructure primitives: configuration base settings, structured JSON logging with correlation IDs (`X-Request-ID`), standard error envelope handlers, JWT/internal-HMAC auth dependencies, health check helpers, event envelope + outbox dispatcher, and resilient HTTP client helpers.
