from datetime import datetime
from typing import Optional

from sqlalchemy import String, ForeignKey, DateTime, Text, Index, Numeric, Date, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    members = relationship(
        "User",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    connections = relationship(
        "Connection",
        back_populates="organization",
        cascade="all, delete-orphan",
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="OWNER",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    organization = relationship(
        "Organization",
        back_populates="members",
    )


class Connection(Base):
    __tablename__ = "connections"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    )

    # Organization membership is not the authorization boundary: each
    # provider connection belongs to the user who created it.
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    provider: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    provider_tenant_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    access_token: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    refresh_token: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    credentials_encrypted: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    scopes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ACTIVE",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    last_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    organization = relationship(
        "Organization",
        back_populates="connections",
    )

    owner = relationship("User")


Index("ix_connections_user_provider", Connection.user_id, Connection.provider)

class AzureConnection(Base):
    __tablename__ = "azure_connections"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
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
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
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
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    input_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    amount: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    billing_interval: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    next_renewal_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", index=True)
    cancellation_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="manual")
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


Index("ix_subscriptions_org_status_renewal", Subscription.organization_id, Subscription.status, Subscription.next_renewal_date)


class ManualSpendEntry(Base):
    __tablename__ = "manual_spend_entries"
    __table_args__ = (UniqueConstraint("organization_id", "provider", "period_start", name="uq_manual_spend_org_provider_period"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    billing_interval: Mapped[str] = mapped_column(String(20), nullable=False, default="monthly")
    period_start: Mapped[datetime] = mapped_column(Date, nullable=False)
    period_end: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (UniqueConstraint("organization_id", "dedupe_key", name="uq_alert_org_dedupe"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    subscription_id: Mapped[Optional[int]] = mapped_column(ForeignKey("subscriptions.id"), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="info", index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    dedupe_key: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
