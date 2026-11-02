"""OpenAI verification, organization usage and cost retrieval."""
from typing import Any, Dict, List, Optional

import httpx


OPENAI_MODELS_URL = "https://api.openai.com/v1/models"
OPENAI_USAGE_URL = "https://api.openai.com/v1/organization/usage/completions"
OPENAI_COSTS_URL = "https://api.openai.com/v1/organization/costs"
OPENAI_TIMEOUT_SECONDS = 12.0


class OpenAIIntegrationError(Exception):
    def __init__(self, message: str, *, category: str = "service"):
        super().__init__(message)
        self.category = category


def _error_for_response(response: httpx.Response) -> OpenAIIntegrationError:
    if response.status_code == 401:
        return OpenAIIntegrationError(
            "OpenAI rejected this API key. Check that it is active and belongs to the intended organization.",
            category="authentication",
        )
    if response.status_code == 403:
        return OpenAIIntegrationError(
            "The OpenAI API key is valid but is not authorized for this request.",
            category="authorization",
        )
    if response.status_code == 429:
        return OpenAIIntegrationError(
            "OpenAI rate-limited the verification request. Wait a moment and try again.",
            category="rate_limit",
        )
    if response.status_code >= 500:
        return OpenAIIntegrationError(
            "OpenAI is temporarily unavailable. Try again shortly.", category="provider"
        )
    return OpenAIIntegrationError(
        "OpenAI could not verify this API key. Check the key and its permissions.",
        category="provider",
    )


def verify_openai_api_key(api_key: str) -> Dict[str, Any]:
    """Verify a key with the read-only List Models endpoint."""
    if not api_key or not api_key.strip():
        raise OpenAIIntegrationError("An OpenAI API key is required.", category="configuration")

    try:
        response = httpx.get(
            OPENAI_MODELS_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=OPENAI_TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException as exc:
        raise OpenAIIntegrationError(
            "The OpenAI verification request timed out. Try again.", category="network"
        ) from exc
    except httpx.RequestError as exc:
        raise OpenAIIntegrationError(
            "OpenAI could not be reached. Check the backend network connection.", category="network"
        ) from exc

    if response.is_error:
        raise _error_for_response(response)

    try:
        payload = response.json()
        models = payload.get("data", [])
    except (ValueError, AttributeError) as exc:
        raise OpenAIIntegrationError(
            "OpenAI returned an unexpected verification response.", category="provider"
        ) from exc

    if not isinstance(models, list):
        raise OpenAIIntegrationError(
            "OpenAI returned an unexpected model response.", category="provider"
        )

    return {"model_count": len(models)}


def _request_page(url: str, api_key: str, params: List[tuple[str, Any]]) -> Dict[str, Any]:
    try:
        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            params=params,
            timeout=OPENAI_TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException as exc:
        raise OpenAIIntegrationError("The OpenAI usage request timed out. Try again.", category="network") from exc
    except httpx.RequestError as exc:
        raise OpenAIIntegrationError("OpenAI could not be reached. Check the backend network connection.", category="network") from exc

    if response.is_error:
        raise _error_for_response(response)
    try:
        payload = response.json()
    except (ValueError, AttributeError) as exc:
        raise OpenAIIntegrationError("OpenAI returned an unexpected analytics response.", category="provider") from exc
    if not isinstance(payload, dict):
        raise OpenAIIntegrationError("OpenAI returned an unexpected analytics response.", category="provider")
    return payload


def _paged_request(url: str, api_key: str, params: List[tuple[str, Any]]) -> List[Dict[str, Any]]:
    """Fetch all organization analytics pages without retaining raw provider payloads."""
    results: List[Dict[str, Any]] = []
    page: Optional[str] = None
    for _ in range(100):
        request_params = list(params)
        if page:
            request_params.append(("page", page))
        payload = _request_page(url, api_key, request_params)
        data = payload.get("data", [])
        if not isinstance(data, list):
            raise OpenAIIntegrationError("OpenAI returned an unexpected analytics response.", category="provider")
        results.extend(bucket for bucket in data if isinstance(bucket, dict))
        if not payload.get("has_more") or not payload.get("next_page"):
            return results
        page = str(payload["next_page"])
    raise OpenAIIntegrationError("OpenAI returned too many analytics pages to process safely.", category="provider")


def get_openai_usage(api_key: str, start_time: int, end_time: int) -> Dict[str, Any]:
    if end_time <= start_time:
        raise OpenAIIntegrationError("The usage date range is invalid.", category="configuration")
    buckets = _paged_request(
        OPENAI_USAGE_URL,
        api_key,
        [("start_time", start_time), ("end_time", end_time), ("bucket_width", "1d"), ("limit", 31), ("group_by", "model"), ("group_by", "project_id")],
    )
    daily: List[Dict[str, Any]] = []
    model_totals: Dict[str, Dict[str, Any]] = {}
    total_input = total_output = total_requests = 0
    request_count_available = True
    for bucket in buckets:
        day_input = day_output = day_requests = 0
        for result in bucket.get("results", []) or []:
            if not isinstance(result, dict):
                continue
            input_tokens = int(result.get("input_tokens") or 0)
            output_tokens = int(result.get("output_tokens") or 0)
            requests = result.get("num_model_requests")
            if requests is None:
                request_count_available = False
            else:
                requests = int(requests or 0)
                day_requests += requests
            day_input += input_tokens
            day_output += output_tokens
            model = result.get("model") or "Unspecified model"
            model_item = model_totals.setdefault(model, {"model": model, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "requests": 0})
            model_item["input_tokens"] += input_tokens
            model_item["output_tokens"] += output_tokens
            model_item["total_tokens"] += input_tokens + output_tokens
            if requests is not None:
                model_item["requests"] += requests
        total_input += day_input
        total_output += day_output
        total_requests += day_requests
        daily.append({"start_time": int(bucket.get("start_time", 0)), "end_time": int(bucket.get("end_time", 0)), "input_tokens": day_input, "output_tokens": day_output, "total_tokens": day_input + day_output, "requests": day_requests if request_count_available else None})
    if not request_count_available:
        for day in daily:
            day["requests"] = None
        for model_item in model_totals.values():
            model_item["requests"] = None
    return {"daily": daily, "by_model": list(model_totals.values()), "total_input_tokens": total_input, "total_output_tokens": total_output, "total_tokens": total_input + total_output, "requests": total_requests if request_count_available else None}


def get_openai_costs(api_key: str, start_time: int, end_time: int) -> Dict[str, Any]:
    if end_time <= start_time:
        raise OpenAIIntegrationError("The cost date range is invalid.", category="configuration")
    buckets = _paged_request(
        OPENAI_COSTS_URL,
        api_key,
        [("start_time", start_time), ("end_time", end_time), ("bucket_width", "1d"), ("limit", 180), ("group_by", "project_id")],
    )
    daily: List[Dict[str, Any]] = []
    by_project: Dict[str, Dict[str, Any]] = {}
    total = 0.0
    currency: Optional[str] = None
    for bucket in buckets:
        day_total = 0.0
        for result in bucket.get("results", []) or []:
            if not isinstance(result, dict):
                continue
            amount = result.get("amount") or {}
            value = float(amount.get("value") or 0) if isinstance(amount, dict) else 0.0
            result_currency = str(amount.get("currency") or "usd").lower() if isinstance(amount, dict) else "usd"
            currency = currency or result_currency
            day_total += value
            project = result.get("project_id") or "Unspecified project"
            item = by_project.setdefault(project, {"project_id": project, "amount": 0.0, "currency": result_currency})
            item["amount"] += value
        total += day_total
        daily.append({"start_time": int(bucket.get("start_time", 0)), "end_time": int(bucket.get("end_time", 0)), "amount": day_total, "currency": currency or "usd"})
    return {"daily": daily, "by_project": list(by_project.values()), "total": total, "currency": currency or "usd"}
