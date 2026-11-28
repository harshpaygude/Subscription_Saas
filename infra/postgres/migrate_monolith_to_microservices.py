"""Non-destructive, idempotent data migration from the monolith database into service-owned DBs.

Usage:
    python infra/postgres/migrate_monolith_to_microservices.py \
        --source postgresql://postgres:postgres@localhost:5432/subscription_saas \
        --target-base postgresql://postgres:postgres@localhost:5432 \
        --dry-run

What it guarantees:
- Does NOT delete or truncate data in the source monolith database.
- Copies rows into each microservice's owned database in foreign-key dependency order.
- Uses INSERT ... ON CONFLICT DO NOTHING (by primary key `id`) so repeated runs are safe.
- Resets PostgreSQL SERIAL/IDENTITY sequences to MAX(id) after copying.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Sequence
from sqlalchemy import create_engine, inspect, text


@dataclass(frozen=True)
class ServiceMigrationPlan:
    service_name: str
    database_name: str
    tables_in_order: tuple[str, ...]


MIGRATION_PLANS: tuple[ServiceMigrationPlan, ...] = (
    ServiceMigrationPlan(
        service_name="identity-service",
        database_name="identity_db",
        tables_in_order=(
            "organizations",
            "users",
            "departments",
            "department_memberships",
        ),
    ),
    ServiceMigrationPlan(
        service_name="subscription-service",
        database_name="subscription_db",
        tables_in_order=(
            "subscriptions",
            "manual_spend_entries",
            "subscription_licenses",
            "subscription_assignments",
        ),
    ),
    ServiceMigrationPlan(
        service_name="asset-service",
        database_name="asset_db",
        tables_in_order=(
            "assets",
            "asset_assignments",
            "asset_maintenance",
        ),
    ),
    ServiceMigrationPlan(
        service_name="lifecycle-service",
        database_name="lifecycle_db",
        tables_in_order=(
            "employee_lifecycles",
            "lifecycle_tasks",
        ),
    ),
    ServiceMigrationPlan(
        service_name="integration-service",
        database_name="integration_db",
        tables_in_order=(
            "connections",
            "azure_connections",
            "azure_oauth_states",
            "azure_subscriptions",
            "gemini_usage_events",
        ),
    ),
    ServiceMigrationPlan(
        service_name="governance-service",
        database_name="governance_db",
        tables_in_order=(
            "alerts",
            "audit_logs",
        ),
    ),
)


def _quote_ident(name: str) -> str:
    return f'"{name.replace(chr(34), chr(34) * 2)}"'


def migrate_table(
    source_engine,
    target_engine,
    table_name: str,
    *,
    dry_run: bool = False,
) -> tuple[int, int]:
    src_inspector = inspect(source_engine)
    dst_inspector = inspect(target_engine)
    if not src_inspector.has_table(table_name):
        return 0, 0
    if not dst_inspector.has_table(table_name):
        raise RuntimeError(
            f"Target table '{table_name}' does not exist in target DB. "
            "Start the target service once (or run its schema init) before migrating data."
        )

    src_cols = {col["name"] for col in src_inspector.get_columns(table_name)}
    dst_cols = [col["name"] for col in dst_inspector.get_columns(table_name)]
    shared_cols = [col for col in dst_cols if col in src_cols]
    if not shared_cols:
        return 0, 0

    col_sql = ", ".join(_quote_ident(col) for col in shared_cols)
    table_sql = _quote_ident(table_name)
    pk_cols = dst_inspector.get_pk_constraint(table_name).get("constrained_columns") or []

    with source_engine.connect() as src_conn:
        rows = src_conn.execute(text(f"SELECT {col_sql} FROM {table_sql}")).mappings().all()

    if dry_run or not rows:
        return len(rows), 0

    placeholders = ", ".join(f":{col}" for col in shared_cols)
    conflict_clause = ""
    if pk_cols:
        pk_sql = ", ".join(_quote_ident(col) for col in pk_cols)
        conflict_clause = f" ON CONFLICT ({pk_sql}) DO NOTHING"

    insert_sql = text(f"INSERT INTO {table_sql} ({col_sql}) VALUES ({placeholders}){conflict_clause}")
    inserted = 0
    with target_engine.begin() as dst_conn:
        for row in rows:
            res = dst_conn.execute(insert_sql, dict(row))
            if res.rowcount:
                inserted += res.rowcount

        if "id" in shared_cols:
            seq_stmt = text(
                "SELECT setval(pg_get_serial_sequence(:tbl, 'id'), "
                "COALESCE((SELECT MAX(id) FROM " + table_sql + "), 1), true)"
            )
            try:
                dst_conn.execute(seq_stmt, {"tbl": table_name})
            except Exception:
                # Non-serial primary key or SQLite target in tests
                pass

    return len(rows), inserted


def run_migration(source_url: str, target_base_url: str, *, dry_run: bool = False) -> dict[str, dict[str, tuple[int, int]]]:
    source_engine = create_engine(source_url, future=True)
    report: dict[str, dict[str, tuple[int, int]]] = {}
    base = target_base_url.rstrip("/")

    for plan in MIGRATION_PLANS:
        target_engine = create_engine(f"{base}/{plan.database_name}", future=True)
        service_report: dict[str, tuple[int, int]] = {}
        for table_name in plan.tables_in_order:
            service_report[table_name] = migrate_table(
                source_engine,
                target_engine,
                table_name,
                dry_run=dry_run,
            )
        report[plan.service_name] = service_report
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Non-destructive monolith-to-microservices DB migrator.")
    parser.add_argument("--source", required=True, help="Source SQLAlchemy URL (monolith database).")
    parser.add_argument("--target-base", required=True, help="Base SQLAlchemy URL without database name.")
    parser.add_argument("--dry-run", action="store_true", help="Inspect row counts without writing.")
    args = parser.parse_args(argv)

    summary = run_migration(args.source, args.target_base, dry_run=args.dry_run)
    for service_name, tables in summary.items():
        print(f"[{service_name}]")
        for table_name, (total, inserted) in tables.items():
            mode = "dry-run" if args.dry_run else f"inserted={inserted}"
            print(f"  - {table_name}: source_rows={total} ({mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
