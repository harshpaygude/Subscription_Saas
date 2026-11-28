import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

import httpx
from fastapi.testclient import TestClient
from jose import jwt

from unisora_kit import verify_internal_service_token
from app.config import GatewaySettings, settings
from app.main import app
from app.rate_limit import SlidingWindowRateLimiter
from app.routing import build_route_table, resolve_route


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self):
        self.client.close()

    def test_route_resolution_and_extensibility(self):
        cfg = GatewaySettings(extra_routes_json='[{"prefix": "/billing-v2", "service": "billing-v2", "url": "http://billing:8007"}]')
        rules = build_route_table(cfg)
        self.assertEqual(resolve_route("/employees/42/onboarding", rules).service_name, "lifecycle-service")
        self.assertEqual(resolve_route("/employees/42", rules).service_name, "identity-service")
        self.assertEqual(resolve_route("/subscriptions/1/licenses", rules).service_name, "subscription-service")
        self.assertEqual(resolve_route("/assets/1", rules).service_name, "asset-service")
        self.assertEqual(resolve_route("/integrations/aws/connections", rules).service_name, "integration-service")
        self.assertEqual(resolve_route("/alerts", rules).service_name, "governance-service")
        self.assertEqual(resolve_route("/billing-v2/invoices", rules).service_name, "billing-v2")

    def test_blocks_internal_routes_externally(self):
        res = self.client.get("/internal/users")
        self.assertEqual(res.status_code, 403)

    def test_rejects_missing_jwt_on_protected_route(self):
        res = self.client.get("/subscriptions")
        self.assertEqual(res.status_code, 401)

    def test_forwards_verified_identity_headers_and_signed_internal_token(self):
        token = jwt.encode(
            {"sub": "7", "organization_id": "3", "role": "OWNER", "email": "owner@acme.test"},
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        captured = {}

        async def fake_request(*, method, url, params, headers, content, follow_redirects):
            captured["url"] = url
            captured["headers"] = headers
            return httpx.Response(200, json={"ok": True})

        with patch("app.main.get_http_client") as mock_client:
            mock_client.return_value.request = AsyncMock(side_effect=fake_request)
            res = self.client.get("/subscriptions", headers={"Authorization": f"Bearer {token}"})

        self.assertEqual(res.status_code, 200)
        self.assertEqual(captured["headers"]["X-User-Id"], "7")
        self.assertEqual(captured["headers"]["X-Organization-Id"], "3")
        self.assertEqual(captured["headers"]["X-User-Role"], "OWNER")
        self.assertTrue(
            verify_internal_service_token(
                captured["headers"]["X-Internal-Service-Token"],
                settings.internal_service_secret,
                user_id=7,
                organization_id=3,
                role="OWNER",
            )
        )

    def test_rate_limiter_enforces_quota(self):
        limiter = SlidingWindowRateLimiter(max_requests_per_minute=2)
        self.assertTrue(limiter.allow("10.0.0.1"))
        self.assertTrue(limiter.allow("10.0.0.1"))
        self.assertFalse(limiter.allow("10.0.0.1"))


if __name__ == "__main__":
    unittest.main()
