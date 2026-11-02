from typing import Any
import httpx

GEMINI_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

class GeminiIntegrationError(Exception):
    def __init__(self, message: str, *, category: str = "service"):
        super().__init__(message)
        self.category = category

def verify_gemini_api_key(api_key: str) -> dict[str, Any]:
    if not api_key or not api_key.strip():
        raise GeminiIntegrationError("A Gemini API key is required.", category="configuration")
    try:
        response = httpx.get(GEMINI_MODELS_URL, headers={"x-goog-api-key": api_key}, timeout=12.0)
    except httpx.TimeoutException as exc:
        raise GeminiIntegrationError("Gemini verification timed out. Try again.", category="network") from exc
    except httpx.RequestError as exc:
        raise GeminiIntegrationError("Gemini could not be reached. Check the backend network connection.", category="network") from exc
    if response.status_code in (401, 403):
        raise GeminiIntegrationError("Gemini rejected this API key. Check that it is active and has access to the Generative Language API.", category="authentication")
    if response.status_code == 429:
        raise GeminiIntegrationError("Gemini rate-limited the verification request. Try again shortly.", category="rate_limit")
    if response.status_code >= 500:
        raise GeminiIntegrationError("Gemini is temporarily unavailable. Try again shortly.", category="provider")
    if response.is_error:
        raise GeminiIntegrationError("Gemini could not verify this API key. Check the key and API access.", category="provider")
    try:
        models = response.json().get("models", [])
    except (ValueError, AttributeError) as exc:
        raise GeminiIntegrationError("Gemini returned an unexpected verification response.", category="provider") from exc
    if not isinstance(models, list):
        raise GeminiIntegrationError("Gemini returned an unexpected model response.", category="provider")
    return {"model_count": len(models)}

def generate_gemini_content(api_key: str, model: str, contents: list[dict[str, Any]], generation_config: dict[str, Any] | None = None) -> dict[str, Any]:
    if not model or not contents:
        raise GeminiIntegrationError("A Gemini model and at least one content message are required.", category="configuration")
    try:
        response = httpx.post(f"{GEMINI_API_BASE}/{model}:generateContent", headers={"x-goog-api-key": api_key, "Content-Type": "application/json"}, json={"contents": contents, **({"generationConfig": generation_config} if generation_config else {})}, timeout=60.0)
    except httpx.TimeoutException as exc:
        raise GeminiIntegrationError("Gemini generation timed out. Try again.", category="network") from exc
    except httpx.RequestError as exc:
        raise GeminiIntegrationError("Gemini could not be reached.", category="network") from exc
    if response.status_code in (401, 403):
        raise GeminiIntegrationError("Gemini rejected this API key or request permissions.", category="authentication")
    if response.status_code == 429:
        raise GeminiIntegrationError("Gemini rate-limited this request.", category="rate_limit")
    if response.is_error:
        raise GeminiIntegrationError("Gemini could not complete the request.", category="provider")
    try:
        payload = response.json()
    except ValueError as exc:
        raise GeminiIntegrationError("Gemini returned an unexpected response.", category="provider") from exc
    usage = payload.get("usageMetadata") or {}
    return {"response": payload, "input_tokens": int(usage.get("promptTokenCount") or 0), "output_tokens": int(usage.get("candidatesTokenCount") or 0), "total_tokens": int(usage.get("totalTokenCount") or 0)}
