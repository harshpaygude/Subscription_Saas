import json
from typing import Optional

from sqlalchemy.orm import Session

from app.database.models import AuditLog, User


def record_audit(
    db: Session,
    actor: User,
    action: str,
    entity_type: str,
    entity_id: int,
    details: Optional[dict] = None,
) -> None:
    db.add(AuditLog(
        organization_id=actor.organization_id,
        actor_id=actor.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=json.dumps(details, default=str) if details else None,
    ))

