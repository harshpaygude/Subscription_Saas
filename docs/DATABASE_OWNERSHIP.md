# Database Ownership & Migration Guide

Each microservice owns a dedicated logical PostgreSQL database (or SQLite database in standalone unit tests), ensuring zero direct cross-service SQL queries or foreign-key coupling.

## Table Ownership Matrix

| Database | Owning Service | Tables |
| --- | --- | --- |
| `identity_db` | `identity-service` | `organizations`, `users`, `departments`, `department_memberships`, `outbox_events` |
| `subscription_db` | `subscription-service` | `subscriptions`, `manual_spend_entries`, `subscription_licenses`, `subscription_assignments`, `outbox_events` |
| `asset_db` | `asset-service` | `assets`, `asset_assignments`, `asset_maintenance`, `outbox_events` |
| `lifecycle_db` | `lifecycle-service` | `employee_lifecycles`, `lifecycle_tasks`, `outbox_events` |
| `integration_db` | `integration-service` | `connections`, `azure_connections`, `azure_oauth_states`, `azure_subscriptions`, `gemini_usage_events`, `outbox_events` |
| `governance_db` | `governance-service` | `alerts`, `audit_logs`, `processed_events` |

Cross-service references (such as `organization_id`, `user_id`, or `department_id`) are stored as logical scalar IDs rather than cross-database foreign keys.

## Preserving Existing Monolith Data

1. [`infra/postgres/init-databases.sql`](../infra/postgres/init-databases.sql) idempotently creates all six service databases alongside the existing `subscription_saas` database.
2. Start the six microservices once so each service initializes its schema tables inside its own database.
3. Preview row counts without modifying data:
   ```bash
   python infra/postgres/migrate_monolith_to_microservices.py \
     --source postgresql://postgres:postgres@localhost:5432/subscription_saas \
     --target-base postgresql://postgres:postgres@localhost:5432 \
     --dry-run
   ```
4. Execute the non-destructive, idempotent copy (`INSERT ... ON CONFLICT DO NOTHING` + `setval` sequence sync):
   ```bash
   python infra/postgres/migrate_monolith_to_microservices.py \
     --source postgresql://postgres:postgres@localhost:5432/subscription_saas \
     --target-base postgresql://postgres:postgres@localhost:5432
   ```
The source monolith database `subscription_saas` is never altered or truncated.
