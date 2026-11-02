import re
from types import SimpleNamespace
from unittest.mock import Mock, patch

import unittest

from app.integrations.aws.client import AWSIntegrationError, assume_connection_role
from app.integrations.aws.routes import _get_connection
from app.integrations.registry import ProviderRegistry
from app.integrations.aws.provider import AWSProvider
from app.database.models import Connection, Organization, User
from app.database.session import Base
from app.integrations.services import ConnectionService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException


class AWSIntegrationTests(unittest.TestCase):
  def test_external_ids_are_urlsafe_and_sufficiently_random(self):
    import secrets

    values = {secrets.token_urlsafe(32) for _ in range(100)}
    self.assertEqual(len(values), 100)
    self.assertTrue(all(re.fullmatch(r"[A-Za-z0-9_-]+", value) for value in values))

  def test_role_assumption_rejects_account_mismatch_before_aws_call(self):
    with self.assertRaisesRegex(AWSIntegrationError, "does not match"):
        assume_connection_role(
            "arn:aws:iam::111111111111:role/UniSoraReadOnly",
            "external-id",
            "222222222222",
        )


  def test_role_assumption_uses_backend_identity_and_customer_session(self):
    fake_session = Mock()
    fake_session.client.return_value.get_caller_identity.return_value = {
        "Account": "111111111111",
        "Arn": "arn:aws:sts::111111111111:assumed-role/customer/session",
    }
    identity = Mock()
    identity.assume_customer_role.return_value = {
        "session": fake_session,
        "identity": fake_session.client.return_value.get_caller_identity.return_value,
        "expiration": "later",
    }

    with patch("app.integrations.aws.client.AWSBackendIdentity", return_value=identity):
        result = assume_connection_role(
            "arn:aws:iam::111111111111:role/UniSoraReadOnly",
            "external-id",
            "111111111111",
        )

    identity.assume_customer_role.assert_called_once()
    self.assertIs(result["session"], fake_session)

  def test_provider_registry_is_metadata_driven(self):
    registry = ProviderRegistry([AWSProvider()])
    self.assertEqual(registry.get("aws").metadata.display_name, "Amazon Web Services")
    self.assertEqual(registry.list_metadata()[0].capabilities, [
        "connection_setup", "costs", "account_plan"
    ])

  def test_connection_lookup_is_organization_scoped(self):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    first_org = Organization(name="first")
    second_org = Organization(name="second")
    session.add_all([first_org, second_org])
    session.flush()
    user = User(email="owner@example.com", password_hash="hash", organization_id=first_org.id)
    session.add(user)
    connection = Connection(organization_id=second_org.id, provider="AWS", provider_tenant_id="111111111111")
    session.add(connection)
    session.commit()

    with self.assertRaises(HTTPException) as error:
        ConnectionService(session).get_for_organization(connection.id, user, provider="AWS")
    self.assertEqual(error.exception.status_code, 404)
    session.close()
