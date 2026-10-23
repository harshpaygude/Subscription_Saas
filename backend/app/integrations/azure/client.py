from datetime import date
from typing import Any
import httpx

ARM = "https://management.azure.com"
class AzureProviderError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None): self.status_code = status_code; super().__init__(message)
class AzureClient:
    def __init__(self, access_token: str, timeout: float = 20.0): self.headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}; self.timeout = timeout
    def _request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        try: response = httpx.request(method, url, headers=self.headers, timeout=self.timeout, **kwargs)
        except httpx.HTTPError as exc: raise AzureProviderError("Azure request failed or timed out") from exc
        if response.status_code >= 400:
            if response.status_code in (401, 403): raise AzureProviderError("Azure authorization does not permit this operation", response.status_code)
            if response.status_code == 429: raise AzureProviderError("Azure rate limit reached; retry later", response.status_code)
            raise AzureProviderError("Azure returned an error", response.status_code)
        return response.json()
    def _paged(self, url: str) -> list[dict[str, Any]]:
        items = []
        while url: payload = self._request("GET", url); items.extend(payload.get("value", [])); url = payload.get("nextLink", "")
        return items
    def subscriptions(self): return self._paged(f"{ARM}/subscriptions?api-version=2022-12-01")
    def resources(self, subscription_id: str): return self._paged(f"{ARM}/subscriptions/{subscription_id}/resources?api-version=2021-04-01")
    def cost(self, subscription_id: str, start: date, end: date):
        if start >= end: raise ValueError("start must be before end")
        body = {"type": "ActualCost", "timeframe": "Custom", "timePeriod": {"from": start.isoformat(), "to": end.isoformat()}, "dataset": {"granularity": "Daily", "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}}}}
        return self._request("POST", f"{ARM}/subscriptions/{subscription_id}/providers/Microsoft.CostManagement/query?api-version=2023-03-01", json=body)
