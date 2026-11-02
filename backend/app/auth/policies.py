from fastapi import HTTPException, status

from app.database.models import User


ADMIN_ROLES = {"OWNER", "ADMIN", "ASSET_MANAGER"}


def require_admin(user: User) -> User:
    if user.role.upper() not in ADMIN_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrative permission required.")
    return user

