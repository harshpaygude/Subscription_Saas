import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.assets.service import assign_asset, return_asset
from app.database.models import Asset, Department, Organization, Subscription, SubscriptionLicense, User
from app.database.session import Base
from app.departments.service import add_membership
from app.license_assignments.service import assign_license


class ResourceManagementTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        org = Organization(name="Acme")
        other_org = Organization(name="Other")
        self.db.add_all([org, other_org])
        self.db.flush()
        self.org = org
        self.other_org = other_org
        self.owner = User(email="owner@acme.test", password_hash="x", organization_id=org.id, role="OWNER")
        self.employee = User(email="employee@acme.test", password_hash="x", organization_id=org.id, role="EMPLOYEE")
        self.other_employee = User(email="employee@other.test", password_hash="x", organization_id=other_org.id, role="EMPLOYEE")
        self.db.add_all([self.owner, self.employee, self.other_employee])
        self.db.flush()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_membership_rejects_cross_organization_user(self):
        department = Department(organization_id=self.org.id, name="Developers")
        self.db.add(department)
        self.db.flush()
        with self.assertRaises(ValueError):
            add_membership(self.db, self.owner, department, self.other_employee.id, __import__("datetime").date.today())

    def test_asset_assignment_preserves_history_on_return(self):
        asset = Asset(organization_id=self.org.id, asset_tag="LT-001", asset_type="Laptop", name="Laptop")
        self.db.add(asset)
        self.db.flush()
        assignment = assign_asset(self.db, self.owner, asset, self.employee.id)
        self.db.commit()
        returned = return_asset(self.db, self.owner, assignment, "Good", "Returned during offboarding")
        self.db.commit()
        self.assertEqual(returned.status, "RETURNED")
        self.assertEqual(asset.status, "AVAILABLE")
        self.assertEqual(self.db.query(type(assignment)).count(), 1)

    def test_license_capacity_is_enforced(self):
        subscription = Subscription(organization_id=self.org.id, user_id=self.owner.id, provider="Test", name="Test", billing_interval="monthly")
        self.db.add(subscription)
        self.db.flush()
        license_item = SubscriptionLicense(organization_id=self.org.id, subscription_id=subscription.id, capacity=1)
        self.db.add(license_item)
        self.db.flush()
        first = assign_license(self.db, self.owner, subscription, license_item, {"user_id": self.employee.id, "notes": None})
        self.db.commit()
        self.assertIsNotNone(first.id)
        with self.assertRaises(ValueError):
            assign_license(self.db, self.owner, subscription, license_item, {"user_id": self.owner.id, "notes": None})


if __name__ == "__main__":
    unittest.main()

