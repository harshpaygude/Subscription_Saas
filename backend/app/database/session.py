from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()

    try:
        yield db
    except Exception:
        # Route handlers intentionally keep persistence atomic. If validation,
        # provider work, or commit processing fails, never leave a transaction
        # open in the pooled session and never expose a partially-written state
        # to the next request.
        db.rollback()
        raise
    finally:
        db.close()
