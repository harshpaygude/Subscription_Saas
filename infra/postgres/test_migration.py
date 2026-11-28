"""Tests for the non-destructive monolith-to-microservices DB migration script."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from sqlalchemy import create_engine, text

from infra.postgres.migrate_monolith_to_microservices import migrate_table


class MigrationScriptTests(unittest.TestCase):
    def test_migrate_table_is_non_destructive_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            src_url = f"sqlite:///{Path(tmpdir) / 'monolith.db'}"
            dst_url = f"sqlite:///{Path(tmpdir) / 'identity.db'}"

            src_engine = create_engine(src_url, future=True)
            dst_engine = create_engine(dst_url, future=True)

            with src_engine.begin() as conn:
                conn.execute(
                    text(
                        "CREATE TABLE organizations (id INTEGER PRIMARY KEY, name TEXT NOT NULL, domain TEXT)"
                    )
                )
                conn.execute(
                    text("INSERT INTO organizations (id, name, domain) VALUES (1, 'Acme', 'acme.com')")
                )
                conn.execute(
                    text("INSERT INTO organizations (id, name, domain) VALUES (2, 'Beta', 'beta.io')")
                )

            with dst_engine.begin() as conn:
                conn.execute(
                    text(
                        "CREATE TABLE organizations (id INTEGER PRIMARY KEY, name TEXT NOT NULL, domain TEXT)"
                    )
                )

            dry_total, dry_inserted = migrate_table(src_engine, dst_engine, "organizations", dry_run=True)
            self.assertEqual((dry_total, dry_inserted), (2, 0))

            with dst_engine.connect() as conn:
                self.assertEqual(conn.execute(text("SELECT COUNT(*) FROM organizations")).scalar(), 0)

            first_total, first_inserted = migrate_table(src_engine, dst_engine, "organizations")
            self.assertEqual((first_total, first_inserted), (2, 2))

            second_total, second_inserted = migrate_table(src_engine, dst_engine, "organizations")
            self.assertEqual((second_total, second_inserted), (2, 0))

            with src_engine.connect() as conn:
                self.assertEqual(conn.execute(text("SELECT COUNT(*) FROM organizations")).scalar(), 2)
            with dst_engine.connect() as conn:
                self.assertEqual(conn.execute(text("SELECT COUNT(*) FROM organizations")).scalar(), 2)


if __name__ == "__main__":
    unittest.main()
