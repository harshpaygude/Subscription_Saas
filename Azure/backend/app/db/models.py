from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class AzureConnection(Base):
    __tablename__ = "azure_connections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    microsoft_home_account_id: Mapped[str | None] = mapped_column(String(255))
    microsoft_tenant_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(40), default="connected", nullable=False)
    encrypted_token_cache: Mapped[str | None] = mapped_column(Text)
    last_successful_refresh: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    subscriptions: Mapped[list["AzureSubscription"]] = relationship(back_populates="connection", cascade="all, delete-orphan")
    __table_args__ = (UniqueConstraint("platform_user_id", "microsoft_home_account_id", name="uq_azure_identity"), Index("ix_azure_connection_user", "platform_user_id"))


class AzureOAuthState(Base):
    __tablename__ = "azure_oauth_states"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    state_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    platform_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_code_verifier: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (Index("ix_azure_oauth_state_expiry", "expires_at"),)


class AzureSubscription(Base):
    __tablename__ = "azure_subscriptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("azure_connections.id", ondelete="CASCADE"), nullable=False)
    subscription_id: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[str | None] = mapped_column(String(255))
    state: Mapped[str | None] = mapped_column(String(50))
    selected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    connection: Mapped[AzureConnection] = relationship(back_populates="subscriptions")
    __table_args__ = (UniqueConstraint("connection_id", "subscription_id", name="uq_azure_subscription"),)
