
from sqlalchemy import inspect, text

from app.database.session import engine


def migrate():
    inspector = inspect(engine)

    if "connections" not in inspector.get_table_names():
        raise RuntimeError(
            "The connections table does not exist. "
            "Initialize the database before running this migration."
        )

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("connections")
    }

    statements = {
        "aws_role_arn": (
            "ALTER TABLE connections "
            "ADD COLUMN aws_role_arn VARCHAR(512)"
        ),
        "aws_external_id": (
            "ALTER TABLE connections "
            "ADD COLUMN aws_external_id VARCHAR(255)"
        ),
    }

    with engine.begin() as connection:
        for column_name, statement in statements.items():
            if column_name not in existing_columns:
                connection.execute(text(statement))
                print("Added column: {}".format(column_name))
            else:
                print("Column already exists: {}".format(column_name))

        # Existing databases may predate the model's unique constraint.
        # PostgreSQL and SQLite both support this index syntax.
        connection.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_connections_aws_external_id "
            "ON connections (aws_external_id)"
        ))

    print("AWS role fields and external-ID uniqueness migration completed.")


if __name__ == "__main__":
    migrate()

