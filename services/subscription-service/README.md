# Subscriptions & Licensing Service

Owns SaaS subscriptions (`/subscriptions/*`), manual spend tracking, license pools, and seat assignments (`/subscription-assignments/*`).

- **Database**: `subscription_db` (`subscriptions`, `manual_spend_entries`, `subscription_licenses`, `subscription_assignments`, `outbox_events`)
- **Port**: `8002`
- **Health**: `GET /health`, `GET /ready`
