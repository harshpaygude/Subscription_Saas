"""SQLAlchemy ORM models strictly owned by Integration Service."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from unisora_kit import OutboxRecordMixin
from app.infrastructure.db import Base


class Connection(Base):
    __tablename__ = "connections"
    __table_args__ = (Index("ix_connections_user_provider", "user_id", "provider"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(nullable=False, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_tenant_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    credentials_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    scopes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    anthropic_reporting_cache: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    anthropic_reporting_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    anthropic_admin_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    anthropic_manual_balance_amount: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    anthropic_manual_balance_currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    anthropic_manual_balance_entered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AzureConnection(Base):
    __tablename__ = "azure_connections"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    organization_id: Mapped[int] = mapped_column(nullable=False, index=True)
    microsoft_home_account_id: Mapped[Optional[str]] = mapped_column(String(255))
    microsoft_tenant_id: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(40), default="CONNECTED", nullable=False)
    encrypted_token_cache: Mapped[Optional[str]] = mapped_column(Text)
    last_successful_refresh: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AzureOAuthState(Base):
    __tablename__ = "azure_oauth_states"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    organization_id: Mapped[int] = mapped_column(nullable=False, index=True)
    state_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    encrypted_code_verifier: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class AzureSubscription(Base):
    __tablename__ = "azure_subscriptions"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("azure_connections.id"), nullable=False, index=True)
    subscription_id: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(255))
    state: Mapped[Optional[str]] = mapped_column(String(50))
    selected: Mapped[bool] = mapped_column(default=False, nullable=False)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class GeminiUsageEvent(Base):
    __tablename__ = "gemini_usage_events"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("connections.id"), nullable=False, index=True)
    organization_id: Mapped[int] = mapped_column(nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    input_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class OutboxEvent(Base, OutboxRecordMixin):
    __tablename__ = "outbox_events"
