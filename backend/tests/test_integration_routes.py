import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user
from app.database.models import AzureConnection, Connection, Organization, User
from app.database.session import Base, get_db
from app.integrations.aws import routes as aws_routes
from app.integrations.aws.client import AWSIntegrationError
from app.integrations.credentials import encrypt_credentials
from app.main import app


class IntegrationRouteTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        organization = Organization(name="Acme", created_at=datetime.utcnow())
        other_organization = Organization(name="Other", created_at=datetime.utcnow())
        self.db.add_all([organization, other_organization])
        self.db.flush()
        self.user = User(
            email="owner@example.com",
            display_name="Owner",
            password_hash="not-used-in-this-test",
            organization_id=organization.id,
            role="OWNER",
            created_at=datetime.utcnow(),
        )
        self.other_user = User(
            email="other@example.com",
            display_name="Other",
            password_hash="not-used-in-this-test",
            organization_id=other_organization.id,
            role="OWNER",
            created_at=datetime.utcnow(),
        )
        self.db.add_all([self.user, self.other_user])
        self.db.commit()

        def db_override():
            try:
                yield self.db
            finally:
                pass

        self.current_user = self.user

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

    def add_aws_connection(self, *, user=None, credentials=True):
        owner = user or self.user
        connection = Connection(
            user_id=owner.id,
            organization_id=owner.organization_id,
            provider="AWS",
            provider_tenant_id="123456789012",
            credentials_encrypted=(
                encrypt_credentials({"access_key_id": "AKIA", "secret_access_key": "secret"})
                if credentials else None
            ),
            scopes="region=us-east-1;auth=account-credentials",
            status="ACTIVE",
        )
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)
        return connection

    def test_azure_connection_without_row_is_structured_disconnected_response(self):
        response = self.client.get("/integrations/azure/connection")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"id": 0, "provider": "AZURE", "connected": False, "status": "NOT_CONNECTED", "last_successful_refresh": None, "created_at": None, "updated_at": None},
        )

    def test_azure_connection_returns_safe_metadata_for_owned_row(self):
        row = AzureConnection(
            user_id=self.user.id,
            organization_id=self.user.organization_id,
            status="REAUTH_REQUIRED",
            encrypted_token_cache="encrypted-token-cache",
            last_successful_refresh=datetime.now(timezone.utc),
        )
        self.db.add(row)
        self.db.commit()

        response = self.client.get("/integrations/azure/connection")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "REAUTH_REQUIRED")
        self.assertFalse(payload["connected"])
        self.assertNotIn("encrypted_token_cache", payload)

    @patch.object(aws_routes, "get_account_plan_state")
    @patch.object(aws_routes, "get_aws_identity")
    def test_aws_account_plan_returns_plan_for_owned_connection(self, identity, plan):
        connection = self.add_aws_connection()
        identity.return_value = {"Account": connection.provider_tenant_id}
        plan.return_value = {
            "account_id": connection.provider_tenant_id,
            "plan_type": "FREE",
            "plan_status": "ACTIVE",
            "credits_remaining": 10.5,
            "currency": "USD",
            "expiration_date": "2027-01-01",
            "days_remaining": 74,
            "original_amount": None,
            "retrieved_at": datetime.now(timezone.utc),
            "data_status": "AVAILABLE",
        }

        response = self.client.get(f"/integrations/aws/connections/{connection.id}/account-plan")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["account_id"], "123456789012")
        self.assertEqual(response.json()["credits_remaining"], 10.5)

    def test_aws_account_plan_returns_404_for_missing_connection(self):
        response = self.client.get("/integrations/aws/connections/24/account-plan")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "AWS connection not found."})

    def test_aws_account_plan_does_not_cross_organization_boundary(self):
        connection = self.add_aws_connection(user=self.other_user)
        response = self.client.get(f"/integrations/aws/connections/{connection.id}/account-plan")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "AWS connection not found."})

    def test_aws_account_plan_requires_stored_credentials(self):
        connection = self.add_aws_connection(credentials=False)
        response = self.client.get(f"/integrations/aws/connections/{connection.id}/account-plan")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json(), {"detail": "Reconnect this AWS account with account credentials before loading account plan details."})

    @patch.object(aws_routes, "get_aws_identity", side_effect=AWSIntegrationError("denied", category="authorization"))
    def test_aws_account_plan_maps_provider_authorization_failure(self, _identity):
        connection = self.add_aws_connection()
        response = self.client.get(f"/integrations/aws/connections/{connection.id}/account-plan")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"detail": "denied"})


if __name__ == "__main__":
    unittest.main()
