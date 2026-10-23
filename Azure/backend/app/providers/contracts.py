"""Small provider contracts used at application boundaries.

Concrete Azure infrastructure can be replaced by test doubles without making
HTTP routes depend on a particular cloud SDK or transport implementation.
"""
from datetime import date
from typing import Any, Protocol


class SubscriptionReader(Protocol):
    def subscriptions(self) -> list[dict[str, Any]]: ...


class ResourceReader(Protocol):
    def resources(self, subscription_id: str) -> list[dict[str, Any]]: ...


class CostReader(Protocol):
    def cost(self, subscription_id: str, start: date, end: date) -> dict[str, Any]: ...
