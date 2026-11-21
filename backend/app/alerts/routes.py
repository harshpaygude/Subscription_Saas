from datetime import date, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from app.auth.dependencies import get_current_user
from app.database.models import Alert, Subscription, User, NotificationPreference
from app.database.session import get_db
from app.notifications.service import send_email, send_whatsapp, build_renewal_email_html

router = APIRouter(prefix="/alerts", tags=["Alerts"])

class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    provider: Optional[str]
    subscription_id: Optional[int]
    category: str
    severity: str
    title: str
    description: str
    is_read: bool
    is_resolved: bool
    created_at: object
    updated_at: object

class AlertCreate(BaseModel):
    category: str = Field(min_length=1, max_length=40)
    severity: str = Field(default="info", min_length=1, max_length=20)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    provider: Optional[str] = None
    subscription_id: Optional[int] = None
    dedupe_key: str = Field(min_length=1, max_length=255)

class NotificationPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    user_id: int
    email_enabled: bool
    whatsapp_enabled: bool
    whatsapp_number: Optional[str]
    notify_days_before: str

class NotificationPreferenceUpdate(BaseModel):
    email_enabled: bool
    whatsapp_enabled: bool
    whatsapp_number: Optional[str] = None
    notify_days_before: str = "30,7,1"

class TestNotificationRequest(BaseModel):
    channel: str = Field(default="email") # "email", "whatsapp", or "both"
    custom_recipient: Optional[str] = None

def create_or_update_renewal_alerts(db: Session, user: User) -> None:
    today = date.today()
    items = (
        db.query(Subscription)
        .filter(
            Subscription.organization_id == user.organization_id,
            Subscription.status == "ACTIVE",
        )
        .all()
    )
    for item in items:
        if item.next_renewal_date is None:
            continue
        days_left = (item.next_renewal_date - today).days
        if days_left < -7:
            # Skip past renewals older than a week
            continue

        raw_type = (getattr(item, "renewal_type", None) or "AUTOPAY").upper()
        note_text = (item.note or "").lower()
        if "manual" in note_text or "invoice" in note_text:
            is_autopay = "auto" in raw_type.lower() and "manual" not in raw_type.lower()
        else:
            is_autopay = "MANUAL" not in raw_type

        mode_label = "Auto-Pay" if is_autopay else "Manual Invoice"
        cost_str = f" ({item.currency} {float(item.amount):,.2f})" if item.amount is not None else ""

        # Milestone 1: 30 Days Prior Notice (7 < days_left <= 30)
        if 7 < days_left <= 30:
            key_30d = f"renewal-30d:{item.id}:{item.next_renewal_date.isoformat()}"
            exists_30d = (
                db.query(Alert)
                .filter(Alert.organization_id == user.organization_id, Alert.dedupe_key == key_30d)
                .first()
            )
            if not exists_30d:
                if is_autopay:
                    desc = (
                        f"Auto-Pay Renewal in {days_left} days: Your {item.name} subscription "
                        f"({item.plan or 'Standard'}) is scheduled to automatically charge{cost_str} "
                        f"on {item.next_renewal_date.isoformat()}. Review license seat allocations and payment card prior to renewal execution."
                    )
                else:
                    desc = (
                        f"Manual Renewal Notice ({days_left} days remaining): Your {item.name} contract "
                        f"({item.plan or 'Standard'}) expires on {item.next_renewal_date.isoformat()}{cost_str}. "
                        f"Submit purchase order or contact vendor to approve payment and prevent service disruption."
                    )
                db.add(
                    Alert(
                        organization_id=user.organization_id,
                        user_id=user.id,
                        provider=item.provider,
                        subscription_id=item.id,
                        category="renewal",
                        severity="info",
                        title=f"{item.name}: 30-Day Renewal Notice ({mode_label})",
                        description=desc,
                        dedupe_key=key_30d,
                    )
                )

        # Milestone 2: 7 Days Prior Warning Notice (1 < days_left <= 7)
        if 1 < days_left <= 7:
            key_7d = f"renewal-7d:{item.id}:{item.next_renewal_date.isoformat()}"
            exists_7d = (
                db.query(Alert)
                .filter(Alert.organization_id == user.organization_id, Alert.dedupe_key == key_7d)
                .first()
            )
            if not exists_7d:
                if is_autopay:
                    desc = (
                        f"Auto-Pay Warning: {item.name} ({item.plan or 'Standard'}) will auto-charge{cost_str} "
                        f"in {days_left} days on {item.next_renewal_date.isoformat()}. Check payment source before execution."
                    )
                else:
                    desc = (
                        f"Upcoming Contract Expiry ({days_left} days left): {item.name} contract expires "
                        f"on {item.next_renewal_date.isoformat()}{cost_str}. Process purchase order to maintain active licenses."
                    )
                db.add(
                    Alert(
                        organization_id=user.organization_id,
                        user_id=user.id,
                        provider=item.provider,
                        subscription_id=item.id,
                        category="renewal",
                        severity="warning",
                        title=f"{item.name}: 7-Day Renewal Warning ({mode_label})",
                        description=desc,
                        dedupe_key=key_7d,
                    )
                )

        # Milestone 3: 1 Day Prior Urgent Alert (0 <= days_left <= 1)
        if 0 <= days_left <= 1:
            key_1d = f"renewal-1d:{item.id}:{item.next_renewal_date.isoformat()}"
            exists_1d = (
                db.query(Alert)
                .filter(Alert.organization_id == user.organization_id, Alert.dedupe_key == key_1d)
                .first()
            )
            if not exists_1d:
                timing = "tomorrow" if days_left == 1 else "today"
                if is_autopay:
                    desc = (
                        f"Final Auto-Pay Notice: {item.name} will be automatically charged{cost_str} "
                        f"{timing} ({item.next_renewal_date.isoformat()}). Ensure your company payment method has sufficient funds to avoid billing issues."
                    )
                    title = f"URGENT: {item.name} Auto-Renews {timing.capitalize()} ({mode_label})"
                else:
                    desc = (
                        f"Urgent Renewal Action: {item.name} subscription contract expires "
                        f"{timing} ({item.next_renewal_date.isoformat()}){cost_str}. Settle vendor invoice or process purchase order immediately to maintain uninterrupted access."
                    )
                    title = f"ACTION REQUIRED: {item.name} Renews {timing.capitalize()} ({mode_label})"

                db.add(
                    Alert(
                        organization_id=user.organization_id,
                        user_id=user.id,
                        provider=item.provider,
                        subscription_id=item.id,
                        category="renewal",
                        severity="warning",
                        title=title,
                        description=desc,
                        dedupe_key=key_1d,
                    )
                )
    db.commit()

@router.post("", response_model=AlertResponse, status_code=201)
def create_alert(payload: AlertCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    existing = db.query(Alert).filter(Alert.organization_id == current_user.organization_id, Alert.dedupe_key == payload.dedupe_key).first()
    if existing: return existing
    alert = Alert(**payload.model_dump(), organization_id=current_user.organization_id, user_id=current_user.id)
    db.add(alert); db.commit(); db.refresh(alert); return alert

@router.get("", response_model=list[AlertResponse])
def list_alerts(
    category: Optional[str] = None,
    severity: Optional[str] = None,
    read: Optional[bool] = None,
    resolved: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    create_or_update_renewal_alerts(db, current_user)
    query = db.query(Alert).filter(Alert.organization_id == current_user.organization_id)
    if category: query = query.filter(Alert.category == category)
    if severity: query = query.filter(Alert.severity == severity)
    if read is not None: query = query.filter(Alert.is_read == read)
    if resolved is not None: query = query.filter(Alert.is_resolved == resolved)
    return query.order_by(Alert.created_at.desc()).all()

@router.get("/unread-count")
def unread_count(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    create_or_update_renewal_alerts(db, current_user)
    return {"count": db.query(Alert).filter(Alert.organization_id == current_user.organization_id, Alert.is_read.is_(False), Alert.is_resolved.is_(False)).count()}

@router.get("/preferences", response_model=NotificationPreferenceResponse)
def get_preferences(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pref = db.query(NotificationPreference).filter(
        NotificationPreference.organization_id == current_user.organization_id,
        NotificationPreference.user_id == current_user.id
    ).first()
    if not pref:
        pref = NotificationPreference(
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            email_enabled=True,
            whatsapp_enabled=False,
            whatsapp_number=None,
            notify_days_before="30,7,1"
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref

@router.put("/preferences", response_model=NotificationPreferenceResponse)
def update_preferences(payload: NotificationPreferenceUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pref = db.query(NotificationPreference).filter(
        NotificationPreference.organization_id == current_user.organization_id,
        NotificationPreference.user_id == current_user.id
    ).first()
    if not pref:
        pref = NotificationPreference(
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            **payload.model_dump()
        )
        db.add(pref)
    else:
        pref.email_enabled = payload.email_enabled
        pref.whatsapp_enabled = payload.whatsapp_enabled
        pref.whatsapp_number = payload.whatsapp_number
        pref.notify_days_before = payload.notify_days_before
    db.commit()
    db.refresh(pref)
    return pref

@router.post("/notify/test")
def send_test_notification(payload: TestNotificationRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pref = db.query(NotificationPreference).filter(
        NotificationPreference.organization_id == current_user.organization_id,
        NotificationPreference.user_id == current_user.id
    ).first()
    
    target_email = payload.custom_recipient if payload.channel == "email" and payload.custom_recipient else current_user.email
    target_wa = payload.custom_recipient if payload.channel == "whatsapp" and payload.custom_recipient else (pref.whatsapp_number if pref else None)
    
    results: Dict[str, Any] = {}

    if payload.channel in ("email", "both"):
        html = build_renewal_email_html(
            subscription_name="Amazon Web Services (Production)",
            plan="Enterprise Cloud Compute",
            days_left=7,
            renewal_date=(date.today() + timedelta(days=7)).isoformat(),
            amount_str="USD $2,450.00",
            mode_label="Auto-Pay",
        )
        results["email"] = send_email(
            to_email=target_email,
            subject="[TEST] UniSora Renewal Notice: AWS Cloud Contract Renews in 7 Days",
            html_content=html,
            text_content="This is a test renewal alert from UniSora Subscription Management.",
        )

    if payload.channel in ("whatsapp", "both"):
        if not target_wa:
            results["whatsapp"] = {"delivered": False, "message": "No WhatsApp phone number configured. Set your number in notification preferences."}
        else:
            msg = "🔔 *UniSora Test Alert*: Amazon Web Services is scheduled to auto-renew on " + (date.today() + timedelta(days=7)).isoformat() + " ($2,450.00). Manage in dashboard."
            results["whatsapp"] = send_whatsapp(target_wa, msg)

    return {"status": "completed", "results": results}

@router.post("/dispatch-due")
def dispatch_due_alerts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    create_or_update_renewal_alerts(db, current_user)
    pref = db.query(NotificationPreference).filter(
        NotificationPreference.organization_id == current_user.organization_id,
        NotificationPreference.user_id == current_user.id
    ).first()

    email_active = pref.email_enabled if pref else True
    wa_active = pref.whatsapp_enabled if pref else False
    wa_num = pref.whatsapp_number if pref else None

    unresolved = (
        db.query(Alert)
        .filter(
            Alert.organization_id == current_user.organization_id,
            Alert.category == "renewal",
            Alert.is_resolved.is_(False),
        )
        .all()
    )

    dispatched = 0
    for alert in unresolved[:5]: # Batch cap for safety
        if email_active and current_user.email:
            send_email(
                to_email=current_user.email,
                subject=f"🔔 UniSora Renewal Notice: {alert.title}",
                html_content=f"<div style='font-family:sans-serif;'><h2>{alert.title}</h2><p>{alert.description}</p><p><a href='https://unisora.in/dashboard/alerts'>Open UniSora Dashboard</a></p></div>",
            )
            dispatched += 1
        if wa_active and wa_num:
            send_whatsapp(wa_num, f"🔔 *{alert.title}*\n{alert.description}")

    return {"dispatched_count": dispatched, "total_active_alerts": len(unresolved)}

def owned(db: Session, user: User, alert_id: int) -> Alert:
    alert = db.query(Alert).filter(Alert.id == alert_id, Alert.organization_id == user.organization_id).first()
    if not alert: raise HTTPException(404, "Alert not found.")
    return alert

@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)): return owned(db, current_user, alert_id)

@router.post("/{alert_id}/read", response_model=AlertResponse)
def mark_read(alert_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    alert = owned(db, current_user, alert_id); alert.is_read = True; db.commit(); db.refresh(alert); return alert

@router.post("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(alert_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    alert = owned(db, current_user, alert_id); alert.is_resolved = True; alert.is_read = True; db.commit(); db.refresh(alert); return alert
