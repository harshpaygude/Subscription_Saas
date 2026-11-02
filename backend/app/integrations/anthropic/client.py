"""Server-side Anthropic Messages and organization analytics client.

The standard Messages API key and optional organization reporting credential are
kept separate by the caller. Secrets never appear in returned payloads or
provider error messages.
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import time
from typing import Any

import httpx

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_ANALYTICS_BASE_URL = "https://api.anthropic.com/v1/organizations/analytics"
ANTHROPIC_API_VERSION = "2026-10-21"
ANTHROPIC_ANALYTICS_BETA = "analytics-usage-cost-2026-08-24"


class AnthropicIntegrationError(Exception):
    def __init__(self, message: str, *, category: str = "provider"):
        super().__init__(message)
        self.category = category


def _provider_message(response: httpx.Response) -> str:
    try:
        value = response.json().get("error", {}).get("message")
        return value if isinstance(value, str) and value else ""
    except (ValueError, AttributeError, TypeError):
        return ""


def _error_for_response(response: httpx.Response, model: str = "") -> AnthropicIntegrationError:
    provider_message = _provider_message(response).lower()
    if response.status_code == 401:
        return AnthropicIntegrationError("Anthropic rejected this credential.", category="authentication")
    if response.status_code == 403:
        return AnthropicIntegrationError("This Anthropic credential is not permitted to access this reporting operation.", category="authorization")
    if response.status_code == 404 or ("model" in provider_message and "not found" in provider_message):
        return AnthropicIntegrationError(f"Anthropic does not support the selected model ({model}).", category="model")
    if response.status_code == 429:
        return AnthropicIntegrationError("Anthropic rate-limited the request. Try again shortly.", category="rate_limit")
    if response.status_code == 400:
        return AnthropicIntegrationError("Anthropic rejected the reporting request. Check the date range and credential type.", category="configuration")
    if response.status_code >= 500:
        return AnthropicIntegrationError("Anthropic is temporarily unavailable. Try again shortly.", category="provider")
    return AnthropicIntegrationError("Anthropic could not complete the request.", category="provider")


def _request_json(url: str, key: str, *, params: list[tuple[str, str]] | None = None, beta: bool = False, timeout: float = 30.0) -> dict[str, Any]:
    if not key or not key.strip():
        raise AnthropicIntegrationError("An Anthropic credential is required.", category="configuration")
    headers = {"x-api-key": key, "anthropic-version": ANTHROPIC_API_VERSION, "content-type": "application/json"}
    if beta:
        headers["anthropic-beta"] = ANTHROPIC_ANALYTICS_BETA
    response = None
    for attempt in range(3):
        try:
            response = httpx.get(url, headers=headers, params=params or [], timeout=timeout)
        except httpx.TimeoutException as exc:
            if attempt == 2:
                raise AnthropicIntegrationError("Anthropic request timed out. Try again.", category="network") from exc
            time.sleep(0.5 * (attempt + 1))
            continue
        except httpx.RequestError as exc:
            if attempt == 2:
                raise AnthropicIntegrationError("Anthropic could not be reached from the backend.", category="network") from exc
            time.sleep(0.5 * (attempt + 1))
            continue
        if response.status_code not in (429, 500, 502, 503, 504) or attempt == 2:
            break
        retry_after = response.headers.get("retry-after")
        try:
            delay = min(max(float(retry_after or "0.5"), 0.1), 5.0)
        except ValueError:
            delay = 0.5 * (attempt + 1)
        time.sleep(delay)
    assert response is not None
    if response.is_error:
        raise _error_for_response(response)
    try:
        payload = response.json()
    except ValueError as exc:
        raise AnthropicIntegrationError("Anthropic returned an unexpected response.", category="provider") from exc
    if not isinstance(payload, dict):
        raise AnthropicIntegrationError("Anthropic returned an unexpected response.", category="provider")
    return payload


def verify_anthropic_api_key(api_key: str, model: str, *, timeout: float = 30.0) -> dict[str, Any]:
    if not api_key or not api_key.strip():
        raise AnthropicIntegrationError("An Anthropic API key is required.", category="configuration")
    if not model or not model.strip():
        raise AnthropicIntegrationError("An Anthropic model is required.", category="configuration")
    body = {"model": model, "max_tokens": 1, "messages": [{"role": "user", "content": "Reply with the single word OK."}]}
    try:
        response = httpx.post(ANTHROPIC_MESSAGES_URL, headers={"x-api-key": api_key, "anthropic-version": ANTHROPIC_API_VERSION, "content-type": "application/json"}, json=body, timeout=timeout)
    except httpx.TimeoutException as exc:
        raise AnthropicIntegrationError("Anthropic verification timed out. Try again.", category="network") from exc
    except httpx.RequestError as exc:
        raise AnthropicIntegrationError("Anthropic could not be reached from the backend.", category="network") from exc
    if response.is_error:
        raise _error_for_response(response, model)
    try:
        payload = response.json()
    except ValueError as exc:
        raise AnthropicIntegrationError("Anthropic returned an unexpected verification response.", category="provider") from exc
    if not isinstance(payload, dict) or payload.get("type") != "message":
        raise AnthropicIntegrationError("Anthropic returned an unexpected verification response.", category="provider")
    return {"model": model, "request_id": response.headers.get("request-id")}


def _parse_date(value: str, name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise AnthropicIntegrationError(f"{name} must use YYYY-MM-DD format.", category="configuration") from exc


def validate_reporting_range(start_date: str, end_date: str) -> tuple[datetime, datetime]:
    start = _parse_date(start_date, "Start date")
    end = _parse_date(end_date, "End date")
    today = datetime.now(timezone.utc).date()
    earliest = max(date(2026, 1, 1), today - timedelta(days=365))
    if start < earliest or end <= start or end > today + timedelta(days=1):
        raise AnthropicIntegrationError("Anthropic reporting dates must be within the last 365 days, start on or after 2026-01-01, and cover at least one day.", category="configuration")
    if (end - start).days > 31:
        raise AnthropicIntegrationError("Anthropic reporting supports a maximum 31-day range per request.", category="configuration")
    return datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc), datetime.combine(end, datetime.min.time(), tzinfo=timezone.utc)


def verify_anthropic_reporting_credential(admin_key: str, *, timeout: float = 30.0) -> dict[str, Any]:
    now = datetime.now(timezone.utc).date()
    start = now - timedelta(days=1)
    payload = _request_json(f"{ANTHROPIC_ANALYTICS_BASE_URL}/usage", admin_key, params=[("starting_at", f"{start.isoformat()}T00:00:00Z"), ("ending_at", f"{now.isoformat()}T00:00:00Z"), ("limit", "1")], beta=True, timeout=timeout)
    return {"data_refreshed_at": payload.get("data_refreshed_at")}


def _paged_report(url: str, admin_key: str, params: list[tuple[str, str]], *, timeout: float = 45.0) -> dict[str, Any]:
    rows: list[Any] = []
    page: str | None = None
    refreshed_at: Any = None
    for _ in range(100):
        query = list(params)
        if page:
            query.append(("page", page))
        payload = _request_json(url, admin_key, params=query, beta=True, timeout=timeout)
        data = payload.get("data")
        if isinstance(data, list):
            rows.extend(data)
        refreshed_at = payload.get("data_refreshed_at")
        if not payload.get("has_more") or not payload.get("next_page"):
            break
        page = str(payload["next_page"])
    else:
        raise AnthropicIntegrationError("Anthropic returned too many report pages.", category="provider")
    return {"data": rows, "data_refreshed_at": refreshed_at}


def get_anthropic_usage_and_cost(admin_key: str, start_date: str, end_date: str) -> dict[str, Any]:
    start, end = validate_reporting_range(start_date, end_date)
    start_value = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_value = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    usage_params = [("starting_at", start_value), ("ending_at", end_value), ("time_bucket_width", "1d"), ("group_by[]", "model"), ("order_by", "time"), ("order", "asc"), ("limit", "31")]
    cost_params = [("starting_at", start_value), ("ending_at", end_value), ("time_bucket_width", "1d"), ("group_by[]", "model"), ("group_by[]", "cost_type"), ("group_by[]", "token_type"), ("order_by", "time"), ("order", "asc"), ("limit", "31")]
    usage = _paged_report(f"{ANTHROPIC_ANALYTICS_BASE_URL}/usage", admin_key, usage_params)
    cost = _paged_report(f"{ANTHROPIC_ANALYTICS_BASE_URL}/cost", admin_key, cost_params)
    return {"start_date": start_date, "end_date": end_date, "usage": usage, "cost": cost, "synced_at": datetime.now(timezone.utc).isoformat()}


def as_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")
