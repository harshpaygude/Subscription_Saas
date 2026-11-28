import sys
import unittest
from decimal import Decimal
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from unisora_kit import OutboxDispatcher, RequestContext
from app.application.license_service import LicenseAssignmentService
from app.domain.entities import SubscriptionEntity, SubscriptionLicenseEntity, normalize_monthly
from app.infrastructure.adapters import OutboxAuditAdapter
from app.infrastructure.db import Base
from app.infrastructure.repositories import (
    SqlAlchemyAssignmentRepository,
    SqlAlchemyLicenseRepository,
    SqlAlchemySubscriptionRepository,
)


class _FakeIdentityLookup:
    def __init__(self, valid_ids: set[int]):
        self.valid_ids = valid_ids

    def user_exists_in_org(self, ctx, user_id):
        return user_id in self.valid_ids


class SubscriptionServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.dispatcher = OutboxDispatcher(source_service="subscription-service", internal_secret="test-secret")

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_supported_intervals_use_decimal_arithmetic(self):
        self.assertEqual(normalize_monthly(Decimal("120.00"), "monthly"), Decimal("120.000000"))
        self.assertEqual(normalize_monthly(Decimal("1200.00"), "annual"), Decimal("100.000000"))
        self.assertEqual(normalize_monthly(Decimal("300.00"), "quarterly"), Decimal("100.000000"))
        self.assertEqual(normalize_monthly(Decimal("12.00"), "weekly"), Decimal("52.000000"))

    def test_unknown_interval_or_amount_is_unavailable(self):
        self.assertIsNone(normalize_monthly(None, "monthly"))
        self.assertIsNone(normalize_monthly(Decimal("50.00"), "one_time"))

    def test_license_capacity_is_enforced(self):
        from datetime import datetime
        sub_repo = SqlAlchemySubscriptionRepository(self.db)
        lic_repo = SqlAlchemyLicenseRepository(self.db)
        assign_repo = SqlAlchemyAssignmentRepository(self.db)
        now = datetime.utcnow()

        sub = sub_repo.create(
            SubscriptionEntity(
                id=None, organization_id=1, user_id=1, provider="Test", name="Test", plan=None,
                amount=None, currency="USD", billing_interval="monthly", start_date=None,
                next_renewal_date=None, status="ACTIVE", cancellation_date=None, source="manual",
                note=None, renewal_type="AUTOPAY", created_at=now, updated_at=now,
            )
        )
        lic = lic_repo.create(
            SubscriptionLicenseEntity(
                id=None, organization_id=1, subscription_id=sub.id, reference="Seat",
                capacity=1, status="ACTIVE", created_at=now, updated_at=now,
            )
        )
        svc = LicenseAssignmentService(
            subscriptions=sub_repo,
            licenses=lic_repo,
            assignments=assign_repo,
            identity_lookup=_FakeIdentityLookup({1, 2}),
            audit=OutboxAuditAdapter(self.db, self.dispatcher),
        )
        ctx = RequestContext(user_id=1, organization_id=1, role="OWNER")
        first = svc.assign_license(ctx=ctx, subscription_id=sub.id, license_id=lic.id, user_id=2)
        self.db.commit()
        self.assertIsNotNone(first.id)
        with self.assertRaises(Exception):
            svc.assign_license(ctx=ctx, subscription_id=sub.id, license_id=lic.id, user_id=1)


if __name__ == "__main__":
    unittest.main()
