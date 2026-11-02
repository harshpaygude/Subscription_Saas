from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.auth.dependencies import get_current_user
from app.database.models import ManualSpendEntry, Subscription, User
from app.database.session import get_db
from app.subscriptions.schemas import ManualSpendCreate, ManualSpendResponse, SubscriptionCreate, SubscriptionResponse, SubscriptionUpdate
from app.subscriptions.service import aggregate_subscriptions, normalize_monthly, upcoming

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])

def owned(db: Session, current_user: User, subscription_id: int) -> Subscription:
    item = db.query(Subscription).filter(Subscription.id == subscription_id, Subscription.organization_id == current_user.organization_id).first()
    if not item: raise HTTPException(404, "Subscription not found.")
    return item

@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def create_subscription(payload: SubscriptionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = Subscription(**payload.model_dump(), organization_id=current_user.organization_id, user_id=current_user.id, source="manual")
    db.add(item); db.commit(); db.refresh(item); return item

@router.get("", response_model=list[SubscriptionResponse])
def list_subscriptions(provider: Optional[str] = None, status_filter: Optional[str] = Query(default=None, alias="status"), billing_interval: Optional[str] = None, renewal_before: Optional[date] = None, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Subscription).filter(Subscription.organization_id == current_user.organization_id)
    if provider: query = query.filter(Subscription.provider == provider)
    if status_filter: query = query.filter(Subscription.status == status_filter.upper())
    if billing_interval: query = query.filter(Subscription.billing_interval == billing_interval)
    if renewal_before: query = query.filter(Subscription.next_renewal_date <= renewal_before)
    return query.order_by(Subscription.next_renewal_date.asc().nullslast(), Subscription.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

@router.get("/summary")
def subscription_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    items = db.query(Subscription).filter(Subscription.organization_id == current_user.organization_id).all()
    totals = aggregate_subscriptions(items)
    return {"active_count": sum(item.status == "ACTIVE" for item in items), "cancelled_count": sum(item.status == "CANCELLED" for item in items), "totals_by_currency": {key: str(value) for key, value in totals.items()}}

@router.get("/renewals", response_model=list[SubscriptionResponse])
def upcoming_renewals(days: int = Query(30, ge=1, le=366), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    start = date.today(); end = start + timedelta(days=days)
    return [item for item in db.query(Subscription).filter(Subscription.organization_id == current_user.organization_id).order_by(Subscription.next_renewal_date.asc()).all() if upcoming(item, start, end)]

@router.get("/spend")
def monthly_spend(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    subscriptions = db.query(Subscription).filter(Subscription.organization_id == current_user.organization_id, Subscription.status == "ACTIVE").all()
    manual = db.query(ManualSpendEntry).filter(ManualSpendEntry.organization_id == current_user.organization_id).all()
    rows = []
    totals: dict[str, Decimal] = {}
    for item in subscriptions:
        normalized = normalize_monthly(item.amount, item.billing_interval)
        if normalized is None: continue
        totals[item.currency] = totals.get(item.currency, Decimal("0")) + normalized
        rows.append({"service": item.provider, "name": item.name, "monthly_spend": str(normalized), "currency": item.currency, "billing_source": item.source, "billing_period": item.billing_interval, "last_updated": item.updated_at, "status": "available"})
    for item in manual:
        normalized = normalize_monthly(item.amount, item.billing_interval)
        if normalized is None: continue
        totals[item.currency] = totals.get(item.currency, Decimal("0")) + normalized
        rows.append({"service": item.provider, "name": item.provider, "monthly_spend": str(normalized), "currency": item.currency, "billing_source": "manual", "billing_period": item.period_start, "last_updated": item.updated_at, "status": "available"})
    return {"totals_by_currency": {key: str(value) for key, value in totals.items()}, "services": rows}

@router.post("/manual-spend", response_model=ManualSpendResponse, status_code=status.HTTP_201_CREATED)
def create_manual_spend(payload: ManualSpendCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = db.query(ManualSpendEntry).filter(ManualSpendEntry.organization_id == current_user.organization_id, ManualSpendEntry.provider == payload.provider, ManualSpendEntry.period_start == payload.period_start).first()
    if item: item.__dict__.update(payload.model_dump()); db.commit(); db.refresh(item); return item
    item = ManualSpendEntry(**payload.model_dump(), organization_id=current_user.organization_id, user_id=current_user.id)
    db.add(item); db.commit(); db.refresh(item); return item

@router.get("/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription(subscription_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)): return owned(db, current_user, subscription_id)

@router.patch("/{subscription_id}", response_model=SubscriptionResponse)
def update_subscription(subscription_id: int, payload: SubscriptionUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = owned(db, current_user, subscription_id)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(item, key, value)
    db.commit(); db.refresh(item); return item

@router.post("/{subscription_id}/cancel", response_model=SubscriptionResponse)
def cancel_subscription(subscription_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = owned(db, current_user, subscription_id); item.status = "CANCELLED"; item.cancellation_date = date.today(); db.commit(); db.refresh(item); return item

@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(subscription_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = owned(db, current_user, subscription_id); db.delete(item); db.commit(); return None
