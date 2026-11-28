# External Provider Integration Service

Owns encrypted cloud, AI, and SaaS connector credentials, verification adapters, and telemetry (`/integrations/*`).

- **Database**: `integration_db` (`connections`, `azure_connections`, `azure_oauth_states`, `azure_subscriptions`, `gemini_usage_events`, `outbox_events`)
- **Port**: `8005`
- **Health**: `GET /health`, `GET /ready`
