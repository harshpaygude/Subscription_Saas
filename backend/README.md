# Legacy Monolith Backend (Deprecated)

This directory contains the original FastAPI monolith preserved during the migration to the microservices architecture.

- **Active Platform Entrypoint:** [`services/gateway`](../services/gateway/README.md) (Port `8000`)
- **Active Microservices:**
  - [`services/identity-service`](../services/identity-service/README.md) (`identity_db`, Port `8001`)
  - [`services/subscription-service`](../services/subscription-service/README.md) (`subscription_db`, Port `8002`)
  - [`services/asset-service`](../services/asset-service/README.md) (`asset_db`, Port `8003`)
  - [`services/lifecycle-service`](../services/lifecycle-service/README.md) (`lifecycle_db`, Port `8004`)
  - [`services/integration-service`](../services/integration-service/README.md) (`integration_db`, Port `8005`)
  - [`services/governance-service`](../services/governance-service/README.md) (`governance_db`, Port `8006`)
- **Shared Cross-Cutting Primitives:** [`packages/service-kit`](../packages/service-kit)

> Note: Keep `backend/.venv` intact if running local multi-service tests with `backend/.venv/bin/python scripts/run_all_tests.py`.
> Use [`infra/postgres/migrate_monolith_to_microservices.py`](../infra/postgres/migrate_monolith_to_microservices.py) to non-destructively migrate data from `subscription_saas` into the six service databases.
