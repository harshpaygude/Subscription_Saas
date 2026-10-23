from datetime import date, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.auth.dependencies import get_current_user
from app.database.models import Subscription, User
from app.database.session import get_db
from app.subscriptions.service import aggregate_subscriptions, normalize_monthly, upcoming

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/summary")
def analytics_summary(days: int = Query(30, ge=1, le=366), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    items = db.query(Subscription).filter(Subscription.organization_id == current_user.organization_id).all()
    active = [item for item in items if item.status == "ACTIVE"]
    by_provider: dict[str, dict[str, str]] = {}
    for item in active:
        normalized = normalize_monthly(item.amount, item.billing_interval)
        if normalized is None: continue
        row = by_provider.setdefault(item.provider, {"currency": item.currency, "monthly_spend": "0.000000", "data_status": "available"})
        if row["currency"] != item.currency: row["data_status"] = "multiple_currencies"
        row["monthly_spend"] = str((Decimal(row["monthly_spend"]) + normalized).quantize(Decimal("0.000001")))
    start = date.today(); end = start + timedelta(days=days)
    return {"active_subscriptions": len(active), "cancelled_subscriptions": sum(item.status == "CANCELLED" for item in items), "upcoming_renewals": sum(upcoming(item, start, end) for item in items), "totals_by_currency": {key: str(value) for key, value in aggregate_subscriptions(active).items()}, "by_provider": by_provider, "historical": [], "historical_note": "Historical snapshots begin when collection is implemented; no past values are fabricated."}

