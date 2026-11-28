"""Open/Closed Strategy Registry for verifying lifecycle task completion."""
from __future__ import annotations

from typing import Optional, Protocol

from unisora_kit import ConflictError, RequestContext
from app.domain.entities import EmployeeLifecycleEntity, LifecycleTaskEntity
from app.domain.ports import AssetPort, SubscriptionPort


class TaskCompletionVerifier(Protocol):
    def verify_and_next_status(
        self,
        *,
        ctx: RequestContext,
        task: LifecycleTaskEntity,
        lifecycle: EmployeeLifecycleEntity,
        completion_note: Optional[str],
        subscriptions: SubscriptionPort,
        assets: AssetPort,
    ) -> str: ...


class RevokeSubscriptionVerifier:
    def verify_and_next_status(self, *, ctx, task, lifecycle, completion_note, subscriptions, assets) -> str:
        del lifecycle, completion_note, assets
        if not task.related_subscription_assignment_id:
            raise ConflictError("Release the subscription assignment before completing this clearance task.")
        assignment = subscriptions.get_assignment(ctx, task.related_subscription_assignment_id)
        if not assignment or assignment.get("status") != "RELEASED":
            raise ConflictError("Release the subscription assignment before completing this clearance task.")
        return "REVOKED"


class RecoverAssetVerifier:
    def verify_and_next_status(self, *, ctx, task, lifecycle, completion_note, subscriptions, assets) -> str:
        del lifecycle, completion_note, subscriptions
        if not task.related_asset_assignment_id:
            raise ConflictError("Return the asset before completing this clearance task.")
        assignment = assets.get_assignment(ctx, task.related_asset_assignment_id)
        if not assignment or assignment.get("status") != "RETURNED":
            raise ConflictError("Return the asset before completing this clearance task.")
        return "RETURNED"


class SubscriptionAccessVerifier:
    def verify_and_next_status(self, *, ctx, task, lifecycle, completion_note, subscriptions, assets) -> str:
        del completion_note, assets
        if not task.related_subscription_id:
            raise ConflictError("Assign the requested subscription license before completing this task.")
        active = subscriptions.list_user_assignments(ctx, lifecycle.user_id, status="ACTIVE")
        if not any(a.get("subscription_id") == task.related_subscription_id for a in active):
            raise ConflictError("Assign the requested subscription license before completing this task.")
        return "ASSIGNED"


class AssetIssueVerifier:
    def verify_and_next_status(self, *, ctx, task, lifecycle, completion_note, subscriptions, assets) -> str:
        del completion_note, subscriptions
        if not task.related_asset_id:
            raise ConflictError("Assign the requested asset before completing this task.")
        active = assets.list_user_assignments(ctx, lifecycle.user_id, status="ACTIVE")
        if not any(a.get("asset_id") == task.related_asset_id for a in active):
            raise ConflictError("Assign the requested asset before completing this task.")
        return "ASSIGNED"


class ManualAccessVerifier:
    def verify_and_next_status(self, *, ctx, task, lifecycle, completion_note, subscriptions, assets) -> str:
        del ctx, task, lifecycle, subscriptions, assets
        if not completion_note or not completion_note.strip():
            raise ConflictError("A verification note is required for manual access tasks.")
        return "VERIFIED"


DEFAULT_TASK_VERIFIERS: dict[str, TaskCompletionVerifier] = {
    "REVOKE_SUBSCRIPTION": RevokeSubscriptionVerifier(),
    "RECOVER_ASSET": RecoverAssetVerifier(),
    "SUBSCRIPTION_ACCESS": SubscriptionAccessVerifier(),
    "ASSET_ISSUE": AssetIssueVerifier(),
    "MANUAL_ACCESS": ManualAccessVerifier(),
}
