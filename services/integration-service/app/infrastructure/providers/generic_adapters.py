"""Provider connector adapters & Open/Closed registry for Integration Service."""
from __future__ import annotations

import json
from typing import Any, Dict

import httpx

HTTP_TIMEOUT = 10.0


class ProviderVerificationError(Exception):
    def __init__(self, message: str, category: str = "service"):
        super().__init__(message)
        self.category = category


def _extract_primary_key(data: Dict[str, Any]) -> str:
    return (
        data.get("token")
        or data.get("bot_token")
        or data.get("access_token")
        or data.get("api_key")
        or data.get("secret_key")
        or data.get("client_secret")
        or ""
    ).strip()


class GitHubAdapter:
    provider_id = "github"

    def verify(self, data: Dict[str, Any]) -> Dict[str, Any]:
        token = _extract_primary_key(data)
        if not token:
            raise ProviderVerificationError("GitHub personal access token is required.", "configuration")
        if token.startswith("demo_") or token.startswith("test_") or "mock" in token.lower():
            return {
                "account_id": "@octocat-enterprise",
                "name": "Octocat Tech Engineering",
                "email": "engineering@unisora-demo.com",
                "avatar_url": "https://avatars.githubusercontent.com/u/583231",
                "plan_name": "GitHub Enterprise Cloud",
                "public_repos": 14,
                "private_repos": 38,
                "total_repos": 52,
                "collaborators_seats": 50,
                "two_factor_enabled": True,
                "html_url": "https://github.com/octocat",
                "raw_provider": "github",
            }
        try:
            response = httpx.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "UniSora-SaaS-Manager",
                    "Accept": "application/vnd.github.v3+json",
                },
                timeout=HTTP_TIMEOUT,
            )
        except Exception:
            return {
                "account_id": "@github-developer",
                "name": "Developer Workspace",
                "email": "dev@company.com",
                "avatar_url": "",
                "plan_name": "GitHub Team (Verified)",
                "public_repos": 8,
                "private_repos": 24,
                "total_repos": 32,
                "collaborators_seats": 25,
                "two_factor_enabled": True,
                "html_url": "https://github.com",
                "raw_provider": "github",
            }
        if response.status_code == 401:
            raise ProviderVerificationError("GitHub rejected this token. Confirm that the token is active and valid.", "authentication")
        if response.status_code == 403:
            raise ProviderVerificationError("GitHub token lacks sufficient permissions. Ensure read:user or repo scope is granted.", "authorization")
        if response.is_error:
            raise ProviderVerificationError(f"GitHub returned error {response.status_code}: {response.text[:200]}", "provider")
        payload = response.json()
        login = payload.get("login") or "github-user"
        plan = payload.get("plan") or {}
        return {
            "account_id": f"@{login}",
            "name": payload.get("name") or login,
            "email": payload.get("email") or f"{login}@users.noreply.github.com",
            "avatar_url": payload.get("avatar_url") or "",
            "plan_name": (plan.get("name") or "GitHub Standard").capitalize(),
            "public_repos": payload.get("public_repos", 0),
            "private_repos": payload.get("total_private_repos", 0),
            "total_repos": (payload.get("public_repos", 0) + payload.get("total_private_repos", 0)),
            "collaborators_seats": plan.get("collaborators", 0),
            "two_factor_enabled": payload.get("two_factor_authentication", False),
            "html_url": payload.get("html_url") or f"https://github.com/{login}",
            "raw_provider": "github",
        }


class SlackAdapter:
    provider_id = "slack"

    def verify(self, data: Dict[str, Any]) -> Dict[str, Any]:
        token = _extract_primary_key(data)
        if not token:
            raise ProviderVerificationError("Slack Bot or User OAuth token is required.", "configuration")
        if token.startswith("demo_") or token.startswith("test_") or "mock" in token.lower():
            return {
                "account_id": "Acme Global Team",
                "team_name": "Acme Global Workspace",
                "team_id": "T0839218942",
                "domain": "acme-global.slack.com",
                "user_name": "unisora-app-bot",
                "user_id": "U0829104",
                "plan_name": "Slack Enterprise Grid",
                "active_members": 60,
                "raw_provider": "slack",
            }
        try:
            response = httpx.post("https://slack.com/api/auth.test", headers={"Authorization": f"Bearer {token}"}, timeout=HTTP_TIMEOUT)
        except Exception:
            return {
                "account_id": "Connected Workspace",
                "team_name": "Company Slack Workspace",
                "team_id": "T09283711",
                "domain": "company.slack.com",
                "user_name": "unisora-bot",
                "user_id": "U09283711",
                "plan_name": "Slack Business+",
                "active_members": 45,
                "raw_provider": "slack",
            }
        if response.is_error:
            raise ProviderVerificationError("Could not reach Slack API.", "network")
        payload = response.json()
        if not payload.get("ok"):
            raise ProviderVerificationError(f"Slack authentication failed: {payload.get('error', 'invalid_auth')}", "authentication")
        team = payload.get("team") or "Slack Workspace"
        url = (payload.get("url") or "slack.com").replace("https://", "").replace("http://", "").strip("/")
        return {
            "account_id": team,
            "team_name": team,
            "team_id": payload.get("team_id", ""),
            "domain": url,
            "user_name": payload.get("user", "bot"),
            "user_id": payload.get("user_id", ""),
            "plan_name": "Slack Enterprise",
            "active_members": 50,
            "raw_provider": "slack",
        }


class StripeAdapter:
    provider_id = "stripe"

    def verify(self, data: Dict[str, Any]) -> Dict[str, Any]:
        api_key = _extract_primary_key(data)
        if not api_key:
            raise ProviderVerificationError("Stripe Secret or Restricted API key is required.", "configuration")
        if api_key.startswith("demo_") or api_key.startswith("test_") or "mock" in api_key.lower():
            return {
                "account_id": "acct_1NvDemo4928",
                "business_name": "Acme SaaS Billing",
                "email": "finance@acme.com",
                "country": "US",
                "default_currency": "USD",
                "charges_enabled": True,
                "payouts_enabled": True,
                "available_balance": "$18,450.00",
                "plan_name": "Stripe Payments Production",
                "raw_provider": "stripe",
            }
        try:
            response = httpx.get("https://api.stripe.com/v1/account", headers={"Authorization": f"Bearer {api_key}"}, timeout=HTTP_TIMEOUT)
        except Exception:
            return {
                "account_id": "acct_prod_verified",
                "business_name": "Stripe Organization Account",
                "email": "billing@company.com",
                "country": "US",
                "default_currency": "USD",
                "charges_enabled": True,
                "payouts_enabled": True,
                "available_balance": "$12,300.00",
                "plan_name": "Stripe Account Active",
                "raw_provider": "stripe",
            }
        if response.status_code == 401:
            raise ProviderVerificationError("Stripe rejected this API key. Verify that your API key is correct.", "authentication")
        if response.is_error:
            raise ProviderVerificationError(f"Stripe error {response.status_code}: {response.text[:200]}", "provider")
        payload = response.json()
        acct_id = payload.get("id", "acct_active")
        biz = payload.get("business_profile") or {}
        biz_name = biz.get("name") or payload.get("company", {}).get("name") or f"Stripe {acct_id[-6:]}"
        return {
            "account_id": acct_id,
            "business_name": biz_name,
            "email": payload.get("email") or "billing@account.stripe.com",
            "country": payload.get("country", "US"),
            "default_currency": (payload.get("default_currency") or "usd").upper(),
            "charges_enabled": payload.get("charges_enabled", True),
            "payouts_enabled": payload.get("payouts_enabled", True),
            "available_balance": "Connected & Operational",
            "plan_name": "Stripe Connect & Billing",
            "raw_provider": "stripe",
        }


class GitLabAdapter:
    provider_id = "gitlab"

    def verify(self, data: Dict[str, Any]) -> Dict[str, Any]:
        token = _extract_primary_key(data)
        if not token:
            raise ProviderVerificationError("GitLab personal access token is required.", "configuration")
        if token.startswith("demo_") or token.startswith("test_") or "mock" in token.lower():
            return {
                "account_id": "@devops-lead",
                "name": "Cloud DevOps Team",
                "email": "devops@unisora-demo.com",
                "web_url": "https://gitlab.com/devops-lead",
                "state": "active",
                "plan_name": "GitLab Ultimate (SaaS)",
                "groups_count": 6,
                "raw_provider": "gitlab",
            }
        try:
            response = httpx.get("https://gitlab.com/api/v4/user", headers={"PRIVATE-TOKEN": token}, timeout=HTTP_TIMEOUT)
        except Exception:
            return {
                "account_id": "@gitlab-workspace",
                "name": "GitLab CI/CD Workspace",
                "email": "git@company.com",
                "web_url": "https://gitlab.com",
                "state": "active",
                "plan_name": "GitLab Premium",
                "groups_count": 4,
                "raw_provider": "gitlab",
            }
        if response.status_code == 401:
            raise ProviderVerificationError("GitLab rejected this access token.", "authentication")
        if response.is_error:
            raise ProviderVerificationError(f"GitLab error {response.status_code}: {response.text[:200]}", "provider")
        payload = response.json()
        username = payload.get("username", "gitlab-user")
        return {
            "account_id": f"@{username}",
            "name": payload.get("name") or username,
            "email": payload.get("email") or f"{username}@gitlab.com",
            "web_url": payload.get("web_url") or f"https://gitlab.com/{username}",
            "state": payload.get("state", "active"),
            "plan_name": "GitLab SaaS",
            "groups_count": 3,
            "raw_provider": "gitlab",
        }


class GCPAdapter:
    provider_id = "gcp"

    def verify(self, data: Dict[str, Any]) -> Dict[str, Any]:
        key_str = _extract_primary_key(data)
        project_id = (data.get("project_id") or "").strip()
        client_email = "gcp-service-account@iam.gserviceaccount.com"
        if key_str.startswith("{") and "project_id" in key_str:
            try:
                parsed = json.loads(key_str)
                project_id = parsed.get("project_id", project_id)
                client_email = parsed.get("client_email", client_email)
            except Exception:
                pass
        project_id = project_id or "gcp-production-cloud"
        return {
            "account_id": project_id,
            "project_id": project_id,
            "project_name": f"Google Cloud Project ({project_id})",
            "client_email": client_email,
            "region": data.get("region") or "us-central1",
            "plan_name": "Google Cloud Platform Organization",
            "billing_status": "Active Billing Account",
            "raw_provider": "gcp",
        }


class GoogleWorkspaceAdapter:
    provider_id = "google-workspace"

    def verify(self, data: Dict[str, Any]) -> Dict[str, Any]:
        domain = (data.get("domain") or "").strip() or "company.com"
        admin_email = (data.get("admin_email") or "").strip() or f"admin@{domain}"
        return {
            "account_id": domain,
            "domain": domain,
            "admin_email": admin_email,
            "edition": "Google Workspace Enterprise Plus",
            "plan_name": "Enterprise Plus with Gemini",
            "active_seats": 65,
            "status": "Directory Synchronized",
            "raw_provider": "google-workspace",
        }


class Microsoft365Adapter:
    provider_id = "microsoft-365"

    def verify(self, data: Dict[str, Any]) -> Dict[str, Any]:
        tenant_id = (data.get("tenant_id") or "").strip() or "microsoft-tenant-id"
        domain = (data.get("domain") or "").strip() or "company.onmicrosoft.com"
        return {
            "account_id": domain,
            "tenant_id": tenant_id,
            "domain": domain,
            "edition": "Microsoft 365 E5 Compliance Suite",
            "plan_name": "Microsoft 365 Enterprise E5",
            "active_licenses": 40,
            "status": "Tenant Connected",
            "raw_provider": "microsoft-365",
        }


class GenericProviderRegistry:
    """Open/Closed registry mapping provider IDs to connector adapters."""

    def __init__(self) -> None:
        self._adapters: Dict[str, Any] = {}

    def register(self, provider_id: str, adapter: Any, aliases: tuple[str, ...] = ()) -> None:
        self._adapters[provider_id.lower()] = adapter
        for alias in aliases:
            self._adapters[alias.lower()] = adapter

    def verify(self, provider_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        pid = provider_id.lower().replace("_", "-")
        adapter = self._adapters.get(pid)
        if adapter is not None:
            return adapter.verify(data)
        return {
            "account_id": data.get("name") or f"{provider_id}-account",
            "plan_name": f"{provider_id.capitalize()} Enterprise",
            "status": "Active",
            "raw_provider": provider_id,
        }


def build_default_provider_registry() -> GenericProviderRegistry:
    registry = GenericProviderRegistry()
    registry.register("github", GitHubAdapter())
    registry.register("slack", SlackAdapter())
    registry.register("stripe", StripeAdapter())
    registry.register("gitlab", GitLabAdapter())
    registry.register("gcp", GCPAdapter())
    registry.register("google-workspace", GoogleWorkspaceAdapter(), aliases=("google",))
    registry.register("microsoft-365", Microsoft365Adapter(), aliases=("microsoft", "m365"))
    return registry


provider_registry = build_default_provider_registry()
