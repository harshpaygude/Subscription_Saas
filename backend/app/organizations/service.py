from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.database.models import Organization
from app.organizations.schemas import OrganizationCreate


def create_organization(
    db: Session,
    organization_data: OrganizationCreate,
) -> Organization:

    organization = Organization(
        name=organization_data.name,
        created_at=datetime.utcnow(),
    )

    db.add(organization)
    db.commit()
    db.refresh(organization)

    return organization


def get_organization(
    db: Session,
    organization_id: int,
) -> Optional[Organization]:

    return (
        db.query(Organization)
        .filter(Organization.id == organization_id)
        .first()
    )
