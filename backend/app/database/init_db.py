from sqlalchemy import inspect, text

from app.database.session import engine, Base
from app.database.models import Organization


def init_db():
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    columns = {column["name"] for column in inspector.get_columns("connections")} if "connections" in tables else set()
    if "connections" in tables and "user_id" not in columns:
        with engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE connections ADD COLUMN user_id INTEGER NULL"
            ))
            connection.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_connections_user_id "
                "ON connections (user_id)"
            ))

    if "connections" in tables and "credentials_encrypted" not in columns:
        with engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE connections ADD COLUMN credentials_encrypted TEXT NULL"
            ))

    if "connections" in tables and "last_verified_at" not in columns:
        with engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE connections ADD COLUMN last_verified_at TIMESTAMP NULL"
            ))

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "display_name" not in user_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN display_name VARCHAR(255) NULL"))
            connection.execute(text("UPDATE users SET display_name = email WHERE display_name IS NULL"))

    # Safe legacy migration: only auto-assign when an organization has one
    # member. Shared legacy connections stay unassigned rather than leaking
    # into every member's account; they can be reconnected by the user.
    if "connections" in tables:
        with engine.begin() as connection:
            connection.execute(text(
            "UPDATE connections AS c "
            "SET user_id = members.user_id "
            "FROM ("
            "  SELECT organization_id, MIN(id) AS user_id "
            "  FROM users GROUP BY organization_id "
            "  HAVING COUNT(*) = 1"
            ") AS members "
            "WHERE c.user_id IS NULL AND c.organization_id = members.organization_id"
            ))

    # The Azure tables were introduced before created_at/updated_at became
    # part of the ORM model. create_all() does not alter existing tables, so
    # add these columns safely for existing PostgreSQL installations.
    if "azure_connections" in tables:
        azure_columns = {column["name"] for column in inspector.get_columns("azure_connections")}
        missing_azure_columns = {
            "created_at": "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP",
        }
        for column_name, definition in missing_azure_columns.items():
            if column_name not in azure_columns:
                with engine.begin() as connection:
                    connection.execute(text(
                        f"ALTER TABLE azure_connections ADD COLUMN {column_name} {definition}"
                    ))


if __name__ == "__main__":
    init_db()
    print("Database tables created.")
