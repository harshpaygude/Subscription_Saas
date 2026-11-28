-- Initialize per-service logical PostgreSQL databases for the UniSora microservices architecture.
-- Safe and idempotent on repeated invocations via psql / docker-entrypoint-initdb.d.

SELECT 'CREATE DATABASE identity_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'identity_db')\gexec

SELECT 'CREATE DATABASE subscription_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'subscription_db')\gexec

SELECT 'CREATE DATABASE asset_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'asset_db')\gexec

SELECT 'CREATE DATABASE lifecycle_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'lifecycle_db')\gexec

SELECT 'CREATE DATABASE integration_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'integration_db')\gexec

SELECT 'CREATE DATABASE governance_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'governance_db')\gexec
