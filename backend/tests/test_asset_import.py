import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.assets.csv_import import (
    generate_sample_asset_csv,
    generate_sample_asset_excel,
    process_asset_bulk_import,
)
from app.database.models import Asset, AssetAssignment, Organization, User
from app.database.session import Base


class AssetImportTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()

        self.org = Organization(name="Test Org")
        self.db.add(self.org)
        self.db.flush()

        self.admin = User(
            email="admin@test.com",
            display_name="Admin User",
            password_hash="hash",
            organization_id=self.org.id,
            role="OWNER",
        )
        self.db.add(self.admin)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_import_csv_with_one_to_many_assets_for_employee(self):
        """
        Tests that an employee (Alex) can receive multiple assets (Laptop, Headset, Monitor).
        """
        csv_data = (
            "Asset Tag,Asset Name,Asset Type,Manufacturer,Model,Serial Number,Purchase Cost,Assigned To\n"
            "LT-101,MacBook Pro 16,Laptop,Apple,M3 Max,SN-APL-01,3499.00,alex.rivera@test.com\n"
            "HD-101,Jabra Evolve2 65,Headset,Jabra,Evolve2,SN-JBR-02,249.00,alex.rivera@test.com\n"
            "MN-101,Dell UltraSharp 27,Monitor,Dell,U2723QE,SN-DLL-03,579.00,alex.rivera@test.com\n"
            "LT-102,Lenovo ThinkPad X1,Laptop,Lenovo,Gen 11,SN-LNV-04,1899.00,sophia.chen@test.com\n"
            "LT-103,Spare Dell Latitude,Laptop,Dell,5540,SN-DLL-05,1299.00,\n"
        ).encode("utf-8")

        result = process_asset_bulk_import(csv_data, "assets.csv", self.db, self.admin)

        self.assertTrue(result["success"])
        self.assertEqual(result["created_assets"], 5)
        self.assertEqual(result["assigned_assets"], 4)
        self.assertEqual(result["employees_matched"], 2)

        # Verify Alex Rivera has 3 distinct active asset assignments (1-to-many)
        alex = self.db.query(User).filter(User.email == "alex.rivera@test.com").first()
        self.assertIsNotNone(alex)

        alex_assignments = (
            self.db.query(AssetAssignment)
            .filter(AssetAssignment.user_id == alex.id, AssetAssignment.status == "ACTIVE")
            .all()
        )
        self.assertEqual(len(alex_assignments), 3)

        assigned_tags = {
            self.db.query(Asset).filter(Asset.id == a.asset_id).first().asset_tag
            for a in alex_assignments
        }
        self.assertEqual(assigned_tags, {"LT-101", "HD-101", "MN-101"})

        # Verify unassigned asset
        spare = self.db.query(Asset).filter(Asset.asset_tag == "LT-103").first()
        self.assertIsNotNone(spare)
        self.assertEqual(spare.status, "AVAILABLE")

    def test_import_wide_columns_multi_asset_row(self):
        """
        Tests wide rows where Laptop, Headset, and Monitor columns are on the same row.
        """
        csv_data = (
            "employee_id,full_name,email,laptop_tag,laptop_name,laptop_serial,headset_tag,headset_name,headset_serial,monitor_tag,monitor_name,monitor_serial\n"
            "EMP-201,Jordan Lee,jordan@test.com,LT-201,MacBook Air 15,SN-AIR-01,HD-201,Sony WH-1000XM5,SN-SNY-01,MN-201,Apple Studio Display,SN-APL-DISP\n"
        ).encode("utf-8")

        result = process_asset_bulk_import(csv_data, "wide_roster.csv", self.db, self.admin)

        self.assertTrue(result["success"])
        self.assertEqual(result["created_assets"], 3)
        self.assertEqual(result["assigned_assets"], 3)

        jordan = self.db.query(User).filter(User.email == "jordan@test.com").first()
        self.assertIsNotNone(jordan)

        jordan_assignments = (
            self.db.query(AssetAssignment)
            .filter(AssetAssignment.user_id == jordan.id, AssetAssignment.status == "ACTIVE")
            .all()
        )
        self.assertEqual(len(jordan_assignments), 3)

    def test_sample_template_generation(self):
        """
        Tests that CSV and Excel sample template generators work without errors.
        """
        csv_sample = generate_sample_asset_csv()
        self.assertIn("LT-101", csv_sample)
        self.assertIn("Jabra Evolve2 65", csv_sample)
        self.assertIn("alex.rivera@acme.com", csv_sample)

        excel_sample = generate_sample_asset_excel()
        self.assertTrue(len(excel_sample) > 1000)

        # Test importing the generated Excel sample
        excel_result = process_asset_bulk_import(excel_sample, "sample.xlsx", self.db, self.admin)
        self.assertTrue(excel_result["success"])
        self.assertGreater(excel_result["created_assets"], 5)
        self.assertGreater(excel_result["assigned_assets"], 3)



if __name__ == "__main__":
    unittest.main()
