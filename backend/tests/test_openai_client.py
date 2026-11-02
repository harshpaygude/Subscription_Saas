import unittest
from unittest.mock import patch

import httpx

from app.integrations.credentials import decrypt_credentials, encrypt_credentials
from app.integrations.openai.client import OpenAIIntegrationError, get_openai_costs, get_openai_usage, verify_openai_api_key


class OpenAIClientTests(unittest.TestCase):
    @patch("app.integrations.openai.client.httpx.get")
    def test_verifies_key_with_models_endpoint(self, mocked_get):
        mocked_get.return_value = httpx.Response(
            200,
            json={"data": [{"id": "gpt-4o-mini"}, {"id": "gpt-4o"}]},
        )

        result = verify_openai_api_key("sk-test")

        self.assertEqual(result, {"model_count": 2})
        request = mocked_get.call_args.args[0]
        self.assertEqual(request, "https://api.openai.com/v1/models")
        self.assertEqual(mocked_get.call_args.kwargs["headers"], {"Authorization": "Bearer sk-test"})

    @patch("app.integrations.openai.client.httpx.get")
    def test_rejects_invalid_key_without_echoing_it(self, mocked_get):
        secret = "sk-never-return-this"
        mocked_get.return_value = httpx.Response(401, json={"error": {"message": secret}})

        with self.assertRaises(OpenAIIntegrationError) as raised:
            verify_openai_api_key(secret)

        self.assertEqual(raised.exception.category, "authentication")
        self.assertNotIn(secret, str(raised.exception))

    @patch("app.integrations.openai.client.httpx.get")
    def test_maps_rate_limit_and_network_failures(self, mocked_get):
        mocked_get.return_value = httpx.Response(429, json={})
        with self.assertRaises(OpenAIIntegrationError) as rate_error:
            verify_openai_api_key("sk-test")
        self.assertEqual(rate_error.exception.category, "rate_limit")

        mocked_get.side_effect = httpx.ConnectTimeout("timeout")
        with self.assertRaises(OpenAIIntegrationError) as network_error:
            verify_openai_api_key("sk-test")
        self.assertEqual(network_error.exception.category, "network")

    def test_encrypts_and_round_trips_provider_credentials(self):
        secret = "sk-encrypted-value"
        encrypted = encrypt_credentials({"api_key": secret})

        self.assertNotIn(secret, encrypted)
        self.assertEqual(decrypt_credentials(encrypted), {"api_key": secret})

    @patch("app.integrations.openai.client.httpx.get")
    def test_aggregates_paginated_usage_without_double_counting(self, mocked_get):
        mocked_get.side_effect = [
            httpx.Response(200, json={"data": [{"start_time": 1, "end_time": 2, "results": [{"model": "gpt-test", "input_tokens": 10, "output_tokens": 4, "num_model_requests": 2}]}], "has_more": True, "next_page": "cursor"}),
            httpx.Response(200, json={"data": [{"start_time": 2, "end_time": 3, "results": [{"model": "gpt-test", "input_tokens": 6, "output_tokens": 3, "num_model_requests": 1}]}], "has_more": False, "next_page": None}),
        ]

        result = get_openai_usage("sk-test", 1, 3)

        self.assertEqual(result["total_input_tokens"], 16)
        self.assertEqual(result["total_output_tokens"], 7)
        self.assertEqual(result["total_tokens"], 23)
        self.assertEqual(result["requests"], 3)
        self.assertEqual(result["by_model"][0]["total_tokens"], 23)
        self.assertEqual(mocked_get.call_count, 2)
        self.assertIn(("page", "cursor"), mocked_get.call_args_list[1].kwargs["params"])

    @patch("app.integrations.openai.client.httpx.get")
    def test_aggregates_reported_costs(self, mocked_get):
        mocked_get.return_value = httpx.Response(200, json={"data": [{"start_time": 1, "end_time": 2, "results": [{"amount": {"value": 0.25, "currency": "usd"}, "project_id": "proj_a"}, {"amount": {"value": 0.10, "currency": "usd"}, "project_id": "proj_a"}]}], "has_more": False})

        result = get_openai_costs("sk-test", 1, 2)

        self.assertAlmostEqual(result["total"], 0.35)
        self.assertEqual(result["by_project"][0]["amount"], 0.35)

    @patch("app.integrations.openai.client.httpx.get")
    def test_maps_usage_permission_error(self, mocked_get):
        mocked_get.return_value = httpx.Response(403, json={})
        with self.assertRaises(OpenAIIntegrationError) as raised:
            get_openai_usage("sk-test", 1, 2)
        self.assertEqual(raised.exception.category, "authorization")


if __name__ == "__main__":
    unittest.main()
