"""SQLAlchemy ORM models strictly owned by Lifecycle Service."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from unisora_kit import OutboxRecordMixin
from app.infrastructure.db import Base


class EmployeeLifecycle(Base):
    __tablename__ = "employee_lifecycles"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_employee_lifecycle_org_user"),
        Index("ix_employee_lifecycles_org_status", "organization_id", "status"),
        Index("ix_employee_lifecycles_org_joined", "organization_id", "joined_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ONBOARDING", index=True)
    joined_at: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    last_working_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    offboarding_initiated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class LifecycleTask(Base):
    __tablename__ = "lifecycle_tasks"
    __table_args__ = (
        Index("ix_lifecycle_tasks_org_status", "organization_id", "status"),
        Index("ix_lifecycle_tasks_lifecycle_status", "lifecycle_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(nullable=False, index=True)
    lifecycle_id: Mapped[int] = mapped_column(ForeignKey("employee_lifecycles.id"), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN", index=True)
    action_status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    assignee_id: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)
    related_subscription_id: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)
    related_subscription_assignment_id: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)
    related_asset_id: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)
    related_asset_assignment_id: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)
    due_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_by: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)
    completion_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class OutboxEvent(Base, OutboxRecordMixin):
    __tablename__ = "outbox_events"
