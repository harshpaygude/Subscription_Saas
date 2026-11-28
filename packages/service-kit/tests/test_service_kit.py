import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from unisora_kit import (
    OutboxDispatcher,
    OutboxRecordMixin,
    create_internal_service_token,
    make_domain_event,
    verify_internal_service_token,
)


class _Base(DeclarativeBase):
    pass


class _OutboxRow(_Base, OutboxRecordMixin):
    __tablename__ = "outbox_events"


class ServiceKitTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        _Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_internal_service_token_round_trip(self):
        token = create_internal_service_token("super-secret", "api-gateway", user_id=7, organization_id=3, role="OWNER")
        self.assertTrue(verify_internal_service_token(token, "super-secret", user_id=7, organization_id=3, role="OWNER"))
        self.assertFalse(verify_internal_service_token(token, "wrong-secret", user_id=7, organization_id=3, role="OWNER"))
        self.assertFalse(verify_internal_service_token(token, "super-secret", user_id=8, organization_id=3, role="OWNER"))

    def test_outbox_delivery_retries_and_dead_letter(self):
        attempts = {"count": 0}

        def failing_transport(_url, _body, _headers):
            attempts["count"] += 1
            return 503

        dispatcher = OutboxDispatcher(
            source_service="identity-service",
            internal_secret="secret",
            max_attempts=2,
            transport=failing_transport,
        )
        ev = make_domain_event(event_type="audit.recorded", source_service="identity-service", payload={"x": 1})
        dispatcher.enqueue(self.db, _OutboxRow, event=ev, target_url="http://governance/internal/events")
        self.db.commit()

        self.assertEqual(dispatcher.flush_pending(self.db, _OutboxRow), 0)
        row = self.db.query(_OutboxRow).one()
        self.assertEqual(row.status, "PENDING")
        self.assertEqual(row.attempts, 1)

        self.assertEqual(dispatcher.flush_pending(self.db, _OutboxRow), 0)
        row = self.db.query(_OutboxRow).one()
        self.assertEqual(row.status, "DEAD_LETTER")
        self.assertEqual(row.attempts, 2)
        self.assertEqual(attempts["count"], 2)


if __name__ == "__main__":
    unittest.main()
