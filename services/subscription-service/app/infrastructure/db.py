"""SQLAlchemy database session setup for Subscription Service."""
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
    inspector = inspect(engine)
    if "subscriptions" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("subscriptions")}
        if "renewal_type" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN renewal_type VARCHAR(50) NOT NULL DEFAULT 'AUTOPAY'"))
