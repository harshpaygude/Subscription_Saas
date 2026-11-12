from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session
from app.auth.dependencies import get_current_user
from app.auth.policies import require_admin
from app.database.models import Connection, ManualSpendEntry, Subscription, User
from app.database.session import get_db
from app.subscriptions.csv_import import generate_subscription_template_bytes, process_subscription_bulk_import
from app.subscriptions.schemas import ManualSpendCreate, ManualSpendResponse, SubscriptionCreate, SubscriptionResponse, SubscriptionUpdate
from app.subscriptions.service import aggregate_subscriptions, normalize_monthly, upcoming

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])

def owned(db: Session, current_user: User, subscription_id: int) -> Subscription:
    item = db.query(Subscription).filter(Subscription.id == subscription_id, Subscription.organization_id == current_user.organization_id).first()
    if not item: raise HTTPException(404, "Subscription not found.")
    return item

@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def create_subscription(payload: SubscriptionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    data = payload.model_dump()
    if data.get("renewal_type"):
        data["renewal_type"] = data["renewal_type"].upper()
    item = Subscription(**data, organization_id=current_user.organization_id, user_id=current_user.id, source="manual")
    db.add(item); db.commit(); db.refresh(item); return item

@router.post("/import-csv")
@router.post("/import")
async def import_subscriptions_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    filename = file.filename or "subscriptions.csv"
    try:
        return process_subscription_bulk_import(db, current_user, content, filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import error: {str(e)}")

@router.get("/sample-template")
def get_subscription_template(
    format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
    current_user: User = Depends(get_current_user),
):
    content, media_type, filename = generate_subscription_template_bytes(fmt=format)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@router.post("/seed-demo")
def seed_demo_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import os
    import secrets
    from decimal import Decimal
    from sqlalchemy import func
    from app.auth.security import hash_password
    from app.database.models import (
        Asset,
        AssetAssignment,
        Connection,
        Department,
        DepartmentMembership,
        EmployeeLifecycle,
        Subscription,
        User,
    )
    from app.organizations.excel_import import parse_excel_workbook

    cand_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "samples", "UniSora_Complete_SaaS_Demo_Dataset.xlsx")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", "public", "UniSora_Complete_SaaS_Demo_Dataset.xlsx")),
        os.path.abspath("samples/UniSora_Complete_SaaS_Demo_Dataset.xlsx"),
        os.path.abspath("../samples/UniSora_Complete_SaaS_Demo_Dataset.xlsx"),
    ]
    content = None
    for p in cand_paths:
        if os.path.exists(p):
            with open(p, "rb") as f:
                content = f.read()
            break

    if not content:
        content, _, _ = generate_subscription_template_bytes(fmt="xlsx")

    preview = parse_excel_workbook(content)
    org_id = current_user.organization_id
    created_dept_count = 0
    created_emp_count = 0
    created_asset_count = 0

    # 1. Seed Departments
    dept_map = {}
    for d_obj in db.query(Department).filter(Department.organization_id == org_id).all():
        dept_map[d_obj.name.strip().lower()] = d_obj

    for parsed_dept in preview.departments:
        key = parsed_dept.name.strip().lower()
        if key not in dept_map:
            new_dept = Department(
                organization_id=org_id,
                name=parsed_dept.name.strip(),
                description=parsed_dept.description,
                is_active=True,
            )
            db.add(new_dept)
            db.flush()
            dept_map[key] = new_dept
            created_dept_count += 1

    # 2. Seed Employees
    user_map = {}
    for u_obj in db.query(User).filter(User.organization_id == org_id).all():
        if u_obj.email:
            user_map[u_obj.email.strip().lower()] = u_obj
        if u_obj.employee_id:
            user_map[u_obj.employee_id.strip().lower()] = u_obj

    for parsed_emp in preview.employees:
        e_email = parsed_emp.email.strip().lower()
        e_id = parsed_emp.employee_id.strip().lower() if parsed_emp.employee_id else None
        target_user = user_map.get(e_email) or (user_map.get(e_id) if e_id else None)

        # Check global email conflict
        existing_global = db.query(User).filter(func.lower(User.email) == e_email).first()
        if existing_global:
            if existing_global.organization_id == org_id:
                target_user = existing_global
            else:
                e_email = f"{e_email.split('@')[0]}_{org_id}@unisora.test"
                target_user = user_map.get(e_email)

        j_date = None
        if parsed_emp.joining_date:
            try:
                j_date = date.fromisoformat(parsed_emp.joining_date[:10])
            except Exception:
                pass

        if not target_user:
            target_user = User(
                organization_id=org_id,
                email=e_email,
                display_name=parsed_emp.full_name.strip(),
                employee_id=parsed_emp.employee_id.strip() if parsed_emp.employee_id else None,
                phone_number=parsed_emp.phone_number.strip() if parsed_emp.phone_number else None,
                role="MEMBER",
                password_hash=hash_password(secrets.token_urlsafe(24)),
            )
            db.add(target_user)
            db.flush()
            created_emp_count += 1
            user_map[e_email] = target_user
            if e_id:
                user_map[e_id] = target_user
            # Map raw email so asset assignment can resolve it
            user_map[parsed_emp.email.strip().lower()] = target_user

            db.add(
                EmployeeLifecycle(
                    organization_id=org_id,
                    user_id=target_user.id,
                    status="ACTIVE",
                    joined_at=j_date,
                )
            )

        # Department assignment
        if parsed_emp.department_name:
            dept = dept_map.get(parsed_emp.department_name.strip().lower())
            if dept:
                mem = db.query(DepartmentMembership).filter(
                    DepartmentMembership.organization_id == org_id,
                    DepartmentMembership.department_id == dept.id,
                    DepartmentMembership.user_id == target_user.id,
                ).first()
                if not mem:
                    db.add(
                        DepartmentMembership(
                            organization_id=org_id,
                            department_id=dept.id,
                            user_id=target_user.id,
                            is_active=True,
                        )
                    )

    # 3. Seed IT Assets
    asset_map = {
        a.asset_tag.strip().lower(): a
        for a in db.query(Asset).filter(Asset.organization_id == org_id).all()
    }

    for parsed_asset in preview.assets:
        tag_key = parsed_asset.asset_tag.strip().lower()
        target_asset = asset_map.get(tag_key)

        cost_val = None
        if parsed_asset.purchase_cost:
            try:
                cost_val = Decimal(str(parsed_asset.purchase_cost).replace("$", "").replace(",", ""))
            except Exception:
                pass

        target_assigned_user = None
        if parsed_asset.assigned_to:
            a_key = parsed_asset.assigned_to.strip().lower()
            target_assigned_user = user_map.get(a_key)

        if not target_asset:
            target_asset = Asset(
                organization_id=org_id,
                asset_tag=parsed_asset.asset_tag.strip(),
                name=parsed_asset.name.strip(),
                asset_type=parsed_asset.asset_type.strip() if parsed_asset.asset_type else "Laptop",
                manufacturer=parsed_asset.manufacturer.strip() if parsed_asset.manufacturer else None,
                model=parsed_asset.model.strip() if parsed_asset.model else None,
                serial_number=parsed_asset.serial_number.strip() if parsed_asset.serial_number else None,
                purchase_cost=cost_val,
                currency=(parsed_asset.currency or "USD").strip().upper(),
                location=parsed_asset.location.strip() if parsed_asset.location else None,
                status="ASSIGNED" if target_assigned_user else "AVAILABLE",
            )
            db.add(target_asset)
            db.flush()
            asset_map[tag_key] = target_asset
            created_asset_count += 1

        if target_assigned_user and target_asset:
            existing_asmt = db.query(AssetAssignment).filter(
                AssetAssignment.organization_id == org_id,
                AssetAssignment.asset_id == target_asset.id,
                AssetAssignment.user_id == target_assigned_user.id,
                AssetAssignment.status == "ACTIVE",
            ).first()
            if not existing_asmt:
                db.add(
                    AssetAssignment(
                        organization_id=org_id,
                        asset_id=target_asset.id,
                        user_id=target_assigned_user.id,
                        assigned_by=current_user.id,
                        status="ACTIVE",
                        handover_notes=f"Assigned {target_asset.name} hardware custody via demo dataset seed.",
                    )
                )

    # 4. Seed Subscriptions
    result = process_subscription_bulk_import(db, current_user, content, "UniSora_Complete_SaaS_Demo_Dataset.xlsx")

    # 5. Seed sample active connections for integrations if not present
    sample_connections = [
        ("aws", "arn:aws:iam::123456789012:root", "region=us-east-1"),
        ("openai", "org-unisora-production-ai", None),
        ("anthropic", "ant-org-unisora-demo", None),
        ("gemini", "projects/unisora-demo-studio", None),
        ("azure", "unisora-cloud.onmicrosoft.com", None),
        ("github", "unisora-org", '{"plan": "enterprise", "seats": 50, "verified": true}'),
        ("slack", "T07A19B2Z", '{"team_name": "UniSora HQ", "users_count": 60, "verified": true}'),
        ("stripe", "acct_1NZs9k2eZvKYlo2C", '{"currency": "USD", "balance": 18450.00, "verified": true}'),
    ]
    for prov, tenant, scopes in sample_connections:
        existing = db.query(Connection).filter(
            Connection.organization_id == current_user.organization_id,
            Connection.provider == prov,
        ).first()
        if not existing:
            db.add(
                Connection(
                    organization_id=current_user.organization_id,
                    user_id=current_user.id,
                    provider=prov,
                    provider_tenant_id=tenant,
                    scopes=scopes,
                    status="ACTIVE",
                    last_verified_at=datetime.utcnow(),
                )
            )

    db.commit()
    msg = f"Demo dataset loaded successfully: {result.get('imported', 0)} SaaS subscriptions, {created_dept_count} departments, {created_emp_count} employees, and {created_asset_count} IT assets."
    return {
        "message": msg,
        "departments_created": created_dept_count,
        "employees_created": created_emp_count,
        "assets_created": created_asset_count,
        **result,
    }

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
    update_data = payload.model_dump(exclude_unset=True)
    if "renewal_type" in update_data and update_data["renewal_type"]:
        update_data["renewal_type"] = update_data["renewal_type"].upper()
    for key, value in update_data.items(): setattr(item, key, value)
    db.commit(); db.refresh(item); return item

@router.post("/{subscription_id}/cancel", response_model=SubscriptionResponse)
def cancel_subscription(subscription_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = owned(db, current_user, subscription_id); item.status = "CANCELLED"; item.cancellation_date = date.today(); db.commit(); db.refresh(item); return item

@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(subscription_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = owned(db, current_user, subscription_id); db.delete(item); db.commit(); return None
