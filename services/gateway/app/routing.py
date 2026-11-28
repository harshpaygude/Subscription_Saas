"""Declarative service routing table for the API Gateway."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional

from app.config import GatewaySettings


@dataclass(frozen=True)
class RouteRule:
    service_name: str
    target_url: str
    pattern: re.Pattern[str]
    require_auth: bool = True


def build_route_table(cfg: GatewaySettings) -> list[RouteRule]:
    """Build ordered route rules (most specific patterns first)."""
    rules = [
        # Lifecycle endpoints nested under /employees/{id}/...
        RouteRule("lifecycle-service", cfg.lifecycle_service_url, re.compile(r"^/employees/\d+/(onboarding|offboarding|lifecycle)$")),
        RouteRule("lifecycle-service", cfg.lifecycle_service_url, re.compile(r"^/employee-lifecycle(/.*)?$")),
        RouteRule("lifecycle-service", cfg.lifecycle_service_url, re.compile(r"^/lifecycle-tasks(/.*)?$")),

        # Identity & Organization endpoints
        RouteRule("identity-service", cfg.identity_service_url, re.compile(r"^/auth/(login|register)$"), require_auth=False),
        RouteRule("identity-service", cfg.identity_service_url, re.compile(r"^/auth(/.*)?$")),
        RouteRule("identity-service", cfg.identity_service_url, re.compile(r"^/organizations(/.*)?$")),
        RouteRule("identity-service", cfg.identity_service_url, re.compile(r"^/departments(/.*)?$")),
        RouteRule("identity-service", cfg.identity_service_url, re.compile(r"^/employees(/.*)?$")),

        # Subscriptions & Licensing
        RouteRule("subscription-service", cfg.subscription_service_url, re.compile(r"^/subscriptions(/.*)?$")),
        RouteRule("subscription-service", cfg.subscription_service_url, re.compile(r"^/subscription-assignments(/.*)?$")),

        # IT Assets
        RouteRule("asset-service", cfg.asset_service_url, re.compile(r"^/assets/sample-template$"), require_auth=False),
        RouteRule("asset-service", cfg.asset_service_url, re.compile(r"^/assets(/.*)?$")),

        # External Integrations
        RouteRule("integration-service", cfg.integration_service_url, re.compile(r"^/integrations/azure/oauth/callback$"), require_auth=False),
        RouteRule("integration-service", cfg.integration_service_url, re.compile(r"^/integrations(/.*)?$")),

        # Governance (Alerts & Analytics)
        RouteRule("governance-service", cfg.governance_service_url, re.compile(r"^/alerts(/.*)?$")),
        RouteRule("governance-service", cfg.governance_service_url, re.compile(r"^/analytics(/.*)?$")),
    ]

    try:
        extras = json.loads(cfg.extra_routes_json or "[]")
        for item in extras:
            prefix = str(item.get("prefix") or "").rstrip("/")
            url = str(item.get("url") or "").rstrip("/")
            svc = str(item.get("service") or "custom-service")
            req_auth = bool(item.get("require_auth", True))
            if prefix and url:
                rules.insert(
                    0,
                    RouteRule(svc, url, re.compile(rf"^{re.escape(prefix)}(/.*)?$"), require_auth=req_auth),
                )
    except Exception:
        pass

    return rules


def resolve_route(path: str, rules: list[RouteRule]) -> Optional[RouteRule]:
    for rule in rules:
        if rule.pattern.match(path):
            return rule
    return None
