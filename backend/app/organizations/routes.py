from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.organizations.schemas import (
    OrganizationCreate,
    OrganizationResponse,
)
from app.organizations.service import (
    create_organization,
    get_organization,
)
from app.auth.dependencies import get_current_user
from app.database.models import User


router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"],
)


@router.post(
    "",
    response_model=OrganizationResponse,
)
async def create_organization_endpoint(
    organization_data: OrganizationCreate,
    db: Session = Depends(get_db),
):
    return create_organization(
        db,
        organization_data,
    )


@router.get(
    "/{organization_id}",
    response_model=OrganizationResponse,
)
async def get_organization_endpoint(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Organization not found")

    organization = get_organization(
        db,
        organization_id,
    )

    if organization is None:
        raise HTTPException(
            status_code=404,
            detail="Organization not found",
        )

    return organization
