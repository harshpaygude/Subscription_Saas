import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

import httpx
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from unisora_kit import RequestContext
from app.api import aws_routes
from app.api.deps import get_current_context
from app.infrastructure.crypto import decrypt_credentials, encrypt_credentials
from app.infrastructure.db import Base, get_db
from app.infrastructure.models import AzureConnection, Connection
from app.infrastructure.providers.anthropic_client import (
    AnthropicIntegrationError,
    get_anthropic_usage_and_cost,
    validate_reporting_range,
    verify_anthropic_api_key,
    verify_anthropic_reporting_credential,
)
from app.infrastructure.providers.aws_client import (
    AWSIntegrationError,
    get_account_plan_state,
    get_aws_identity,
    verify_aws_connection,
)
from app.infrastructure.providers.generic_adapters import provider_registry
from app.infrastructure.providers.openai_client import (
    OpenAIIntegrationError,
    get_openai_costs,
    get_openai_usage,
    verify_openai_api_key,
)
from app.main import app


class FakeAWSClient:
    def __init__(self, service_name):
        self.service_name = service_name

    def get_caller_identity(self):
        return {"Account": "123456789012", "Arn": "arn:aws:iam::123456789012:user/test"}

    def get_cost_and_usage(self, **kwargs):
        return {"ResultsByTime": []}

    def get_account_plan_state(self):
        return {
            "accountId": "123456789012",
            "accountPlanType": "FREE",
            "accountPlanStatus": "ACTIVE",
            "accountPlanRemainingCredits": {"amount": 100.5, "unit": "USD"},
            "accountPlanExpirationDate": datetime(2026, 10, 18, 23, tzinfo=timezone.utc),
        }


class FakeSession:
    def get_available_regions(self, service_name):
        return ["us-east-1", "eu-west-1"]

    def client(self, service_name):
        return FakeAWSClient(service_name)


class AWSClientTests(unittest.TestCase):
    credentials = {"access_key_id": "AKIAEXAMPLE", "secret_access_key": "secret-value"}

    @patch("app.infrastructure.providers.aws_client.boto3.Session", return_value=FakeSession())
    def test_verification_checks_identity_and_read_only_cost_access(self, _session):
        result = verify_aws_connection(self.credentials, " US-EAST-1 ")
        self.assertEqual(result["account_id"], "123456789012")
        self.assertTrue(result["cost_access"])
        self.assertEqual(result["region"], "us-east-1")

    @patch("app.infrastructure.providers.aws_client.boto3.Session", return_value=FakeSession())
    def test_invalid_region_is_rejected_before_sdk_call(self, session):
        with self.assertRaisesRegex(AWSIntegrationError, "not a valid AWS region") as raised:
            verify_aws_connection(self.credentials, "not-a-region")
        self.assertEqual(raised.exception.category, "region")
        session.assert_called_once()

    @patch("app.infrastructure.providers.aws_client.boto3.Session", return_value=FakeSession())
    def test_missing_credentials_are_classified_as_configuration_error(self, _session):
        with self.assertRaises(AWSIntegrationError) as raised:
            get_aws_identity({"access_key_id": "only"})
        self.assertEqual(raised.exception.category, "configuration")
        self.assertNotIn("only", str(raised.exception))

    @patch("app.infrastructure.providers.aws_client.boto3.Session")
    def test_sts_permission_failure_does_not_echo_sdk_details(self, session):
        fake = FakeSession()
        error = ClientError({"Error": {"Code": "AccessDenied", "Message": "secret-value should not be returned"}}, "GetCallerIdentity")
        fake.client = lambda _s: type("Denied", (), {"get_caller_identity": lambda _self: (_ for _ in ()).throw(error)})()
        session.return_value = fake
        with self.assertRaises(AWSIntegrationError) as raised:
            get_aws_identity(self.credentials)
        self.assertEqual(raised.exception.category, "authorization")
        self.assertNotIn("secret-value", str(raised.exception))

    @patch("app.infrastructure.providers.aws_client.boto3.Session", return_value=FakeSession())
    @patch("app.infrastructure.providers.aws_client.datetime")
    def test_account_plan_uses_utc_calendar_days(self, clock, _session):
        clock.now.return_value = datetime(2026, 10, 17, 23, 30, tzinfo=timezone.utc)
        result = get_account_plan_state(self.credentials, "us-east-1")
        self.assertEqual(result["credits_remaining"], 100.5)
        self.assertEqual(result["expiration_date"], "2026-10-18")
        self.assertEqual(result["days_remaining"], 1)


class OpenAIClientTests(unittest.TestCase):
    @patch("app.infrastructure.providers.openai_client.httpx.get")
    def test_verifies_key_with_models_endpoint(self, mocked_get):
        mocked_get.return_value = httpx.Response(200, json={"data": [{"id": "gpt-4o-mini"}, {"id": "gpt-4o"}]})
        self.assertEqual(verify_openai_api_key("sk-test"), {"model_count": 2})

    @patch("app.infrastructure.providers.openai_client.httpx.get")
    def test_rejects_invalid_key_without_echoing_it(self, mocked_get):
        secret = "sk-never-return-this"
        mocked_get.return_value = httpx.Response(401, json={"error": {"message": secret}})
        with self.assertRaises(OpenAIIntegrationError) as raised:
            verify_openai_api_key(secret)
        self.assertEqual(raised.exception.category, "authentication")
        self.assertNotIn(secret, str(raised.exception))

    @patch("app.infrastructure.providers.openai_client.httpx.get")
    def test_maps_rate_limit_and_network_failures(self, mocked_get):
        mocked_get.return_value = httpx.Response(429, json={})
        with self.assertRaises(OpenAIIntegrationError) as rate_error:
            verify_openai_api_key("sk-test")
        self.assertEqual(rate_error.exception.category, "rate_limit")
        mocked_get.side_effect = httpx.ConnectTimeout("timeout")
        with self.assertRaises(OpenAIIntegrationError) as net_error:
            verify_openai_api_key("sk-test")
        self.assertEqual(net_error.exception.category, "network")

    def test_encrypts_and_round_trips_provider_credentials(self):
        secret = "sk-encrypted-value"
        encrypted = encrypt_credentials({"api_key": secret})
        self.assertNotIn(secret, encrypted)
        self.assertEqual(decrypt_credentials(encrypted), {"api_key": secret})

    @patch("app.infrastructure.providers.openai_client.httpx.get")
    def test_aggregates_paginated_usage_and_costs(self, mocked_get):
        mocked_get.side_effect = [
            httpx.Response(200, json={"data": [{"start_time": 1, "end_time": 2, "results": [{"model": "gpt-test", "input_tokens": 10, "output_tokens": 4, "num_model_requests": 2}]}], "has_more": True, "next_page": "cursor"}),
            httpx.Response(200, json={"data": [{"start_time": 2, "end_time": 3, "results": [{"model": "gpt-test", "input_tokens": 6, "output_tokens": 3, "num_model_requests": 1}]}], "has_more": False}),
            httpx.Response(200, json={"data": [{"start_time": 1, "end_time": 2, "results": [{"amount": {"value": 0.25, "currency": "usd"}, "project_id": "proj_a"}, {"amount": {"value": 0.10, "currency": "usd"}, "project_id": "proj_a"}]}], "has_more": False}),
        ]
        usage = get_openai_usage("sk-test", 1, 3)
        self.assertEqual(usage["total_tokens"], 23)
        costs = get_openai_costs("sk-test", 1, 2)
        self.assertAlmostEqual(costs["total"], 0.35)


class AnthropicClientTests(unittest.TestCase):
    @patch("app.infrastructure.providers.anthropic_client.httpx.post")
    def test_verification_uses_messages_api_and_returns_no_secret(self, post):
        post.return_value = httpx.Response(200, json={"type": "message"}, headers={"request-id": "req-test"})
        result = verify_anthropic_api_key("sk-ant-test-secret", "claude-sonnet-4-6")
        self.assertEqual(result["model"], "claude-sonnet-4-6")

    @patch("app.infrastructure.providers.anthropic_client.httpx.post")
    def test_authentication_and_network_errors(self, post):
        post.return_value = httpx.Response(401, json={"error": {"message": "invalid x-api-key"}})
        with self.assertRaises(AnthropicIntegrationError) as auth_err:
            verify_anthropic_api_key("sk-ant-test-secret", "claude-sonnet-4-6")
        self.assertEqual(auth_err.exception.category, "authentication")
        post.side_effect = httpx.ConnectError("unavailable")
        with self.assertRaises(AnthropicIntegrationError) as net_err:
            verify_anthropic_api_key("sk-ant-test-secret", "claude-sonnet-4-6")
        self.assertEqual(net_err.exception.category, "network")

    @patch("app.infrastructure.providers.anthropic_client.httpx.get")
    def test_reporting_and_pagination(self, get):
        get.return_value = httpx.Response(200, json={"data": [], "has_more": False, "data_refreshed_at": None})
        self.assertIsNone(verify_anthropic_reporting_credential("sk-ant-admin-test")["data_refreshed_at"])
        get.side_effect = [
            httpx.Response(200, json={"data": [{"usage": {"total_tokens": 25}}], "has_more": True, "next_page": "page-2"}),
            httpx.Response(200, json={"data": [{"usage": {"total_tokens": 3}}], "has_more": False}),
            httpx.Response(200, json={"data": [{"cost": {"amount": "41280.000000"}}], "has_more": False}),
        ]
        res = get_anthropic_usage_and_cost("sk-ant-admin-test", "2026-10-01", "2026-10-03")
        self.assertEqual(len(res["usage"]["data"]), 2)

    def test_reporting_date_range_rejects_more_than_31_days(self):
        with self.assertRaises(AnthropicIntegrationError) as raised:
            validate_reporting_range("2026-01-01", "2026-02-02")
        self.assertEqual(raised.exception.category, "configuration")


class IntegrationRouteAndRegistryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.ctx = RequestContext(user_id=1, organization_id=1, role="OWNER")

        app.dependency_overrides[get_db] = lambda: (yield self.db)
        app.dependency_overrides[get_current_context] = lambda: self.ctx
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()
        self.db.close()
        self.engine.dispose()

    def add_aws_connection(self, *, user_id=1, org_id=1, credentials=True):
        conn = Connection(
            user_id=user_id,
            organization_id=org_id,
            provider="AWS",
            provider_tenant_id="123456789012",
            credentials_encrypted=encrypt_credentials({"access_key_id": "AKIA", "secret_access_key": "secret"}) if credentials else None,
            scopes="region=us-east-1;auth=account-credentials",
            status="ACTIVE",
        )
        self.db.add(conn)
        self.db.commit()
        self.db.refresh(conn)
        return conn

    def test_azure_connection_without_row_and_with_row(self):
        res = self.client.get("/integrations/azure/connection")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()["connected"])
        self.db.add(AzureConnection(user_id=1, organization_id=1, status="REAUTH_REQUIRED", encrypted_token_cache="enc"))
        self.db.commit()
        res2 = self.client.get("/integrations/azure/connection")
        self.assertEqual(res2.json()["status"], "REAUTH_REQUIRED")
        self.assertNotIn("encrypted_token_cache", res2.json())

    @patch.object(aws_routes, "get_account_plan_state")
    @patch.object(aws_routes, "get_aws_identity")
    def test_aws_account_plan_and_isolation(self, identity, plan):
        conn = self.add_aws_connection()
        identity.return_value = {"Account": conn.provider_tenant_id}
        plan.return_value = {
            "account_id": conn.provider_tenant_id, "plan_type": "FREE", "plan_status": "ACTIVE",
            "credits_remaining": 10.5, "currency": "USD", "expiration_date": "2027-01-01",
            "days_remaining": 74, "original_amount": None, "retrieved_at": datetime.now(timezone.utc), "data_status": "AVAILABLE",
        }
        res = self.client.get(f"/integrations/aws/connections/{conn.id}/account-plan")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["credits_remaining"], 10.5)

        other_conn = self.add_aws_connection(user_id=2, org_id=2)
        res_other = self.client.get(f"/integrations/aws/connections/{other_conn.id}/account-plan")
        self.assertEqual(res_other.status_code, 404)

    def test_ocp_custom_provider_adapter_registration(self):
        class _CustomDatadogAdapter:
            def verify(self, data):
                return {"account_id": f"dd-{data.get('site', 'us1')}", "plan_name": "Datadog Pro"}

        provider_registry.register("datadog-custom", _CustomDatadogAdapter())
        result = provider_registry.verify("datadog-custom", {"site": "eu1"})
        self.assertEqual(result["account_id"], "dd-eu1")


if __name__ == "__main__":
    unittest.main()
