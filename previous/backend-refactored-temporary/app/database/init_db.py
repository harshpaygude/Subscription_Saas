from app.database.session import engine, Base
from app.database.models import Organization


def init_db():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database tables created.")
