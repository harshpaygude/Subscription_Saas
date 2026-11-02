import io
import unittest
from datetime import datetime

from fastapi.testclient import TestClient
import openpyxl
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user
from app.database.models import Department, Organization, User
from app.database.session import Base, get_db
from app.main import app


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        # Create test organization
        self.org = Organization(name="UniSora Org", created_at=datetime.utcnow())
        self.other_org = Organization(name="Other Org", created_at=datetime.utcnow())
        self.db.add_all([self.org, self.other_org])
        self.db.flush()

        # Owner / Admin user
        self.owner = User(
            email="owner@unisora.test",
            display_name="UniSora Admin",
            password_hash="test-hash",
            organization_id=self.org.id,
            role="OWNER",
            created_at=datetime.utcnow(),
        )
        # Member (non-admin)
        self.member = User(
            email="member@unisora.test",
            display_name="Regular Member",
            password_hash="test-hash",
            organization_id=self.org.id,
            role="MEMBER",
            created_at=datetime.utcnow(),
        )
        self.db.add_all([self.owner, self.member])
        self.db.commit()

        self.current_user = self.owner

        def db_override():
            try:
                yield self.db
            finally:
                pass

        def user_override():
            return self.current_user

        app.dependency_overrides[get_db] = db_override
        app.dependency_overrides[get_current_user] = user_override
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()
        self.db.close()
        self.engine.dispose()

    def test_onboarding_status_initial_state(self):
        res = self.client.get("/organizations/me/onboarding-status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["onboarding_completed"])
        self.assertIsNone(data["onboarding_completed_at"])

    def test_profile_update(self):
        payload = {
            "legal_name": "UniSora Global Corp",
            "industry": "Technology & Software",
            "company_size": "51–200 employees",
            "country": "United States",
            "city": "San Francisco",
        }
        res = self.client.patch("/organizations/me/profile", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["legal_name"], "UniSora Global Corp")
        self.assertEqual(data["industry"], "Technology & Software")
        self.assertEqual(data["city"], "San Francisco")

    def test_onboarding_submission_marks_completed_and_creates_departments(self):
        payload = {
            "company": {
                "legal_name": "Enterprise Inc",
                "display_name": "Enterprise",
                "industry": "Financial Services & Banking",
                "company_size": "201–500 employees",
                "country": "United Kingdom",
                "company_email": "ops@enterprise.test",
                "company_phone": "+44 20 7946 0912",
            },
            "departments": [
                {"name": "Engineering", "description": "Core platform engineering"},
                {"name": "Finance & Accounting", "description": "Financial planning"},
            ],
        }
        res = self.client.post("/organizations/me/onboarding", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["onboarding_completed"])
        self.assertIsNotNone(data["onboarding_completed_at"])
        self.assertEqual(data["legal_name"], "Enterprise Inc")

        # Verify departments exist in database
        depts = (
            self.db.query(Department)
            .filter(Department.organization_id == self.org.id)
            .all()
        )
        dept_names = {d.name for d in depts}
        self.assertIn("Engineering", dept_names)
        self.assertIn("Finance & Accounting", dept_names)

        # Verify status endpoint reflects completion
        status_res = self.client.get("/organizations/me/onboarding-status")
        self.assertEqual(status_res.status_code, 200)
        self.assertTrue(status_res.json()["onboarding_completed"])

    def test_non_admin_cannot_submit_onboarding(self):
        self.current_user = self.member
        payload = {
            "company": {"legal_name": "Hacker Corp"},
            "departments": [],
        }
        res = self.client.post("/organizations/me/onboarding", json=payload)
        self.assertEqual(res.status_code, 403)

    def test_excel_template_download(self):
        res = self.client.get("/organizations/me/onboarding/excel-template")
        self.assertEqual(res.status_code, 200)
        self.assertIn("spreadsheetml", res.headers.get("content-type", ""))
        # Verify content can be read by openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(res.content))
        self.assertIn("Company", wb.sheetnames)
        self.assertIn("Departments", wb.sheetnames)
        self.assertIn("Employees", wb.sheetnames)
        self.assertIn("Assets", wb.sheetnames)

    def test_excel_parse_valid_workbook(self):
        # Create a valid workbook in memory
        wb = openpyxl.Workbook()
        ws_company = wb.active
        ws_company.title = "Company"
        ws_company.append(["company_name", "legal_name", "industry", "company_size", "country"])
        ws_company.append(["Alpha Tech", "Alpha Technologies Ltd", "IT", "11–50 employees", "Canada"])

        ws_dept = wb.create_sheet("Departments")
        ws_dept.append(["department_name", "description"])
        ws_dept.append(["Sales", "Direct sales"])
        ws_dept.append(["Marketing", "Growth"])

        ws_emp = wb.create_sheet("Employees")
        ws_emp.append(["employee_id", "full_name", "email", "department_name", "phone_number"])
        ws_emp.append(["EMP-101", "Alex Smith", "alex@alpha.test", "Sales", "+1234567890"])

        ws_asset = wb.create_sheet("Assets")
        ws_asset.append(["asset_tag", "name", "asset_type", "assigned_to", "purchase_cost"])
        ws_asset.append(["AST-001", "MacBook Pro 16", "Laptop", "alex@alpha.test", "2999.00"])

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        files = {"file": ("test.xlsx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        res = self.client.post("/organizations/me/onboarding/parse-excel", files=files)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["valid"])
        self.assertEqual(data["company"]["company_name"], "Alpha Tech")
        self.assertEqual(data["company"]["country"], "Canada")
        self.assertEqual(data["department_count"], 2)
        self.assertEqual(data["employee_count"], 1)
        self.assertEqual(data["asset_count"], 1)
        self.assertEqual(data["assets"][0]["asset_tag"], "AST-001")
        self.assertEqual(data["assets"][0]["assigned_to"], "alex@alpha.test")
        self.assertEqual(len(data["errors"]), 0)

    def test_onboarding_submission_creates_employees_and_assets(self):
        from app.database.models import Asset, AssetAssignment, EmployeeLifecycle
        payload = {
            "company": {
                "legal_name": "Tech Corp",
                "display_name": "Tech",
                "industry": "Technology & Software",
                "company_size": "11–50 employees",
                "country": "United States",
            },
            "departments": [
                {"name": "Engineering", "description": "Core dev"},
            ],
            "employees": [
                {
                    "employee_id": "EMP-999",
                    "full_name": "John Doe",
                    "email": "johndoe@techcorp.test",
                    "department_name": "Engineering",
                }
            ],
            "assets": [
                {
                    "asset_tag": "AST-LAP-999",
                    "name": "ThinkPad T14",
                    "asset_type": "Laptop",
                    "assigned_to": "johndoe@techcorp.test",
                    "purchase_cost": "1499.00",
                }
            ],
        }
        res = self.client.post("/organizations/me/onboarding", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["onboarding_completed"])

        # Check user created
        emp_user = self.db.query(User).filter(User.email == "johndoe@techcorp.test").first()
        self.assertIsNotNone(emp_user)
        self.assertEqual(emp_user.employee_id, "EMP-999")

        # Check lifecycle created
        lifecycle = self.db.query(EmployeeLifecycle).filter(EmployeeLifecycle.user_id == emp_user.id).first()
        self.assertIsNotNone(lifecycle)
        self.assertEqual(lifecycle.status, "ACTIVE")

        # Check asset created and assigned
        asset = self.db.query(Asset).filter(Asset.asset_tag == "AST-LAP-999").first()
        self.assertIsNotNone(asset)
        self.assertEqual(asset.status, "ASSIGNED")
        self.assertEqual(asset.name, "ThinkPad T14")

        # Check assignment record
        assignment = self.db.query(AssetAssignment).filter(AssetAssignment.asset_id == asset.id).first()
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.user_id, emp_user.id)
        self.assertEqual(assignment.status, "ACTIVE")

    def test_excel_parse_rejects_non_xlsx(self):
        files = {"file": ("test.txt", b"plain text", "text/plain")}
        res = self.client.post("/organizations/me/onboarding/parse-excel", files=files)
        self.assertEqual(res.status_code, 400)


if __name__ == "__main__":
    unittest.main()
