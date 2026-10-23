"""Shared provider discovery endpoint used by the integration catalog UI."""

from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from app.integrations.catalog import get_provider_registry

router = APIRouter(prefix="/integrations", tags=["Integrations"])


class ProviderMetadataResponse(BaseModel):
    provider_id: str
    display_name: str
    description: str
    capabilities: List[str]


@router.get("/providers", response_model=List[ProviderMetadataResponse])
def list_providers() -> List[ProviderMetadataResponse]:
    return [ProviderMetadataResponse.model_validate(item.__dict__) for item in get_provider_registry().list_metadata()]
