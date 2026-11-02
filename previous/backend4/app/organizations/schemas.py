from datetime import datetime

from pydantic import BaseModel, Field


class OrganizationCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
    )


class OrganizationResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
