"""SQLAlchemy database session setup for Identity Service."""
from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


def _make_engine(url: str):
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


engine = _make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_db_ready() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def init_db() -> None:
    from app.infrastructure import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    # Safe additive column checks for legacy Postgres databases
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    if "users" in tables:
        cols = {c["name"] for c in inspector.get_columns("users")}
        with engine.begin() as conn:
            if "display_name" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN display_name VARCHAR(255) NULL"))
                conn.execute(text("UPDATE users SET display_name = email WHERE display_name IS NULL"))
            if "employee_id" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN employee_id VARCHAR(80) NULL"))
            if "phone_number" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN phone_number VARCHAR(40) NULL"))
