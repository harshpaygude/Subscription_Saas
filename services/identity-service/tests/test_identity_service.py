import io
import os
import sys
import unittest
from datetime import date, datetime
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from fastapi.testclient import TestClient
import openpyxl
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from unisora_kit import RequestContext
from app.api.deps import (
    get_current_context,
    get_department_service,
    get_organization_service,
)
from app.application.department_service import DepartmentService
from app.application.organization_service import OrganizationService
from app.infrastructure.adapters import OutboxAuditAdapter
from app.infrastructure.db import Base, get_db
from app.infrastructure.models import Department, Organization, User
from app.infrastructure.repositories import (
    SqlAlchemyDepartmentRepository,
    SqlAlchemyOrganizationRepository,
    SqlAlchemyUserRepository,
)
from app.infrastructure.security import BcryptPasswordHasher
from app.main import app
from unisora_kit import OutboxDispatcher


class _FakeLifecyclePort:
    def __init__(self):
        self.calls = []

    def ensure_active_lifecycle(self, ctx, user_id, joined_at):
        self.calls.append((user_id, joined_at))


class _FakeAssetPort:
    def __init__(self):
        self.imported = []

    def get_active_assignment_counts(self, ctx):
        return {}

    def validate_available_assets(self, ctx, asset_ids):
        return asset_ids

    def assign_assets_to_user(self, ctx, user_id, asset_ids, reassign=False):
        pass

    def create_and_assign_assets(self, ctx, assets, user_lookup):
        self.imported.append((assets, user_lookup))
        return len(assets), sum(1 for a in assets if a.get("assigned_to") and a["assigned_to"].lower() in user_lookup)


class _FakeSubscriptionPort:
    def get_active_assignment_counts(self, ctx):
        return {}

    def assign_subscriptions_to_user(self, ctx, user_id, subscription_ids):
        pass

    def import_subscriptions(self, ctx, subscriptions):
        return len(subscriptions)

    def ensure_subscription_and_assign(self, ctx, user_id, sub_name, plan, amount):
        return True


class _FakeIntegrationPort:
    def seed_connections(self, ctx, integrations):
        pass


class IdentityServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.org = Organization(name="UniSora Org", created_at=datetime.utcnow())
        self.other_org = Organization(name="Other Org", created_at=datetime.utcnow())
        self.db.add_all([self.org, self.other_org])
        self.db.flush()

        self.owner = User(
            email="owner@unisora.test",
            display_name="UniSora Admin",
            password_hash="test-hash",
            organization_id=self.org.id,
            role="OWNER",
            created_at=datetime.utcnow(),
        )
        self.member = User(
            email="member@unisora.test",
            display_name="Regular Member",
            password_hash="test-hash",
            organization_id=self.org.id,
            role="MEMBER",
            created_at=datetime.utcnow(),
        )
        self.other_employee = User(
            email="employee@other.test",
            display_name="Other Emp",
            password_hash="test-hash",
            organization_id=self.other_org.id,
            role="MEMBER",
            created_at=datetime.utcnow(),
        )
        self.db.add_all([self.owner, self.member, self.other_employee])
        self.db.commit()

        self.current_user = self.owner
        self.fake_lifecycle = _FakeLifecyclePort()
        self.fake_assets = _FakeAssetPort()
        self.fake_subs = _FakeSubscriptionPort()
        self.fake_integrations = _FakeIntegrationPort()
        self.dispatcher = OutboxDispatcher(source_service="identity-service", internal_secret="test-secret")

        def db_override():
            yield self.db

        def ctx_override():
            return RequestContext(
                user_id=self.current_user.id,
                organization_id=self.current_user.organization_id,
                role=self.current_user.role,
                email=self.current_user.email,
            )

        def org_service_override():
            return OrganizationService(
                organizations=SqlAlchemyOrganizationRepository(self.db),
                users=SqlAlchemyUserRepository(self.db),
                departments=SqlAlchemyDepartmentRepository(self.db),
                hasher=BcryptPasswordHasher(),
                lifecycle_port=self.fake_lifecycle,
                asset_port=self.fake_assets,
                subscription_port=self.fake_subs,
                integration_port=self.fake_integrations,
                audit=OutboxAuditAdapter(self.db, self.dispatcher),
            )

        app.dependency_overrides[get_db] = db_override
        app.dependency_overrides[get_current_context] = ctx_override
        app.dependency_overrides[get_organization_service] = org_service_override
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()
        self.db.close()
        self.engine.dispose()

    def test_membership_rejects_cross_organization_user(self):
        dept = Department(organization_id=self.org.id, name="Developers")
        self.db.add(dept)
        self.db.commit()
        svc = DepartmentService(
            departments=SqlAlchemyDepartmentRepository(self.db),
            users=SqlAlchemyUserRepository(self.db),
            audit=OutboxAuditAdapter(self.db, self.dispatcher),
        )
        with self.assertRaises(Exception):
            svc.add_membership(
                organization_id=self.org.id,
                actor_id=self.owner.id,
                department_id=dept.id,
                user_id=self.other_employee.id,
                effective_from=date.today(),
            )

    def test_onboarding_status_initial_state(self):
        res = self.client.get("/organizations/me/onboarding-status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["onboarding_completed"])
        self.assertIsNone(data["onboarding_completed_at"])

    def test_profile_update(self):
        res = self.client.patch(
            "/organizations/me/profile",
            json={"legal_name": "UniSora Global Corp", "industry": "Technology & Software", "city": "San Francisco"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["legal_name"], "UniSora Global Corp")

    def test_onboarding_submission_marks_completed_and_creates_departments(self):
        payload = {
            "company": {"legal_name": "Enterprise Inc", "display_name": "Enterprise"},
            "departments": [
                {"name": "Engineering", "description": "Core platform engineering"},
                {"name": "Finance & Accounting", "description": "Financial planning"},
            ],
        }
        res = self.client.post("/organizations/me/onboarding", json=payload)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["onboarding_completed"])
        depts = self.db.query(Department).filter(Department.organization_id == self.org.id).all()
        self.assertIn("Engineering", {d.name for d in depts})

    def test_non_admin_cannot_submit_onboarding(self):
        self.current_user = self.member
        res = self.client.post("/organizations/me/onboarding", json={"company": {"legal_name": "Hacker Corp"}, "departments": []})
        self.assertEqual(res.status_code, 403)

    def test_excel_template_and_parse(self):
        res = self.client.get("/organizations/me/onboarding/excel-template")
        self.assertEqual(res.status_code, 200)
        wb = openpyxl.load_workbook(io.BytesIO(res.content))
        self.assertIn("Company", wb.sheetnames)
        self.assertIn("Departments", wb.sheetnames)

        buf = io.BytesIO()
        wb.save(buf)
        parse_res = self.client.post(
            "/organizations/me/onboarding/parse-excel",
            files={"file": ("test.xlsx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        self.assertEqual(parse_res.status_code, 200)
        self.assertTrue(parse_res.json()["valid"])

    def test_onboarding_submission_creates_employees_and_delegates_assets(self):
        payload = {
            "company": {"legal_name": "Tech Corp"},
            "departments": [{"name": "Engineering"}],
            "employees": [{"employee_id": "EMP-999", "full_name": "John Doe", "email": "johndoe@techcorp.test", "department_name": "Engineering"}],
            "assets": [{"asset_tag": "AST-LAP-999", "name": "ThinkPad T14", "asset_type": "Laptop", "assigned_to": "johndoe@techcorp.test"}],
        }
        res = self.client.post("/organizations/me/onboarding", json=payload)
        self.assertEqual(res.status_code, 200)
        emp = self.db.query(User).filter(User.email == "johndoe@techcorp.test").first()
        self.assertIsNotNone(emp)
        self.assertEqual(len(self.fake_lifecycle.calls), 1)
        self.assertEqual(len(self.fake_assets.imported), 1)

    def test_auth_register_and_login_flow(self):
        reg = self.client.post(
            "/auth/register",
            json={"email": "founder@newco.io", "password": "StrongPassword123!", "organization_name": "NewCo"},
        )
        self.assertEqual(reg.status_code, 200)
        login = self.client.post("/auth/login", json={"email": "founder@newco.io", "password": "StrongPassword123!"})
        self.assertEqual(login.status_code, 200)
        self.assertIn("access_token", login.json())


if __name__ == "__main__":
    unittest.main()
