"""Shared organization-scoped connection lifecycle operations."""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.database.models import Connection, User


class ConnectionService:
    def __init__(self, db: Session):
        self.db = db

    def get_for_organization(
        self, connection_id: int, user: User, provider: Optional[str] = None
    ) -> Connection:
        query = self.db.query(Connection).filter(
            Connection.id == connection_id,
            Connection.organization_id == user.organization_id,
        )
        if provider:
            query = query.filter(Connection.provider == provider)
        connection = query.first()
        if connection is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration connection not found.",
            )
        return connection

    def list_for_organization(self, user: User, provider: Optional[str] = None):
        query = self.db.query(Connection).filter(
            Connection.organization_id == user.organization_id
        )
        if provider:
            query = query.filter(Connection.provider == provider)
        return query.order_by(Connection.created_at.desc()).all()

    def disconnect(self, connection: Connection) -> None:
        self.db.delete(connection)
        self.db.commit()
