import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from botocore.exceptions import ClientError

from app.integrations.aws.client import (
    AWSIntegrationError,
    get_account_plan_state,
    get_aws_identity,
    verify_aws_connection,
)


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

    @patch("app.integrations.aws.client.boto3.Session", return_value=FakeSession())
    def test_verification_checks_identity_and_read_only_cost_access(self, _session):
        result = verify_aws_connection(self.credentials, " US-EAST-1 ")
        self.assertEqual(result["account_id"], "123456789012")
        self.assertTrue(result["cost_access"])
        self.assertEqual(result["region"], "us-east-1")

    @patch("app.integrations.aws.client.boto3.Session", return_value=FakeSession())
    def test_invalid_region_is_rejected_before_sdk_call(self, session):
        with self.assertRaisesRegex(AWSIntegrationError, "not a valid AWS region") as raised:
            verify_aws_connection(self.credentials, "not-a-region")
        self.assertEqual(raised.exception.category, "region")
        session.assert_called_once()

    @patch("app.integrations.aws.client.boto3.Session", return_value=FakeSession())
    def test_missing_credentials_are_classified_as_configuration_error(self, _session):
        with self.assertRaises(AWSIntegrationError) as raised:
            get_aws_identity({"access_key_id": "only"})
        self.assertEqual(raised.exception.category, "configuration")
        self.assertNotIn("only", str(raised.exception))
        self.assertNotIn("secret-value", str(raised.exception))

    @patch("app.integrations.aws.client.boto3.Session")
    def test_sts_permission_failure_does_not_echo_sdk_details(self, session):
        fake = FakeSession()
        error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "secret-value should not be returned"}},
            "GetCallerIdentity",
        )
        fake.client = lambda _service: type("DeniedClient", (), {"get_caller_identity": lambda _self: (_ for _ in ()).throw(error)})()
        session.return_value = fake
        with self.assertRaises(AWSIntegrationError) as raised:
            get_aws_identity(self.credentials)
        self.assertEqual(raised.exception.category, "authorization")
        self.assertNotIn("secret-value", str(raised.exception))

    @patch("app.integrations.aws.client.boto3.Session", return_value=FakeSession())
    @patch("app.integrations.aws.client.datetime")
    def test_account_plan_uses_utc_calendar_days_and_keeps_raw_expiration(self, clock, _session):
        clock.now.return_value = datetime(2026, 10, 17, 23, 30, tzinfo=timezone.utc)
        result = get_account_plan_state(self.credentials, "us-east-1")
        self.assertEqual(result["credits_remaining"], 100.5)
        self.assertEqual(result["expiration_date"], "2026-10-18")
        self.assertEqual(result["days_remaining"], 1)
        self.assertEqual(result["data_status"], "AVAILABLE")
        self.assertIsNone(result["original_amount"])


if __name__ == "__main__":
    unittest.main()
