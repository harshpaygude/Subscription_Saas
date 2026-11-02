"""Explicitly local-only, non-persistent manual ARM-token support."""
from threading import Lock


class ManualTokenStore:
    def __init__(self) -> None:
        self._tokens: dict[str, str] = {}
        self._selected: dict[str, set[str]] = {}
        self._lock = Lock()

    def set(self, user_id: str, token: str) -> None:
        with self._lock:
            self._tokens[user_id] = token
            self._selected.pop(user_id, None)

    def get(self, user_id: str) -> str | None:
        with self._lock:
            return self._tokens.get(user_id)

    def clear(self, user_id: str) -> None:
        with self._lock:
            self._tokens.pop(user_id, None)
            self._selected.pop(user_id, None)

    def select(self, user_id: str, subscription_ids: set[str]) -> None:
        with self._lock:
            self._selected[user_id] = set(subscription_ids)

    def selected(self, user_id: str) -> set[str]:
        with self._lock:
            return set(self._selected.get(user_id, set()))


manual_tokens = ManualTokenStore()
