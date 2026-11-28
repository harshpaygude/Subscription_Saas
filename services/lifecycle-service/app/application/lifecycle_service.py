"""Application service for Employee Lifecycle orchestration (DIP & OCP)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from unisora_kit import ConflictError, DomainValidationError, NotFoundError, RequestContext
from app.application.task_verifiers import DEFAULT_TASK_VERIFIERS, TaskCompletionVerifier
from app.domain.entities import EmployeeLifecycleEntity, LifecycleTaskEntity
from app.domain.ports import (
    AssetPort,
    AuditEventPort,
    IdentityPort,
    LifecycleRepository,
    LifecycleTaskRepository,
    SubscriptionPort,
)


class LifecycleService:
    def __init__(
        self,
        lifecycles: LifecycleRepository,
        tasks: LifecycleTaskRepository,
        identity: IdentityPort,
        subscriptions: SubscriptionPort,
        assets: AssetPort,
        audit: AuditEventPort,
        verifiers: Optional[dict[str, TaskCompletionVerifier]] = None,
    ):
        self.lifecycles = lifecycles
        self.tasks = tasks
        self.identity = identity
        self.subscriptions = subscriptions
        self.assets = assets
        self.audit = audit
        self.verifiers = verifiers or DEFAULT_TASK_VERIFIERS

    def ensure_active(self, *, organization_id: int, user_id: int, joined_at: date) -> EmployeeLifecycleEntity:
        existing = self.lifecycles.get_by_user(user_id, organization_id)
        if existing:
            return existing
        now = datetime.utcnow()
        return self.lifecycles.create(
            EmployeeLifecycleEntity(
                id=None,
                organization_id=organization_id,
                user_id=user_id,
                status="ACTIVE",
                joined_at=joined_at,
                last_working_date=None,
                offboarding_initiated_at=None,
                completed_at=None,
                created_at=now,
                updated_at=now,
            )
        )

    def start_onboarding(
        self,
        *,
        ctx: RequestContext,
        user_id: int,
        department_id: int,
        joined_at: date,
        task_specs: list[dict[str, Any]],
    ) -> EmployeeLifecycleEntity:
        self.identity.get_user(ctx, user_id)
        lifecycle = self.lifecycles.get_by_user(user_id, ctx.organization_id)
        if lifecycle and lifecycle.status == "OFFBOARDING":
            raise DomainValidationError("Cannot start onboarding while offboarding is active.")

        now = datetime.utcnow()
        if lifecycle is None:
            lifecycle = self.lifecycles.create(
                EmployeeLifecycleEntity(
                    id=None,
                    organization_id=ctx.organization_id,
                    user_id=user_id,
                    status="ONBOARDING",
                    joined_at=joined_at,
                    last_working_date=None,
                    offboarding_initiated_at=None,
                    completed_at=None,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            lifecycle.status = "ONBOARDING"
            lifecycle.joined_at = joined_at
            lifecycle.last_working_date = None
            lifecycle.completed_at = None
            lifecycle = self.lifecycles.save(lifecycle)

        self.identity.sync_onboarding_membership(ctx, user_id, department_id, joined_at)
        assert lifecycle.id is not None

        for spec in task_specs:
            ttype = spec["task_type"]
            if ttype == "SUBSCRIPTION_ACCESS":
                sub_id = spec.get("subscription_id")
                if not sub_id:
                    raise DomainValidationError("Subscription access tasks require a subscription.")
                if not self.subscriptions.subscription_exists(ctx, sub_id):
                    raise DomainValidationError("Subscription not found in this organization.")
            elif ttype == "ASSET_ISSUE":
                asset_id = spec.get("asset_id")
                if not asset_id:
                    raise DomainValidationError("Asset issue tasks require an asset.")
                if not self.assets.get_asset(ctx, asset_id):
                    raise DomainValidationError("Asset not found in this organization.")

            self.tasks.create(
                LifecycleTaskEntity(
                    id=None,
                    organization_id=ctx.organization_id,
                    lifecycle_id=lifecycle.id,
                    task_type=ttype,
                    title=spec["title"],
                    status="OPEN",
                    action_status="PENDING",
                    required=bool(spec.get("required", True)),
                    assignee_id=None,
                    related_subscription_id=spec.get("subscription_id"),
                    related_subscription_assignment_id=None,
                    related_asset_id=spec.get("asset_id"),
                    related_asset_assignment_id=None,
                    due_at=spec.get("due_at"),
                    completed_at=None,
                    completed_by=None,
                    completion_note=None,
                    created_at=now,
                    updated_at=now,
                )
            )

        if self.tasks.count_open_required(lifecycle.id) == 0:
            lifecycle.status = "ACTIVE"
            lifecycle = self.lifecycles.save(lifecycle)

        self.audit.record(
            organization_id=ctx.organization_id,
            actor_id=ctx.user_id,
            action="employee.onboarding.started",
            entity_type="employee_lifecycle",
            entity_id=lifecycle.id,
            details={"user_id": user_id},
        )
        return lifecycle

    def start_offboarding(
        self,
        *,
        ctx: RequestContext,
        user_id: int,
        last_working_date: date,
    ) -> EmployeeLifecycleEntity:
        lifecycle = self.lifecycles.get_by_user(user_id, ctx.organization_id)
        if not lifecycle:
            raise NotFoundError("Employee lifecycle profile not found. Start onboarding first.")
        if lifecycle.status == "COMPLETED":
            raise ConflictError("Completed offboarding cannot be restarted.")

        now = datetime.utcnow()
        lifecycle.status = "OFFBOARDING"
        lifecycle.last_working_date = last_working_date
        lifecycle.offboarding_initiated_at = now
        lifecycle = self.lifecycles.save(lifecycle)
        assert lifecycle.id is not None

        self.identity.deactivate_memberships(ctx, user_id, last_working_date)

        for asgn in self.subscriptions.list_user_assignments(ctx, user_id, status="ACTIVE"):
            asgn_id = int(asgn["id"])
            if not self.tasks.find_open_by_related(
                lifecycle.id, "REVOKE_SUBSCRIPTION", subscription_assignment_id=asgn_id
            ):
                self.tasks.create(
                    LifecycleTaskEntity(
                        id=None,
                        organization_id=ctx.organization_id,
                        lifecycle_id=lifecycle.id,
                        task_type="REVOKE_SUBSCRIPTION",
                        title="Revoke software access",
                        status="OPEN",
                        action_status="PENDING",
                        required=True,
                        assignee_id=None,
                        related_subscription_id=asgn.get("subscription_id"),
                        related_subscription_assignment_id=asgn_id,
                        related_asset_id=None,
                        related_asset_assignment_id=None,
                        due_at=None,
                        completed_at=None,
                        completed_by=None,
                        completion_note=None,
                        created_at=now,
                        updated_at=now,
                    )
                )

        for asgn in self.assets.list_user_assignments(ctx, user_id, status="ACTIVE"):
            asgn_id = int(asgn["id"])
            asset_id = int(asgn["asset_id"])
            asset_label = asgn.get("resource_name") or f"Asset #{asset_id}"
            if not self.tasks.find_open_by_related(
                lifecycle.id, "RECOVER_ASSET", asset_assignment_id=asgn_id
            ):
                self.tasks.create(
                    LifecycleTaskEntity(
                        id=None,
                        organization_id=ctx.organization_id,
                        lifecycle_id=lifecycle.id,
                        task_type="RECOVER_ASSET",
                        title=f"Recover company asset: {asset_label}",
                        status="OPEN",
                        action_status="PENDING",
                        required=True,
                        assignee_id=None,
                        related_subscription_id=None,
                        related_subscription_assignment_id=None,
                        related_asset_id=asset_id,
                        related_asset_assignment_id=asgn_id,
                        due_at=None,
                        completed_at=None,
                        completed_by=None,
                        completion_note=None,
                        created_at=now,
                        updated_at=now,
                    )
                )

        if self.tasks.count_open_required(lifecycle.id) == 0:
            lifecycle.status = "COMPLETED"
            lifecycle.completed_at = datetime.utcnow()
            lifecycle = self.lifecycles.save(lifecycle)

        self.audit.record(
            organization_id=ctx.organization_id,
            actor_id=ctx.user_id,
            action="employee.offboarding.started",
            entity_type="employee_lifecycle",
            entity_id=lifecycle.id,
            details={"user_id": user_id, "last_working_date": str(last_working_date)},
        )
        return lifecycle

    def complete_task(
        self, *, ctx: RequestContext, task_id: int, completion_note: Optional[str]
    ) -> LifecycleTaskEntity:
        task = self.tasks.get_by_id(task_id, ctx.organization_id)
        if not task:
            raise NotFoundError("Lifecycle task not found.")
        if task.status == "COMPLETED":
            return task

        lifecycle = self.lifecycles.get_by_id(task.lifecycle_id, ctx.organization_id)
        if not lifecycle:
            raise NotFoundError("Employee lifecycle profile not found.")

        verifier = self.verifiers.get(task.task_type, self.verifiers["MANUAL_ACCESS"])
        task.action_status = verifier.verify_and_next_status(
            ctx=ctx,
            task=task,
            lifecycle=lifecycle,
            completion_note=completion_note,
            subscriptions=self.subscriptions,
            assets=self.assets,
        )
        task.status = "COMPLETED"
        task.completed_at = datetime.utcnow()
        task.completed_by = ctx.user_id
        task.completion_note = completion_note
        saved_task = self.tasks.save(task)

        if self.tasks.count_open_required(lifecycle.id or 0) == 0:
            if lifecycle.status == "ONBOARDING":
                lifecycle.status = "ACTIVE"
            elif lifecycle.status == "OFFBOARDING":
                lifecycle.status = "COMPLETED"
                lifecycle.completed_at = datetime.utcnow()
            self.lifecycles.save(lifecycle)

        assert saved_task.id is not None
        self.audit.record(
            organization_id=ctx.organization_id,
            actor_id=ctx.user_id,
            action="employee.lifecycle_task.completed",
            entity_type="lifecycle_task",
            entity_id=saved_task.id,
            details={"task_type": saved_task.task_type, "action_status": saved_task.action_status},
        )
        return saved_task

    def get_employee_lifecycle_view(self, ctx: RequestContext, user_id: int) -> dict[str, Any]:
        lifecycle = self.lifecycles.get_by_user(user_id, ctx.organization_id)
        if not lifecycle:
            raise NotFoundError("Employee lifecycle profile not found.")
        user = self.identity.get_user(ctx, user_id)
        depts = {d["id"]: d["name"] for d in self.identity.list_departments(ctx)}
        sub_assigns = self.subscriptions.list_user_assignments(ctx, user_id)
        asset_assigns = self.assets.list_user_assignments(ctx, user_id)
        tasks = self.tasks.list_by_lifecycle(lifecycle.id or 0)
        return self._build_employee_view(lifecycle, user, depts, sub_assigns, asset_assigns, tasks)

    def get_dashboard(self, ctx: RequestContext) -> dict[str, Any]:
        lifecycles = self.lifecycles.list_by_org(ctx.organization_id)
        pending_tasks = self.tasks.list_by_org(ctx.organization_id, status="OPEN")
        users_by_id = {u["id"]: u for u in self.identity.list_users(ctx)}
        depts = {d["id"]: d["name"] for d in self.identity.list_departments(ctx)}

        sub_by_user: dict[int, list[dict[str, Any]]] = {}
        for a in self.subscriptions.list_all_assignments(ctx):
            sub_by_user.setdefault(int(a["user_id"]), []).append(a)

        asset_by_user: dict[int, list[dict[str, Any]]] = {}
        for a in self.assets.list_all_assignments(ctx):
            asset_by_user.setdefault(int(a["user_id"]), []).append(a)

        all_views = []
        for lc in lifecycles:
            user = users_by_id.get(lc.user_id)
            if not user:
                continue
            tasks = self.tasks.list_by_lifecycle(lc.id or 0)
            all_views.append(
                self._build_employee_view(
                    lc,
                    user,
                    depts,
                    sub_by_user.get(lc.user_id, []),
                    asset_by_user.get(lc.user_id, []),
                    tasks,
                )
            )

        return {
            "new_joiners": [v for v in all_views if v["status"] == "ONBOARDING"],
            "working": [v for v in all_views if v["status"] == "ACTIVE"],
            "offboarding": [v for v in all_views if v["status"] == "OFFBOARDING"],
            "completed": [v for v in all_views if v["status"] == "COMPLETED"],
            "pending_tasks": [t.__dict__ for t in pending_tasks],
        }

    def list_tasks(self, organization_id: int, status_filter: Optional[str] = None) -> list[LifecycleTaskEntity]:
        return self.tasks.list_by_org(organization_id, status=status_filter)

    @staticmethod
    def _build_employee_view(
        lifecycle: EmployeeLifecycleEntity,
        user: dict[str, Any],
        depts: dict[int, str],
        sub_assigns: list[dict[str, Any]],
        asset_assigns: list[dict[str, Any]],
        tasks: list[LifecycleTaskEntity],
    ) -> dict[str, Any]:
        dept_ids = list(user.get("department_ids") or [])
        return {
            "id": lifecycle.id,
            "user_id": lifecycle.user_id,
            "email": user["email"],
            "display_name": user.get("display_name"),
            "employee_id": user.get("employee_id"),
            "phone_number": user.get("phone_number"),
            "role": user["role"],
            "status": lifecycle.status,
            "joined_at": lifecycle.joined_at,
            "last_working_date": lifecycle.last_working_date,
            "department_ids": dept_ids,
            "department_names": [depts[d] for d in dept_ids if d in depts],
            "subscription_assignments": [
                {
                    "id": a["id"],
                    "resource_id": a["subscription_id"],
                    "status": a["status"],
                    "assigned_at": a["assigned_at"],
                    "released_at": a.get("released_at"),
                    "resource_name": a.get("resource_name"),
                    "resource_provider": a.get("resource_provider"),
                }
                for a in sub_assigns
            ],
            "asset_assignments": [
                {
                    "id": a["id"],
                    "resource_id": a["asset_id"],
                    "status": a["status"],
                    "assigned_at": a["assigned_at"],
                    "released_at": a.get("returned_at"),
                    "resource_name": a.get("resource_name"),
                    "resource_provider": a.get("resource_provider"),
                }
                for a in asset_assigns
            ],
            "tasks": [t.__dict__ for t in tasks],
            "open_task_count": sum(1 for t in tasks if t.status == "OPEN" and t.required),
            "completed_task_count": sum(1 for t in tasks if t.status == "COMPLETED"),
        }
