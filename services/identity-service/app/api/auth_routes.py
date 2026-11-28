"""Authentication routes for Identity Service."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from unisora_kit import DomainValidationError, RequestContext
from app.api.deps import commit_with_outbox, get_auth_service, get_current_context
from app.api.schemas import (
    ChangePasswordRequest,
    ProfileUpdate,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.application.auth_service import AuthService
from app.infrastructure.db import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db),
    service: AuthService = Depends(get_auth_service),
):
    try:
        user = service.register(
            email=user_data.email,
            password=user_data.password,
            organization_name=user_data.organization_name,
        )
        commit_with_outbox(db)
        return user
    except DomainValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc


@router.post("/login", response_model=TokenResponse)
async def login(
    user_data: UserLogin,
    service: AuthService = Depends(get_auth_service),
):
    token = service.login(email=user_data.email, password=user_data.password)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    ctx: RequestContext = Depends(get_current_context),
    service: AuthService = Depends(get_auth_service),
):
    return service.get_user(ctx.user_id)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: ProfileUpdate,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: AuthService = Depends(get_auth_service),
):
    user = service.update_profile(user_id=ctx.user_id, display_name=data.display_name)
    commit_with_outbox(db)
    return user


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: AuthService = Depends(get_auth_service),
):
    try:
        service.change_password(
            user_id=ctx.user_id,
            current_password=data.current_password,
            new_password=data.new_password,
        )
        commit_with_outbox(db)
        return {"message": "Password changed successfully."}
    except DomainValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
