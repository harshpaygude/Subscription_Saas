import unittest
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.assets.service import assign_asset, return_asset
from app.database.models import Asset, Department, DepartmentMembership, EmployeeLifecycle, LifecycleTask, Organization, Subscription, SubscriptionAssignment, SubscriptionLicense, User
from app.database.session import Base
from app.employee_lifecycle.schemas import OnboardingTaskRequest
from app.employee_lifecycle.service import complete_task, start_offboarding, start_onboarding
from app.license_assignments.service import assign_license, release_license


class EmployeeLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.org = Organization(name="Acme")
        self.db.add(self.org)
        self.db.flush()
        self.admin = User(email="admin@acme.test", password_hash="x", organization_id=self.org.id, role="OWNER")
        self.employee = User(email="new@acme.test", password_hash="x", organization_id=self.org.id, role="EMPLOYEE")
        self.db.add_all([self.admin, self.employee])
        self.db.flush()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_onboarding_task_requires_real_assignment_before_completion(self):
        department = Department(organization_id=self.org.id, name="Developers")
        self.db.add(department)
        self.db.flush()
        task_spec = OnboardingTaskRequest(task_type="MANUAL_ACCESS", title="Verify HR access")
        lifecycle = start_onboarding(self.db, self.admin, self.employee.id, department.id, date.today(), [task_spec])
        self.db.commit()
        task = self.db.query(LifecycleTask).filter(LifecycleTask.lifecycle_id == lifecycle.id).one()
        with self.assertRaises(ValueError):
            complete_task(self.db, self.admin, task, None)
        complete_task(self.db, self.admin, task, "HR verified access in the identity provider")
        self.db.commit()
        self.assertEqual(task.status, "COMPLETED")
        self.assertEqual(self.db.get(EmployeeLifecycle, lifecycle.id).status, "ACTIVE")

    def test_lifecycle_keeps_department_membership_in_sync(self):
        department = Department(organization_id=self.org.id, name="Developers")
        self.db.add(department)
        self.db.flush()

        lifecycle = start_onboarding(self.db, self.admin, self.employee.id, department.id, date.today(), [])
        self.db.commit()
        membership = self.db.query(DepartmentMembership).filter(DepartmentMembership.user_id == self.employee.id, DepartmentMembership.is_active.is_(True)).one()
        self.assertEqual(membership.department_id, department.id)

        start_offboarding(self.db, self.admin, lifecycle, date.today())
        self.db.commit()
        self.assertFalse(self.db.query(DepartmentMembership).filter(DepartmentMembership.user_id == self.employee.id, DepartmentMembership.is_active.is_(True)).first())

    def test_offboarding_requires_release_and_return_before_clearance(self):
        subscription = Subscription(organization_id=self.org.id, user_id=self.admin.id, provider="Test", name="Test", billing_interval="monthly")
        license_item = SubscriptionLicense(organization_id=self.org.id, subscription_id=1, capacity=1)
        asset = Asset(organization_id=self.org.id, asset_tag="LT-001", asset_type="Laptop", name="Laptop")
        self.db.add(subscription)
        self.db.flush()
        license_item.subscription_id = subscription.id
        self.db.add_all([license_item, asset])
        self.db.flush()
        assign_license(self.db, self.admin, subscription, license_item, {"user_id": self.employee.id, "notes": None})
        asset_assignment = assign_asset(self.db, self.admin, asset, self.employee.id)
        lifecycle = EmployeeLifecycle(organization_id=self.org.id, user_id=self.employee.id, status="ACTIVE", joined_at=date.today())
        self.db.add(lifecycle)
        self.db.flush()
        start_offboarding(self.db, self.admin, lifecycle, date.today())
        self.db.commit()
        tasks = self.db.query(LifecycleTask).filter(LifecycleTask.lifecycle_id == lifecycle.id).all()
        self.assertEqual({task.task_type for task in tasks}, {"REVOKE_SUBSCRIPTION", "RECOVER_ASSET"})
        for task in tasks:
            with self.assertRaises(ValueError):
                complete_task(self.db, self.admin, task, None)
        release_license(self.db, self.admin, self.db.query(SubscriptionAssignment).first())
        return_asset(self.db, self.admin, asset_assignment, "Good", "Returned")
        for task in tasks:
            complete_task(self.db, self.admin, task, None)
        self.db.commit()
        self.assertEqual(self.db.get(EmployeeLifecycle, lifecycle.id).status, "COMPLETED")


if __name__ == "__main__":
    unittest.main()

