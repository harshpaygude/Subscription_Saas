from datetime import datetime

from sqlalchemy.orm import Session

from app.database.models import Organization, User
from app.auth.schemas import UserRegister
from app.auth.security import (
    hash_password,
    verify_password,
)


def register_user(
    db: Session,
    user_data: UserRegister,
) -> User:

    existing_user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if existing_user:
        raise ValueError("User with this email already exists.")

    organization = Organization(
        name=user_data.organization_name,
        created_at=datetime.utcnow(),
    )

    db.add(organization)
    db.flush()

    user = User(
        email=user_data.email,
        display_name=user_data.email.split("@")[0],
        password_hash=hash_password(
            user_data.password
        ),
        organization_id=organization.id,
        role="OWNER",
        created_at=datetime.utcnow(),
    )

    db.add(user)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(user)

    return user


def authenticate_user(
    db: Session,
    email: str,
    password: str,
):

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user:
        return None

    if not verify_password(
        password,
        user.password_hash,
    ):
        return None

    return user
