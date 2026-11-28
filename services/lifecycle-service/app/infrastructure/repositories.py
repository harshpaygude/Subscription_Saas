"""SQLAlchemy repositories for Lifecycle Service."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.domain.entities import EmployeeLifecycleEntity, LifecycleTaskEntity
from app.infrastructure.models import EmployeeLifecycle, LifecycleTask


def _to_lifecycle(row: EmployeeLifecycle) -> EmployeeLifecycleEntity:
    return EmployeeLifecycleEntity(
        id=row.id,
        organization_id=row.organization_id,
        user_id=row.user_id,
        status=row.status,
        joined_at=row.joined_at,
        last_working_date=row.last_working_date,
        offboarding_initiated_at=row.offboarding_initiated_at,
        completed_at=row.completed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_task(row: LifecycleTask) -> LifecycleTaskEntity:
    return LifecycleTaskEntity(
        id=row.id,
        organization_id=row.organization_id,
        lifecycle_id=row.lifecycle_id,
        task_type=row.task_type,
        title=row.title,
        status=row.status,
        action_status=row.action_status,
        required=row.required,
        assignee_id=row.assignee_id,
        related_subscription_id=row.related_subscription_id,
        related_subscription_assignment_id=row.related_subscription_assignment_id,
        related_asset_id=row.related_asset_id,
        related_asset_assignment_id=row.related_asset_assignment_id,
        due_at=row.due_at,
        completed_at=row.completed_at,
        completed_by=row.completed_by,
        completion_note=row.completion_note,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyLifecycleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, lifecycle_id: int, organization_id: int) -> Optional[EmployeeLifecycleEntity]:
        row = self.db.query(EmployeeLifecycle).filter(
            EmployeeLifecycle.id == lifecycle_id, EmployeeLifecycle.organization_id == organization_id
        ).first()
        return _to_lifecycle(row) if row else None

    def get_by_user(self, user_id: int, organization_id: int) -> Optional[EmployeeLifecycleEntity]:
        row = self.db.query(EmployeeLifecycle).filter(
            EmployeeLifecycle.user_id == user_id, EmployeeLifecycle.organization_id == organization_id
        ).first()
        return _to_lifecycle(row) if row else None

    def list_by_org(self, organization_id: int) -> list[EmployeeLifecycleEntity]:
        rows = (
            self.db.query(EmployeeLifecycle)
            .filter(EmployeeLifecycle.organization_id == organization_id)
            .order_by(EmployeeLifecycle.updated_at.desc())
            .all()
        )
        return [_to_lifecycle(r) for r in rows]

    def create(self, lifecycle: EmployeeLifecycleEntity) -> EmployeeLifecycleEntity:
        row = EmployeeLifecycle(
            organization_id=lifecycle.organization_id,
            user_id=lifecycle.user_id,
            status=lifecycle.status,
            joined_at=lifecycle.joined_at,
            last_working_date=lifecycle.last_working_date,
            offboarding_initiated_at=lifecycle.offboarding_initiated_at,
            completed_at=lifecycle.completed_at,
        )
        self.db.add(row)
        self.db.flush()
        return _to_lifecycle(row)

    def save(self, lifecycle: EmployeeLifecycleEntity) -> EmployeeLifecycleEntity:
        row = self.db.query(EmployeeLifecycle).filter(
            EmployeeLifecycle.id == lifecycle.id, EmployeeLifecycle.organization_id == lifecycle.organization_id
        ).first()
        if not row:
            raise ValueError("Lifecycle not found")
        row.status = lifecycle.status
        row.joined_at = lifecycle.joined_at
        row.last_working_date = lifecycle.last_working_date
        row.offboarding_initiated_at = lifecycle.offboarding_initiated_at
        row.completed_at = lifecycle.completed_at
        self.db.flush()
        return _to_lifecycle(row)


class SqlAlchemyLifecycleTaskRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, task_id: int, organization_id: int) -> Optional[LifecycleTaskEntity]:
        row = self.db.query(LifecycleTask).filter(
            LifecycleTask.id == task_id, LifecycleTask.organization_id == organization_id
        ).first()
        return _to_task(row) if row else None

    def list_by_lifecycle(self, lifecycle_id: int) -> list[LifecycleTaskEntity]:
        rows = (
            self.db.query(LifecycleTask)
            .filter(LifecycleTask.lifecycle_id == lifecycle_id)
            .order_by(LifecycleTask.created_at.asc())
            .all()
        )
        return [_to_task(r) for r in rows]

    def list_by_org(self, organization_id: int, *, status: Optional[str] = None) -> list[LifecycleTaskEntity]:
        query = self.db.query(LifecycleTask).filter(LifecycleTask.organization_id == organization_id)
        if status:
            query = query.filter(LifecycleTask.status == status.upper())
        rows = query.order_by(LifecycleTask.due_at.asc().nullslast(), LifecycleTask.created_at.asc()).all()
        return [_to_task(r) for r in rows]

    def count_open_required(self, lifecycle_id: int) -> int:
        return (
            self.db.query(LifecycleTask)
            .filter(
                LifecycleTask.lifecycle_id == lifecycle_id,
                LifecycleTask.required.is_(True),
                LifecycleTask.status == "OPEN",
            )
            .count()
        )

    def find_open_by_related(
        self,
        lifecycle_id: int,
        task_type: str,
        *,
        subscription_assignment_id: Optional[int] = None,
        asset_assignment_id: Optional[int] = None,
    ) -> Optional[LifecycleTaskEntity]:
        query = self.db.query(LifecycleTask).filter(
            LifecycleTask.lifecycle_id == lifecycle_id,
            LifecycleTask.task_type == task_type,
            LifecycleTask.status == "OPEN",
        )
        if subscription_assignment_id is not None:
            query = query.filter(LifecycleTask.related_subscription_assignment_id == subscription_assignment_id)
        if asset_assignment_id is not None:
            query = query.filter(LifecycleTask.related_asset_assignment_id == asset_assignment_id)
        row = query.first()
        return _to_task(row) if row else None

    def create(self, task: LifecycleTaskEntity) -> LifecycleTaskEntity:
        row = LifecycleTask(
            organization_id=task.organization_id,
            lifecycle_id=task.lifecycle_id,
            task_type=task.task_type,
            title=task.title,
            status=task.status,
            action_status=task.action_status,
            required=task.required,
            assignee_id=task.assignee_id,
            related_subscription_id=task.related_subscription_id,
            related_subscription_assignment_id=task.related_subscription_assignment_id,
            related_asset_id=task.related_asset_id,
            related_asset_assignment_id=task.related_asset_assignment_id,
            due_at=task.due_at,
        )
        self.db.add(row)
        self.db.flush()
        return _to_task(row)

    def save(self, task: LifecycleTaskEntity) -> LifecycleTaskEntity:
        row = self.db.query(LifecycleTask).filter(LifecycleTask.id == task.id).first()
        if not row:
            raise ValueError("Task not found")
        row.status = task.status
        row.action_status = task.action_status
        row.completed_at = task.completed_at
        row.completed_by = task.completed_by
        row.completion_note = task.completion_note
        self.db.flush()
        return _to_task(row)
