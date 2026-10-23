import unittest
from unittest.mock import patch

import httpx

from app.integrations.anthropic.client import AnthropicIntegrationError, verify_anthropic_api_key


class AnthropicClientTests(unittest.TestCase):
    @patch("app.integrations.anthropic.client.httpx.post")
    def test_verification_uses_messages_api_and_returns_no_secret(self, post):
        post.return_value = httpx.Response(200, json={"type": "message", "role": "assistant", "content": []}, headers={"request-id": "req-test"})

        result = verify_anthropic_api_key("sk-ant-test-secret", "claude-sonnet-4-6")

        self.assertEqual(result["model"], "claude-sonnet-4-6")
        self.assertNotIn("secret", repr(result))
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs["headers"]["anthropic-version"], "2023-06-01")
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


if __name__ == "__main__":
    unittest.main()
