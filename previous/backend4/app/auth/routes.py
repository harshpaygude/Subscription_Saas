from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.models import User

from app.auth.schemas import (
    UserRegister,
    UserLogin,
    TokenResponse,
    UserResponse,
)

from app.auth.service import (
    register_user,
    authenticate_user,
)

from app.auth.security import (
    create_access_token,
)

from app.auth.dependencies import (
    get_current_user,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db),
):
    try:
        user = register_user(
            db,
            user_data,
        )

        return user

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    user_data: UserLogin,
    db: Session = Depends(get_db),
):
    user = authenticate_user(
        db,
        user_data.email,
        user_data.password,
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    token = create_access_token(
        {
            "sub": str(user.id),
            "organization_id": str(
                user.organization_id
            ),
            "role": user.role,
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
    }


@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user
