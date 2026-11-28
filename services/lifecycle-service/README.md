# Employee Lifecycle Service

Owns employee onboarding/offboarding state machines and clearance tasks (`/employee-lifecycle/*`, `/employees/{id}/onboarding`, `/employees/{id}/offboarding`, `/lifecycle-tasks/*`).

- **Database**: `lifecycle_db` (`employee_lifecycles`, `lifecycle_tasks`, `outbox_events`)
- **Port**: `8004`
- **Health**: `GET /health`, `GET /ready`
