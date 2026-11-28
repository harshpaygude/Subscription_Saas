# Extending UniSora: Adding Services & Integrations

The microservices architecture follows the Open/Closed and Dependency Inversion principles so new capabilities can be added without modifying unrelated services.

## Adding a New Microservice

1. **Scaffold from Clean Architecture Layout**
   Create `services/<domain>-service/` with:
   - `app/config.py` (inheriting `BaseServiceSettings` from `unisora_kit`)
   - `app/domain/`, `app/application/`, `app/infrastructure/`, `app/api/`
   - `app/main.py` registering `configure_logging`, `register_exception_handlers`, and `health_router`
   - `Dockerfile`, `requirements.txt`, `README.md`, and `tests/`
2. **Provision Dedicated Database**
   Add `CREATE DATABASE <domain>_db` to [`infra/postgres/init-databases.sql`](../infra/postgres/init-databases.sql) and configure `DATABASE_URL` in [`docker-compose.yml`](../docker-compose.yml).
3. **Register Gateway Route (Zero Code Edit Option)**
   Add a rule either cleanly in `services/gateway/app/routing.py` or dynamically via `EXTRA_ROUTES_JSON`:
   ```json
   [{"prefix": "/billing-v2", "service": "billing-service", "url": "http://billing-service:8007", "require_auth": true}]
   ```
4. **Add to Test Runner**
   Append `(ROOT / "services" / "<domain>-service", "tests")` to [`scripts/run_all_tests.py`](../scripts/run_all_tests.py).

## Adding a Generic SaaS Integration Adapter (OCP)

1. Implement a connector class with `provider_id` and `verify(self, data: Dict[str, Any]) -> Dict[str, Any]` in [`services/integration-service/app/infrastructure/providers/generic_adapters.py`](../services/integration-service/app/infrastructure/providers/generic_adapters.py).
2. Register the adapter instance in `build_default_provider_registry()` on `GenericProviderRegistry` without modifying route handlers or persistence models.
3. Add frontend provider metadata to [`frontend/lib/integrations.ts`](../frontend/lib/integrations.ts).

## Adding a Lifecycle Task Completion Verifier (OCP)

Implement the `TaskCompletionVerifier` protocol in [`services/lifecycle-service/app/application/task_verifiers.py`](../services/lifecycle-service/app/application/task_verifiers.py) and register it in `DEFAULT_TASK_VERIFIERS` (or inject custom verifiers into `LifecycleApplicationService`) so new task completion rules extend behavior without modifying core completion orchestration.
