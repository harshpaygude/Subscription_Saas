# Identity & Organization Service

Owns authentication (`/auth/*`), organizations & onboarding (`/organizations/*`), departments (`/departments/*`), and employee directory (`/employees/*`).

- **Database**: `identity_db` (`organizations`, `users`, `departments`, `department_memberships`, `outbox_events`)
- **Port**: `8001`
- **Health**: `GET /health`, `GET /ready`
