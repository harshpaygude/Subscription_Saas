import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import Connection, Organization, User
from app.database.session import Base


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_connection_survives_a_new_session_and_isolation_is_scoped(self):
        organization = Organization(name="Acme", created_at=datetime.utcnow())
        other_organization = Organization(name="Other", created_at=datetime.utcnow())
        self.db.add_all([organization, other_organization])
        self.db.flush()
        user = User(
            email="owner@example.com",
            display_name="Owner",
            password_hash="not-used-in-this-test",
            organization_id=organization.id,
            role="OWNER",
            created_at=datetime.utcnow(),
        )
        other_user = User(
            email="other@example.com",
            display_name="Other",
            password_hash="not-used-in-this-test",
            organization_id=other_organization.id,
            role="OWNER",
            created_at=datetime.utcnow(),
        )
        self.db.add_all([user, other_user])
        self.db.flush()
        self.db.add(Connection(
            user_id=user.id,
            organization_id=organization.id,
            provider="OPENAI",
            credentials_encrypted="encrypted-value",
            status="ACTIVE",
        ))
        self.db.commit()
        user_id = user.id
        organization_id = organization.id
        other_user_id = other_user.id
        other_organization_id = other_organization.id

        self.db.close()
        self.db = self.Session()
        saved = self.db.query(Connection).filter(
            Connection.user_id == user_id,
            Connection.organization_id == organization_id,
            Connection.provider == "OPENAI",
        ).one()
        hidden = self.db.query(Connection).filter(
            Connection.user_id == other_user_id,
            Connection.organization_id == other_organization_id,
            Connection.provider == "OPENAI",
        ).all()

        self.assertEqual(saved.status, "ACTIVE")
        self.assertEqual(saved.credentials_encrypted, "encrypted-value")
        self.assertEqual(hidden, [])

    def test_failed_transaction_rolls_back_without_erasing_saved_connection(self):
        organization = Organization(name="Acme", created_at=datetime.utcnow())
        self.db.add(organization)
        self.db.flush()
        self.db.add(Connection(
            organization_id=organization.id,
            provider="AWS",
            provider_tenant_id="123456789012",
            status="ACTIVE",
        ))
        self.db.commit()

        self.db.add(Organization(name=None))
        with self.assertRaises(Exception):
            self.db.commit()
        self.db.rollback()

        saved = self.db.query(Connection).filter(Connection.provider == "AWS").one()
        self.assertEqual(saved.provider_tenant_id, "123456789012")


if __name__ == "__main__":
    unittest.main()
