import unittest
from unittest.mock import patch

import httpx

from app.integrations.anthropic.client import AnthropicIntegrationError, get_anthropic_usage_and_cost, validate_reporting_range, verify_anthropic_api_key, verify_anthropic_reporting_credential


class AnthropicClientTests(unittest.TestCase):
    @patch("app.integrations.anthropic.client.httpx.post")
    def test_verification_uses_messages_api_and_returns_no_secret(self, post):
        post.return_value = httpx.Response(200, json={"type": "message", "role": "assistant", "content": []}, headers={"request-id": "req-test"})

        result = verify_anthropic_api_key("sk-ant-test-secret", "claude-sonnet-4-6")

        self.assertEqual(result["model"], "claude-sonnet-4-6")
        self.assertNotIn("secret", repr(result))
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs["headers"]["anthropic-version"], "2026-10-21")
        self.assertEqual(kwargs["headers"]["x-api-key"], "sk-ant-test-secret")
        self.assertEqual(kwargs["json"]["max_tokens"], 1)

    @patch("app.integrations.anthropic.client.httpx.post")
    def test_authentication_error_is_classified_without_provider_payload(self, post):
        post.return_value = httpx.Response(401, json={"error": {"type": "authentication_error", "message": "invalid x-api-key"}})

        with self.assertRaises(AnthropicIntegrationError) as raised:
            verify_anthropic_api_key("sk-ant-test-secret", "claude-sonnet-4-6")

        self.assertEqual(raised.exception.category, "authentication")
        self.assertNotIn("sk-ant-test-secret", str(raised.exception))

    @patch("app.integrations.anthropic.client.httpx.post")
    def test_network_failure_is_not_reported_as_success(self, post):
        post.side_effect = httpx.ConnectError("connection unavailable")

        with self.assertRaises(AnthropicIntegrationError) as raised:
            verify_anthropic_api_key("sk-ant-test-secret", "claude-sonnet-4-6")

        self.assertEqual(raised.exception.category, "network")

    @patch("app.integrations.anthropic.client.httpx.get")
    def test_reporting_credential_uses_official_analytics_endpoint(self, get):
        get.return_value = httpx.Response(200, json={"data": [], "has_more": False, "data_refreshed_at": None})

        result = verify_anthropic_reporting_credential("sk-ant-admin-test")

        self.assertIsNone(result["data_refreshed_at"])
        request = get.call_args
        self.assertEqual(request.args[0], "https://api.anthropic.com/v1/organizations/analytics/usage")
        self.assertEqual(request.kwargs["headers"]["anthropic-beta"], "analytics-usage-cost-2026-08-24")
        self.assertEqual(request.kwargs["headers"]["x-api-key"], "sk-ant-admin-test")

    @patch("app.integrations.anthropic.client.httpx.get")
    def test_reporting_permission_error_is_distinguished(self, get):
        get.return_value = httpx.Response(403, json={"error": {"message": "forbidden"}})
        with self.assertRaises(AnthropicIntegrationError) as raised:
            verify_anthropic_reporting_credential("sk-ant-api-standard")
        self.assertEqual(raised.exception.category, "authorization")

    @patch("app.integrations.anthropic.client.httpx.get")
    def test_usage_and_cost_reports_follow_pagination_and_normalize_inputs(self, get):
        get.side_effect = [
            httpx.Response(200, json={"data": [{"starting_at": "2026-10-01T00:00:00Z", "ending_at": "2026-10-02T00:00:00Z", "group": {"model": "claude-sonnet-4-6"}, "usage": {"uncached_input_tokens": 10, "cache_creation": {"ephemeral_5m_input_tokens": 3, "ephemeral_1h_input_tokens": 2}, "cache_read_input_tokens": 4, "output_tokens": 6, "total_tokens": 25, "requests": 1}}], "has_more": True, "next_page": "page-2", "data_refreshed_at": "2026-10-30T01:00:00Z"}),
            httpx.Response(200, json={"data": [{"starting_at": "2026-10-02T00:00:00Z", "ending_at": "2026-10-03T00:00:00Z", "group": {"model": "claude-sonnet-4-6"}, "usage": {"uncached_input_tokens": 1, "cache_creation": {}, "cache_read_input_tokens": 0, "output_tokens": 2, "total_tokens": 3, "requests": 1}}], "has_more": False, "data_refreshed_at": "2026-10-30T01:00:00Z"}),
            httpx.Response(200, json={"data": [{"starting_at": "2026-10-01T00:00:00Z", "ending_at": "2026-10-02T00:00:00Z", "group": {"model": "claude-sonnet-4-6", "cost_type": "tokens", "token_type": "output_tokens"}, "cost": {"currency": "USD", "amount": "41280.000000", "list_amount": "51600.000000", "requests": None}}], "has_more": False, "data_refreshed_at": "2026-10-30T01:00:00Z"}),
        ]

        result = get_anthropic_usage_and_cost("sk-ant-admin-test", "2026-10-01", "2026-10-03")

        self.assertEqual(len(result["usage"]["data"]), 2)
        self.assertEqual(get.call_count, 3)
        self.assertIn(("page", "page-2"), get.call_args_list[1].kwargs["params"])
        self.assertEqual(result["cost"]["data"][0]["cost"]["amount"], "41280.000000")

    def test_reporting_date_range_rejects_more_than_31_days(self):
        with self.assertRaises(AnthropicIntegrationError) as raised:
            validate_reporting_range("2026-01-01", "2026-02-02")
        self.assertEqual(raised.exception.category, "configuration")


if __name__ == "__main__":
    unittest.main()
