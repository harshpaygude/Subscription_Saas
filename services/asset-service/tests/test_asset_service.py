import io
import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

import openpyxl
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from unisora_kit import OutboxDispatcher, RequestContext
from app.application.asset_bulk_import import (
    generate_sample_asset_csv,
    generate_sample_asset_excel,
    process_asset_bulk_import,
)
from app.application.asset_service import AssetService
from app.infrastructure.adapters import OutboxAuditAdapter
from app.infrastructure.db import Base
from app.infrastructure.repositories import (
    SqlAlchemyAssetAssignmentRepository,
    SqlAlchemyAssetMaintenanceRepository,
    SqlAlchemyAssetRepository,
)


class _FakeIdentityLookup:
    def __init__(self):
        self.users = [{"id": 2, "email": "alex.rivera@acme.test", "display_name": "Alex Rivera", "employee_id": "EMP101"}]

    def user_exists_in_org(self, ctx, user_id):
        return any(u["id"] == user_id for u in self.users)

    def list_org_users(self, ctx):
        return self.users

    def provision_user(self, ctx, *, email, display_name, employee_id):
        new_id = len(self.users) + 10
        u = {"id": new_id, "email": email, "display_name": display_name, "employee_id": employee_id}
        self.users.append(u)
        return u


class AssetServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.dispatcher = OutboxDispatcher(source_service="asset-service", internal_secret="test-secret")
        self.identity = _FakeIdentityLookup()
        self.ctx = RequestContext(user_id=1, organization_id=1, role="OWNER")
        self.assets_repo = SqlAlchemyAssetRepository(self.db)
        self.assign_repo = SqlAlchemyAssetAssignmentRepository(self.db)
        self.svc = AssetService(
            assets=self.assets_repo,
            assignments=self.assign_repo,
            maintenance=SqlAlchemyAssetMaintenanceRepository(self.db),
            identity_lookup=self.identity,
            audit=OutboxAuditAdapter(self.db, self.dispatcher),
        )

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_asset_assignment_preserves_history_on_return(self):
        asset = self.svc.create_asset(organization_id=1, actor_id=1, data={"asset_tag": "LT-001", "asset_type": "Laptop", "name": "Laptop"})
        assignment = self.svc.assign_asset(ctx=self.ctx, asset_id=asset.id, user_id=2)
        self.db.commit()
        returned = self.svc.return_asset(ctx=self.ctx, assignment_id=assignment.id, condition_at_return="Good", handover_notes="Returned")
        self.db.commit()
        self.assertEqual(returned.status, "RETURNED")
        self.assertEqual(self.assets_repo.get_by_id(asset.id, 1).status, "AVAILABLE")
        self.assertEqual(len(self.assign_repo.list_by_asset(asset.id, 1)), 1)

    def test_import_csv_with_one_to_many_assets_for_employee(self):
        csv_content = (
            "Asset Tag,Asset Name,Asset Type,Manufacturer,Model,Serial Number,Purchase Cost,Currency,Location,Status,Assigned Employee Email,Assigned Employee Name,Employee ID,Handover Notes\n"
            "LT-901,MacBook Pro 16,Laptop,Apple,A2991,SN-1,3499.00,USD,SF HQ,Assigned,alex.rivera@acme.test,Alex Rivera,EMP101,Laptop\n"
            "HD-901,Jabra Evolve2 65,Headset,Jabra,Evolve2-65,SN-2,249.00,USD,SF HQ,Assigned,alex.rivera@acme.test,Alex Rivera,EMP101,Headset\n"
            "MN-901,Dell UltraSharp 27,Monitor,Dell,U2723QE,SN-3,579.00,USD,SF HQ,Assigned,alex.rivera@acme.test,Alex Rivera,EMP101,Monitor\n"
        ).encode("utf-8")
        result = process_asset_bulk_import(
            content=csv_content,
            filename="assets.csv",
            ctx=self.ctx,
            assets=self.assets_repo,
            assignments=self.assign_repo,
            identity_lookup=self.identity,
            audit=OutboxAuditAdapter(self.db, self.dispatcher),
        )
        self.db.commit()
        self.assertTrue(result["success"])
        self.assertEqual(result["created_assets"], 3)
        self.assertEqual(result["assigned_assets"], 3)
        self.assertEqual(len(self.assign_repo.list_filtered(1, user_id=2, status="ACTIVE")), 3)

    def test_import_wide_columns_multi_asset_row(self):
        csv_content = (
            "employee_id,full_name,email,laptop_tag,laptop_name,headset_tag,headset_name,monitor_tag,monitor_name\n"
            "EMP999,Sarah Connor,sarah.connor@acme.test,LT-800,ThinkPad X1,HD-800,Sony XM5,MN-800,Apple Display\n"
        ).encode("utf-8")
        result = process_asset_bulk_import(
            content=csv_content,
            filename="wide.csv",
            ctx=self.ctx,
            assets=self.assets_repo,
            assignments=self.assign_repo,
            identity_lookup=self.identity,
            audit=OutboxAuditAdapter(self.db, self.dispatcher),
        )
        self.assertEqual(result["created_assets"], 3)
        self.assertEqual(result["assigned_assets"], 3)

    def test_sample_template_generation(self):
        self.assertIn("LT-101", generate_sample_asset_csv())
        wb = openpyxl.load_workbook(io.BytesIO(generate_sample_asset_excel()))
        self.assertIn("IT Assets", wb.sheetnames)
        self.assertIn("Multi-Device Roster", wb.sheetnames)


if __name__ == "__main__":
    unittest.main()
