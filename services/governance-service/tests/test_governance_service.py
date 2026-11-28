import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from unisora_kit import RequestContext, create_internal_service_token
from app.api.routes import get_alert_service, get_analytics_service, get_current_context
from app.application.governance_service import AlertService, AnalyticsService
from app.config import settings
from app.infrastructure.adapters import SqlAlchemyAlertRepository, SqlAlchemyAuditRepository
from app.infrastructure.db import Base, get_db
from app.infrastructure.models import AuditLog
from app.main import app


class _FakeSubReadPort:
    def __init__(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        self.subs = [
            {
                "id": 101, "provider": "github", "name": "GitHub Enterprise", "plan": "Enterprise",
                "amount": "1200.00", "currency": "USD", "billing_interval": "annual",
                "next_renewal_date": tomorrow, "status": "ACTIVE", "renewal_type": "AUTOPAY", "note": None,
            }
        ]

    def list_subscriptions(self, ctx):
        return self.subs

    def list_active_assignments(self, ctx):
        return [{"id": 1}, {"id": 2}]


class _FakeAssetReadPort:
    def get_summary(self, ctx):
        return {"total": 5, "assigned": 3, "available": 2}


class _FakeIdentityReadPort:
    def get_organization(self, ctx, org_id):
        return {"id": org_id, "name": "Acme Corp"}

    def list_users(self, ctx):
        return [{"id": 1, "email": "admin@acme.test"}]

    def list_departments(self, ctx):
        return [{"id": 1, "name": "Engineering", "is_active": True}]


class GovernanceServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.ctx = RequestContext(user_id=1, organization_id=1, role="OWNER")
        self.subs = _FakeSubReadPort()

        app.dependency_overrides[get_db] = lambda: (yield self.db)
        app.dependency_overrides[get_current_context] = lambda: self.ctx
        app.dependency_overrides[get_alert_service] = lambda: AlertService(SqlAlchemyAlertRepository(self.db), self.subs)
        app.dependency_overrides[get_analytics_service] = lambda: AnalyticsService(
            self.subs, _FakeAssetReadPort(), _FakeIdentityReadPort(), SqlAlchemyAuditRepository(self.db)
        )
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()
        self.db.close()
        self.engine.dispose()

    def test_renewal_alert_evaluation_and_dedupe(self):
        res = self.client.get("/alerts")
        self.assertEqual(res.status_code, 200)
        alerts = res.json()
        self.assertEqual(len(alerts), 1)
        self.assertIn("URGENT: GitHub Enterprise", alerts[0]["title"])
        # Second call does not duplicate alert
        res2 = self.client.get("/alerts")
        self.assertEqual(len(res2.json()), 1)

    def test_analytics_summary_and_audit_export_fix(self):
        summary = self.client.get("/analytics/summary").json()
        self.assertEqual(summary["active_subscriptions"], 1)
        self.assertEqual(summary["totals_by_currency"]["USD"], "100.000000")
        self.assertEqual(summary["license_utilization"], 2)
        self.assertEqual(summary["assets"]["assigned"], 3)

        export = self.client.get("/analytics/audit-export?range_type=monthly")
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export.json()["subscriptions"][0]["renewal_date"], self.subs.subs[0]["next_renewal_date"])

    def test_idempotent_event_ingestion_and_auth(self):
        payload = {
            "event_id": "evt-unique-1",
            "event_type": "audit.recorded",
            "event_version": "1.0",
            "source_service": "identity-service",
            "occurred_at": "2026-11-28T00:00:00Z",
            "payload": {"organization_id": 1, "actor_id": 1, "action": "user.created", "entity_type": "user", "entity_id": 42},
        }
        # Reject unsigned request
        unauth = self.client.post("/internal/events", json=payload)
        self.assertEqual(unauth.status_code, 401)

        token = create_internal_service_token(settings.internal_service_secret, "identity-service")
        r1 = self.client.post("/internal/events", json=payload, headers={"X-Internal-Service-Token": token})
        self.assertEqual(r1.status_code, 200)
        self.assertFalse(r1.json()["deduplicated"])

        r2 = self.client.post("/internal/events", json=payload, headers={"X-Internal-Service-Token": token})
        self.assertEqual(r2.status_code, 200)
        self.assertTrue(r2.json()["deduplicated"])
        self.assertEqual(self.db.query(AuditLog).count(), 1)


if __name__ == "__main__":
    unittest.main()
