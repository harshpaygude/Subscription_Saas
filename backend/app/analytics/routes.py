from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.auth.dependencies import get_current_user
from app.database.models import Asset, AssetAssignment, AuditLog, Department, Organization, Subscription, SubscriptionAssignment, User
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
    assets = db.query(Asset).filter(Asset.organization_id == current_user.organization_id).all()
    active_asset_assignments = db.query(AssetAssignment).filter(AssetAssignment.organization_id == current_user.organization_id, AssetAssignment.status == "ACTIVE").count()
    active_license_assignments = db.query(SubscriptionAssignment).filter(SubscriptionAssignment.organization_id == current_user.organization_id, SubscriptionAssignment.status == "ACTIVE").count()
    return {
        "active_subscriptions": len(active),
        "cancelled_subscriptions": sum(item.status == "CANCELLED" for item in items),
        "upcoming_renewals": sum(upcoming(item, start, end) for item in items),
        "totals_by_currency": {key: str(value) for key, value in aggregate_subscriptions(active).items()},
        "by_provider": by_provider,
        "departments": db.query(Department).filter(Department.organization_id == current_user.organization_id, Department.is_active.is_(True)).count(),
        "assets": {"total": len(assets), "assigned": active_asset_assignments, "available": sum(item.status == "AVAILABLE" for item in assets)},
        "license_utilization": active_license_assignments,
        "historical": [],
        "historical_note": "Historical snapshots begin when collection is implemented; no past values are fabricated.",
    }


@router.get("/audit-export")
def audit_export(
    range_type: str = Query("monthly", description="1year, 6months, monthly, or custom"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    if range_type == "1year":
        calc_start = today - timedelta(days=365)
        calc_end = today
    elif range_type == "6months":
        calc_start = today - timedelta(days=180)
        calc_end = today
    elif range_type == "monthly":
        calc_start = today - timedelta(days=30)
        calc_end = today
    else:
        try:
            calc_start = date.fromisoformat(start_date) if start_date else (today - timedelta(days=30))
        except Exception:
            calc_start = today - timedelta(days=30)
        try:
            calc_end = date.fromisoformat(end_date) if end_date else today
        except Exception:
            calc_end = today

    if calc_start > calc_end:
        calc_start, calc_end = calc_end, calc_start

    start_dt = datetime.combine(calc_start, time.min)
    end_dt = datetime.combine(calc_end, time.max)

    logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.organization_id == current_user.organization_id,
            AuditLog.created_at >= start_dt,
            AuditLog.created_at <= end_dt,
        )
        .order_by(AuditLog.created_at.desc())
        .limit(500)
        .all()
    )

    items = db.query(Subscription).filter(Subscription.organization_id == current_user.organization_id).all()
    active = [item for item in items if item.status == "ACTIVE"]

    by_provider: dict[str, dict[str, str]] = {}
    for item in active:
        normalized = normalize_monthly(item.amount, item.billing_interval)
        if normalized is None:
            continue
        row = by_provider.setdefault(item.provider, {"currency": item.currency, "monthly_spend": "0.000000", "data_status": "available"})
        if row["currency"] != item.currency:
            row["data_status"] = "multiple_currencies"
        row["monthly_spend"] = str((Decimal(row["monthly_spend"]) + normalized).quantize(Decimal("0.000001")))

    log_entries = []
    for log in logs:
        actor = db.query(User).filter(User.id == log.actor_id).first()
        log_entries.append({
            "id": log.id,
            "created_at": log.created_at.isoformat(),
            "actor_email": actor.email if actor else "system",
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "details": log.details,
        })

    org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()

    return {
        "organization_id": current_user.organization_id,
        "organization_name": org.name if org else "UniSora Workspace",
        "generated_at": datetime.utcnow().isoformat(),
        "range_type": range_type,
        "start_date": calc_start.isoformat(),
        "end_date": calc_end.isoformat(),
        "summary": {
            "active_subscriptions": len(active),
            "cancelled_subscriptions": sum(item.status == "CANCELLED" for item in items),
            "upcoming_renewals": sum(upcoming(item, calc_start, calc_end) for item in items),
            "totals_by_currency": {key: str(value) for key, value in aggregate_subscriptions(active).items()},
        },
        "by_provider": by_provider,
        "subscriptions": [
            {
                "id": s.id,
                "provider": s.provider,
                "currency": s.currency,
                "amount": str(s.amount),
                "billing_interval": s.billing_interval,
                "status": s.status,
                "renewal_date": s.renewal_date.isoformat() if s.renewal_date else None,
            }
            for s in items
        ],
        "audit_logs": log_entries,
    }


