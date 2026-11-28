"""Authentication and user profile application service (pure DIP)."""
from __future__ import annotations

from datetime import datetime

from unisora_kit import DomainValidationError, NotFoundError, UnauthorizedError
from app.domain.entities import UserEntity
from app.domain.ports import (
    AuditEventPort,
    OrganizationRepository,
    PasswordHasher,
    TokenIssuer,
    UserRepository,
)


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        organizations: OrganizationRepository,
        hasher: PasswordHasher,
        tokens: TokenIssuer,
        audit: AuditEventPort,
        token_expire_minutes: int = 60,
    ):
        self.users = users
        self.organizations = organizations
        self.hasher = hasher
        self.tokens = tokens
        self.audit = audit
        self.token_expire_minutes = token_expire_minutes

    def register(self, *, email: str, password: str, organization_name: str) -> UserEntity:
        normalized_email = email.strip().lower()
        if self.users.get_by_email(normalized_email) is not None:
            raise DomainValidationError("User with this email already exists.")

        org = self.organizations.create(organization_name.strip())
        assert org.id is not None
        user = self.users.create(
            UserEntity(
                id=None,
                email=normalized_email,
                display_name=normalized_email.split("@")[0],
                password_hash=self.hasher.hash(password),
                organization_id=org.id,
                role="OWNER",
                created_at=datetime.utcnow(),
            )
        )
        assert user.id is not None
        self.audit.record(
            organization_id=org.id,
            actor_id=user.id,
            action="auth.registered",
            entity_type="user",
            entity_id=user.id,
        )
        return user

    def login(self, *, email: str, password: str) -> str:
        user = self.users.get_by_email(email.strip().lower())
        if not user or not self.hasher.verify(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")
        return self.tokens.create_access_token(
            {
                "sub": str(user.id),
                "organization_id": str(user.organization_id),
                "role": user.role,
                "email": user.email,
            },
            expires_minutes=self.token_expire_minutes,
        )

    def get_user(self, user_id: int) -> UserEntity:
        user = self.users.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    def update_profile(self, *, user_id: int, display_name: str) -> UserEntity:
        user = self.get_user(user_id)
        user.display_name = display_name.strip()
        return self.users.save(user)

    def change_password(self, *, user_id: int, current_password: str, new_password: str) -> None:
        user = self.get_user(user_id)
        if not self.hasher.verify(current_password, user.password_hash):
            raise DomainValidationError("Current password is incorrect.")
        user.password_hash = self.hasher.hash(new_password)
        self.users.save(user)
        assert user.id is not None
        self.audit.record(
            organization_id=user.organization_id,
            actor_id=user.id,
            action="auth.password_changed",
            entity_type="user",
            entity_id=user.id,
        )
