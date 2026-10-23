from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from app.auth.dependencies import get_current_user
from app.database.models import Alert, Subscription, User
from app.database.session import get_db

router = APIRouter(prefix="/alerts", tags=["Alerts"])

class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; organization_id: int; provider: Optional[str]; subscription_id: Optional[int]; category: str; severity: str; title: str; description: str; is_read: bool; is_resolved: bool; created_at: object; updated_at: object

class AlertCreate(BaseModel):
    category: str = Field(min_length=1, max_length=40); severity: str = Field(default="info", min_length=1, max_length=20); title: str = Field(min_length=1, max_length=255); description: str = Field(min_length=1); provider: Optional[str] = None; subscription_id: Optional[int] = None; dedupe_key: str = Field(min_length=1, max_length=255)

def create_or_update_renewal_alerts(db: Session, user: User) -> None:
    start = date.today(); end = start + timedelta(days=30)
    items = db.query(Subscription).filter(Subscription.organization_id == user.organization_id, Subscription.status == "ACTIVE").all()
    for item in items:
        if item.next_renewal_date is None or not (start <= item.next_renewal_date <= end): continue
        key = f"renewal:{item.id}:{item.next_renewal_date.isoformat()}"
        if db.query(Alert).filter(Alert.organization_id == user.organization_id, Alert.dedupe_key == key).first(): continue
        db.add(Alert(organization_id=user.organization_id, user_id=user.id, provider=item.provider, subscription_id=item.id, category="renewal", severity="info", title=f"{item.name} renews soon", description=f"{item.name} is scheduled to renew on {item.next_renewal_date.isoformat()}.", dedupe_key=key))
    db.commit()

@router.post("", response_model=AlertResponse, status_code=201)
def create_alert(payload: AlertCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    existing = db.query(Alert).filter(Alert.organization_id == current_user.organization_id, Alert.dedupe_key == payload.dedupe_key).first()
    if existing: return existing
    alert = Alert(**payload.model_dump(), organization_id=current_user.organization_id, user_id=current_user.id)
    db.add(alert); db.commit(); db.refresh(alert); return alert

@router.get("", response_model=list[AlertResponse])
def list_alerts(category: Optional[str] = None, severity: Optional[str] = None, read: Optional[bool] = None, resolved: Optional[bool] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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
