from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

class ShadowItEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    vendor_name: str
    category: str
    monthly_amount: float
    currency: str
    transaction_count: int
    first_seen: Optional[date]
    last_seen: Optional[date]
    risk_level: str
    status: str
    raw_descriptions: Optional[str]
    created_at: datetime
    updated_at: datetime

class ShadowItStatsResponse(BaseModel):
    total_monthly_spend: float
    currency: str
    vendor_count: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    discovered_count: int
    approved_count: int
    blocked_count: int

class ShadowItUploadResponse(BaseModel):
    processed_transactions: int
    matched_vendors_count: int
    new_entries_created: int
    entries_updated: int
    total_monthly_spend_discovered: float
    currency: str
    entries: List[ShadowItEntryResponse]
