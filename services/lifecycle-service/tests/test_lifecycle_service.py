import sys
import unittest
from datetime import date
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from unisora_kit import OutboxDispatcher, RequestContext
from app.application.lifecycle_service import LifecycleService
from app.infrastructure.adapters import OutboxAuditAdapter
from app.infrastructure.db import Base
from app.infrastructure.repositories import SqlAlchemyLifecycleRepository, SqlAlchemyLifecycleTaskRepository


class _FakeIdentityPort:
    def __init__(self):
        self.active_memberships = set()

    def get_user(self, ctx, user_id):
        return {"id": user_id, "email": "new@acme.test", "display_name": "New", "role": "MEMBER", "department_ids": [1]}

    def list_users(self, ctx):
        return [self.get_user(ctx, 2)]

    def list_departments(self, ctx):
        return [{"id": 1, "name": "Developers", "is_active": True}]

    def sync_onboarding_membership(self, ctx, user_id, department_id, effective_from):
        self.active_memberships.add((user_id, department_id))

    def deactivate_memberships(self, ctx, user_id, effective_to):
        self.active_memberships = {m for m in self.active_memberships if m[0] != user_id}


class _FakeSubscriptionPort:
    def __init__(self):
        self.assignments = {10: {"id": 10, "subscription_id": 1, "user_id": 2, "status": "ACTIVE"}}

    def subscription_exists(self, ctx, subscription_id):
        return subscription_id == 1

    def list_user_assignments(self, ctx, user_id, status=None):
        return [a for a in self.assignments.values() if a["user_id"] == user_id and (status is None or a["status"] == status)]

    def list_all_assignments(self, ctx):
        return list(self.assignments.values())

    def get_assignment(self, ctx, assignment_id):
        return self.assignments.get(assignment_id)


class _FakeAssetPort:
    def __init__(self):
        self.assignments = {20: {"id": 20, "asset_id": 5, "user_id": 2, "status": "ACTIVE", "resource_name": "Laptop (LT-001)"}}

    def get_asset(self, ctx, asset_id):
        return {"id": asset_id, "name": "Laptop", "asset_tag": "LT-001"} if asset_id == 5 else None

    def list_user_assignments(self, ctx, user_id, status=None):
        return [a for a in self.assignments.values() if a["user_id"] == user_id and (status is None or a["status"] == status)]

    def list_all_assignments(self, ctx):
        return list(self.assignments.values())

    def get_assignment(self, ctx, assignment_id):
        return self.assignments.get(assignment_id)


class LifecycleServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.dispatcher = OutboxDispatcher(source_service="lifecycle-service", internal_secret="test-secret")
        self.identity = _FakeIdentityPort()
        self.subs = _FakeSubscriptionPort()
        self.assets = _FakeAssetPort()
        self.ctx = RequestContext(user_id=1, organization_id=1, role="OWNER")
        self.lc_repo = SqlAlchemyLifecycleRepository(self.db)
        self.task_repo = SqlAlchemyLifecycleTaskRepository(self.db)
        self.svc = LifecycleService(
            lifecycles=self.lc_repo,
            tasks=self.task_repo,
            identity=self.identity,
            subscriptions=self.subs,
            assets=self.assets,
            audit=OutboxAuditAdapter(self.db, self.dispatcher),
        )

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_onboarding_task_requires_note_before_completion(self):
        lc = self.svc.start_onboarding(
            ctx=self.ctx,
            user_id=2,
            department_id=1,
            joined_at=date.today(),
            task_specs=[{"task_type": "MANUAL_ACCESS", "title": "Verify HR access", "required": True}],
        )
        self.db.commit()
        task = self.task_repo.list_by_lifecycle(lc.id)[0]
        with self.assertRaises(Exception):
            self.svc.complete_task(ctx=self.ctx, task_id=task.id, completion_note=None)
        done_task = self.svc.complete_task(ctx=self.ctx, task_id=task.id, completion_note="HR verified")
        self.db.commit()
        self.assertEqual(done_task.status, "COMPLETED")
        self.assertEqual(self.lc_repo.get_by_id(lc.id, 1).status, "ACTIVE")

    def test_lifecycle_keeps_department_membership_in_sync(self):
        lc = self.svc.start_onboarding(ctx=self.ctx, user_id=2, department_id=1, joined_at=date.today(), task_specs=[])
        self.assertIn((2, 1), self.identity.active_memberships)
        self.svc.start_offboarding(ctx=self.ctx, user_id=2, last_working_date=date.today())
        self.assertNotIn((2, 1), self.identity.active_memberships)

    def test_offboarding_requires_release_and_return_before_clearance(self):
        self.svc.ensure_active(organization_id=1, user_id=2, joined_at=date.today())
        lc = self.svc.start_offboarding(ctx=self.ctx, user_id=2, last_working_date=date.today())
        self.db.commit()
        tasks = self.task_repo.list_by_lifecycle(lc.id)
        self.assertEqual({t.task_type for t in tasks}, {"REVOKE_SUBSCRIPTION", "RECOVER_ASSET"})
        for t in tasks:
            with self.assertRaises(Exception):
                self.svc.complete_task(ctx=self.ctx, task_id=t.id, completion_note=None)
        self.subs.assignments[10]["status"] = "RELEASED"
        self.assets.assignments[20]["status"] = "RETURNED"
        for t in tasks:
            self.svc.complete_task(ctx=self.ctx, task_id=t.id, completion_note=None)
        self.db.commit()
        self.assertEqual(self.lc_repo.get_by_id(lc.id, 1).status, "COMPLETED")


if __name__ == "__main__":
    unittest.main()
