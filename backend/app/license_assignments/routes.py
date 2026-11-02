from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.policies import require_admin
from app.database.models import Subscription, SubscriptionAssignment, SubscriptionLicense, User
from app.database.session import get_db
from app.license_assignments.schemas import LicenseCreate, LicenseResponse, SubscriptionAssignmentCreate, SubscriptionAssignmentResponse
from app.license_assignments.service import assign_license, release_license

router = APIRouter(tags=["License assignments"])


@router.post("/subscriptions/{subscription_id}/licenses", response_model=LicenseResponse, status_code=status.HTTP_201_CREATED)
def create_license(subscription_id: int, payload: LicenseCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id, Subscription.organization_id == current_user.organization_id).first()
    if not subscription: raise HTTPException(404, "Subscription not found.")
    item = SubscriptionLicense(organization_id=current_user.organization_id, subscription_id=subscription.id, **payload.model_dump())
    db.add(item); db.commit(); db.refresh(item); return item


@router.get("/subscriptions/{subscription_id}/licenses", response_model=list[LicenseResponse])
def list_licenses(subscription_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id, Subscription.organization_id == current_user.organization_id).first()
    if not subscription: raise HTTPException(404, "Subscription not found.")
    return db.query(SubscriptionLicense).filter(SubscriptionLicense.subscription_id == subscription_id, SubscriptionLicense.organization_id == current_user.organization_id).order_by(SubscriptionLicense.id.asc()).all()


@router.post("/subscription-assignments", response_model=SubscriptionAssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(payload: SubscriptionAssignmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    subscription = db.query(Subscription).filter(Subscription.id == payload.subscription_id, Subscription.organization_id == current_user.organization_id).first()
    if not subscription: raise HTTPException(404, "Subscription not found.")
    license_item = db.query(SubscriptionLicense).filter(SubscriptionLicense.id == payload.license_id, SubscriptionLicense.organization_id == current_user.organization_id).first() if payload.license_id else None
    try:
        assignment = assign_license(db, current_user, subscription, license_item, payload.model_dump(exclude={"subscription_id", "license_id"}) | {"user_id": payload.user_id})
        assignment.subscription_id = subscription.id; assignment.license_id = license_item.id if license_item else None
        db.commit(); db.refresh(assignment); return assignment
    except ValueError as exc:
        db.rollback(); raise HTTPException(409, str(exc))


@router.get("/subscription-assignments", response_model=list[SubscriptionAssignmentResponse])
def list_assignments(subscription_id: int | None = None, user_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(SubscriptionAssignment).filter(SubscriptionAssignment.organization_id == current_user.organization_id)
    if subscription_id: query = query.filter(SubscriptionAssignment.subscription_id == subscription_id)
    if user_id: query = query.filter(SubscriptionAssignment.user_id == user_id)
    return query.order_by(SubscriptionAssignment.assigned_at.desc()).all()


@router.post("/subscription-assignments/{assignment_id}/release", response_model=SubscriptionAssignmentResponse)
def release_assignment(assignment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    item = db.query(SubscriptionAssignment).filter(SubscriptionAssignment.id == assignment_id, SubscriptionAssignment.organization_id == current_user.organization_id, SubscriptionAssignment.status == "ACTIVE").first()
    if not item: raise HTTPException(404, "Active subscription assignment not found.")
    release_license(db, current_user, item); db.commit(); db.refresh(item); return item

