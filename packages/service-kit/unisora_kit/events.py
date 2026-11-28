"""Versioned domain events, transactional outbox, and idempotent consumer helpers."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import httpx
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from unisora_kit.logging import get_correlation_id, get_logger
from unisora_kit.security import create_internal_service_token

logger = get_logger("unisora_kit.events")


@dataclass(frozen=True)
class DomainEvent:
    event_id: str
    event_type: str
    event_version: str
    source_service: str
    occurred_at: str
    correlation_id: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_domain_event(
    *,
    event_type: str,
    source_service: str,
    payload: dict[str, Any],
    event_version: str = "1.0",
    correlation_id: str | None = None,
) -> DomainEvent:
    return DomainEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        event_version=event_version,
        source_service=source_service,
        occurred_at=datetime.now(timezone.utc).isoformat(),
        correlation_id=correlation_id or get_correlation_id() or str(uuid.uuid4()),
        payload=payload,
    )


class OutboxRecordMixin:
    """Mixin for each service's local transactional outbox_events table."""

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    event_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    target_url: Mapped[str] = mapped_column(String(512), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING", index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    dispatched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class ProcessedEventMixin:
    """Mixin for idempotent consumer deduplication."""

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class OutboxDispatcher:
    """Dispatches pending outbox events with retry and dead-letter transition."""

    def __init__(
        self,
        *,
        source_service: str,
        internal_secret: str,
        max_attempts: int = 3,
        timeout: float = 3.0,
        transport: Optional[Callable[[str, dict, dict], int]] = None,
    ):
        self.source_service = source_service
        self.internal_secret = internal_secret
        self.max_attempts = max_attempts
        self.timeout = timeout
        self._transport = transport

    def enqueue(
        self,
        db: Session,
        model_cls: type,
        *,
        event: DomainEvent,
        target_url: str,
    ) -> Any:
        record = model_cls(
            event_id=event.event_id,
            event_type=event.event_type,
            event_version=event.event_version,
            target_url=target_url,
            payload_json=json.dumps(event.to_dict(), default=str),
            correlation_id=event.correlation_id,
            status="PENDING",
            attempts=0,
        )
        db.add(record)
        return record

    def flush_pending(self, db: Session, model_cls: type, limit: int = 50) -> int:
        pending = (
            db.query(model_cls)
            .filter(model_cls.status == "PENDING")
            .order_by(model_cls.id.asc())
            .limit(limit)
            .all()
        )
        delivered = 0
        for row in pending:
            if not row.target_url:
                row.status = "SKIPPED"
                continue
            body = json.loads(row.payload_json)
            headers = {
                "Content-Type": "application/json",
                "X-Request-ID": row.correlation_id or "",
                "X-Internal-Service-Token": create_internal_service_token(
                    self.internal_secret, self.source_service
                ),
            }
            try:
                if self._transport is not None:
                    code = self._transport(row.target_url, body, headers)
                else:
                    resp = httpx.post(row.target_url, json=body, headers=headers, timeout=self.timeout)
                    code = resp.status_code
                if 200 <= code < 300:
                    row.status = "DELIVERED"
                    row.dispatched_at = datetime.utcnow()
                    delivered += 1
                else:
                    self._mark_retry_or_dead_letter(row, f"HTTP {code}")
            except Exception as exc:
                self._mark_retry_or_dead_letter(row, str(exc)[:300])
        db.commit()
        return delivered

    def _mark_retry_or_dead_letter(self, row: Any, error_message: str) -> None:
        row.attempts += 1
        row.last_error = error_message
        if row.attempts >= self.max_attempts:
            row.status = "DEAD_LETTER"
            logger.warning(
                "outbox.dead_letter",
                extra={"extra_fields": {"event_id": row.event_id, "event_type": row.event_type}},
            )
