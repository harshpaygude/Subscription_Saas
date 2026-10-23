"""Small, server-side Anthropic Messages API client.

The API key never leaves this module's request boundary and is never included
in raised error messages.
"""
from typing import Any

import httpx

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"


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


def _error_for_response(response: httpx.Response, model: str) -> AnthropicIntegrationError:
    provider_message = _provider_message(response).lower()
    if response.status_code == 401:
        return AnthropicIntegrationError("Anthropic rejected this API key.", category="authentication")
    if response.status_code == 403:
        return AnthropicIntegrationError("This Anthropic key is not authorized for the requested operation.", category="authorization")
    if response.status_code == 404 or "model" in provider_message and "not found" in provider_message:
        return AnthropicIntegrationError(f"Anthropic does not support the selected model ({model}).", category="model")
    if response.status_code == 429:
        return AnthropicIntegrationError("Anthropic rate-limited the verification request. Try again shortly.", category="rate_limit")
    if response.status_code in (402, 409) or any(word in provider_message for word in ("credit", "billing", "balance")):
        return AnthropicIntegrationError("Anthropic rejected the request because billing or credits require attention.", category="billing")
    if response.status_code >= 500:
        return AnthropicIntegrationError("Anthropic is temporarily unavailable. Try again shortly.", category="provider")
    return AnthropicIntegrationError("Anthropic could not verify this key and model.", category="provider")


def verify_anthropic_api_key(api_key: str, model: str, *, timeout: float = 30.0) -> dict[str, Any]:
    if not api_key or not api_key.strip():
        raise AnthropicIntegrationError("An Anthropic API key is required.", category="configuration")
    if not model or not model.strip():
        raise AnthropicIntegrationError("An Anthropic model is required.", category="configuration")

    body = {
        "model": model,
        "max_tokens": 1,
        "messages": [{"role": "user", "content": "Reply with the single word OK."}],
    }
    try:
        response = httpx.post(
            ANTHROPIC_MESSAGES_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": ANTHROPIC_API_VERSION,
                "content-type": "application/json",
            },
            json=body,
            timeout=timeout,
        )
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
