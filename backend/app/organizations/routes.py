from datetime import datetime, date
import io
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.policies import require_admin
from app.auth.security import hash_password
from app.database.models import (
    Asset,
    AssetAssignment,
    Department,
    DepartmentMembership,
    EmployeeLifecycle,
    Organization,
    User,
)
from app.database.session import get_db
from app.organizations.excel_import import parse_excel_workbook
from app.organizations.schemas import (
    OnboardingSubmit,
    OrganizationCreate,
    OrganizationProfileUpdate,
    OrganizationResponse,
)
from app.organizations.service import create_organization, get_organization

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_organization(
    payload: OrganizationCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_organization(db, payload.name)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization with this name already exists",
        )


@router.get(
    "/me",
    response_model=OrganizationResponse,
)
def get_current_user_organization(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org = get_organization(db, current_user.organization_id)
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return org


@router.get(
    "/{organization_id}",
    response_model=OrganizationResponse,
)
def get_organization_by_id(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access organizations outside your workspace",
        )
    org = get_organization(db, organization_id)
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return org


@router.get(
    "/me/onboarding-status",
    response_model=dict,
)
async def get_onboarding_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check if the current user's organization has completed initial onboarding."""
    org = get_organization(db, current_user.organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    return {
        "organization_id": org.id,
        "organization_name": org.name,
        "onboarding_completed": bool(org.onboarding_completed),
        "onboarding_completed_at": (
            org.onboarding_completed_at.isoformat()
            if org.onboarding_completed_at
            else None
        ),
    }


@router.patch(
    "/me/profile",
    response_model=OrganizationResponse,
)
async def update_organization_profile(
    payload: OrganizationProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the company profile for the current user's organization."""
    org = get_organization(db, current_user.organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(org, field, value)

    try:
        db.commit()
        db.refresh(org)
    except Exception:
        db.rollback()
        raise

    return org


@router.post(
    "/me/onboarding",
    response_model=OrganizationResponse,
)
async def submit_onboarding(
    payload: OnboardingSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit company onboarding: save profile + departments + employees + assets + mark completed."""
    require_admin(current_user)

    org = get_organization(db, current_user.organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    # 1. Update company profile
    for field, value in payload.company.model_dump(exclude_unset=True).items():
        setattr(org, field, value)

    # 2. Create departments (skip duplicates gracefully)
    dept_map: dict[str, Department] = {}
    # Cache existing departments
    for d in db.query(Department).filter(Department.organization_id == org.id).all():
        dept_map[d.name.lower()] = d

    for dept_input in payload.departments:
        key = dept_input.name.strip().lower()
        if key not in dept_map:
            dept = Department(
                organization_id=org.id,
                name=dept_input.name.strip(),
                description=dept_input.description,
            )
            db.add(dept)
            dept_map[key] = dept

    db.flush()
    # Refresh map with persisted department IDs
    for key, d in list(dept_map.items()):
        if not d.id:
            db.refresh(d)

    # 3. Create employees if provided
    created_users: dict[str, User] = {}
    for emp in payload.employees:
        email_clean = str(emp.email).strip().lower()
        existing_user = (
            db.query(User)
            .filter(User.organization_id == org.id, User.email.ilike(email_clean))
            .first()
        )
        if not existing_user:
            emp_user = User(
                email=email_clean,
                display_name=emp.full_name.strip(),
                employee_id=emp.employee_id.strip() if emp.employee_id else None,
                phone_number=emp.phone_number.strip() if emp.phone_number else None,
                password_hash=hash_password(secrets.token_urlsafe(24)),
                organization_id=org.id,
                role="MEMBER",
            )
            db.add(emp_user)
            db.flush()
            created_users[email_clean] = emp_user
            if emp.employee_id:
                created_users[emp.employee_id.strip().lower()] = emp_user

            # Joining date
            effective_date = date.today()
            if emp.joining_date:
                try:
                    effective_date = date.fromisoformat(str(emp.joining_date)[:10])
                except Exception:
                    pass

            # Create lifecycle record
            db.add(
                EmployeeLifecycle(
                    organization_id=org.id,
                    user_id=emp_user.id,
                    status="ACTIVE",
                    joined_at=effective_date,
                )
            )

            # Assign department membership if matching
            if emp.department_name:
                dept_match = dept_map.get(emp.department_name.strip().lower())
                if dept_match:
                    db.add(
                        DepartmentMembership(
                            organization_id=org.id,
                            department_id=dept_match.id,
                            user_id=emp_user.id,
                            effective_from=effective_date,
                        )
                    )
        else:
            created_users[email_clean] = existing_user
            if existing_user.employee_id:
                created_users[existing_user.employee_id.strip().lower()] = existing_user

    # 4. Create IT assets if provided
    for asset_input in payload.assets:
        tag_clean = asset_input.asset_tag.strip()
        existing_asset = (
            db.query(Asset)
            .filter(Asset.organization_id == org.id, Asset.asset_tag == tag_clean)
            .first()
        )
        if not existing_asset:
            cost_val: Optional[float] = None
            if asset_input.purchase_cost:
                try:
                    cost_val = float(str(asset_input.purchase_cost).replace("$", "").replace(",", "").strip())
                except Exception:
                    pass

            new_asset = Asset(
                organization_id=org.id,
                asset_tag=tag_clean,
                name=asset_input.name.strip(),
                asset_type=asset_input.asset_type.strip() if asset_input.asset_type else "Laptop",
                manufacturer=asset_input.manufacturer.strip() if asset_input.manufacturer else None,
                model=asset_input.model.strip() if asset_input.model else None,
                serial_number=asset_input.serial_number.strip() if asset_input.serial_number else None,
                purchase_cost=cost_val,
                currency=asset_input.currency.strip().upper() if asset_input.currency else "USD",
                location=asset_input.location.strip() if asset_input.location else None,
                status="AVAILABLE",
            )
            db.add(new_asset)
            db.flush()

            # Assign to employee if assigned_to specified
            if asset_input.assigned_to:
                target_key = asset_input.assigned_to.strip().lower()
                target_user = created_users.get(target_key)
                if not target_user:
                    target_user = (
                        db.query(User)
                        .filter(
                            User.organization_id == org.id,
                            (User.email.ilike(target_key)) | (User.employee_id == target_key),
                        )
                        .first()
                    )
                if target_user:
                    new_asset.status = "ASSIGNED"
                    db.add(
                        AssetAssignment(
                            organization_id=org.id,
                            asset_id=new_asset.id,
                            user_id=target_user.id,
                            assigned_by=current_user.id,
                            status="ACTIVE",
                            handover_notes="Imported via initial company onboarding Excel",
                        )
                    )

    # 5. Mark onboarding completed
    org.onboarding_completed = True
    org.onboarding_completed_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(org)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A department or asset with this identifier already exists.")
    except Exception:
        db.rollback()
        raise

    return org


@router.post(
    "/me/onboarding/parse-excel",
    response_model=dict,
)
async def parse_onboarding_excel(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Parse an uploaded Excel workbook and return a comprehensive preview without saving."""
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are accepted.")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10 MB limit
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10 MB.")

    preview = parse_excel_workbook(content)

    return {
        "valid": preview.valid,
        "company": {
            "company_name": preview.company.company_name if preview.company else None,
            "legal_name": preview.company.legal_name if preview.company else None,
            "industry": preview.company.industry if preview.company else None,
            "company_size": preview.company.company_size if preview.company else None,
            "website": preview.company.website if preview.company else None,
            "company_email": preview.company.company_email if preview.company else None,
            "company_phone": preview.company.company_phone if preview.company else None,
            "country": preview.company.country if preview.company else None,
            "state": preview.company.state if preview.company else None,
            "city": preview.company.city if preview.company else None,
            "address": preview.company.address if preview.company else None,
            "postal_code": preview.company.postal_code if preview.company else None,
            "tax_registration_number": preview.company.tax_registration_number if preview.company else None,
        } if preview.company else None,
        "departments": [{"name": d.name, "description": d.description} for d in preview.departments],
        "employees": [
            {
                "employee_id": e.employee_id,
                "full_name": e.full_name,
                "email": e.email,
                "phone_number": e.phone_number,
                "department_name": e.department_name,
                "joining_date": str(e.joining_date) if e.joining_date else None,
            }
            for e in preview.employees
        ],
        "assets": [
            {
                "asset_tag": a.asset_tag,
                "name": a.name,
                "asset_type": a.asset_type,
                "manufacturer": a.manufacturer,
                "model": a.model,
                "serial_number": a.serial_number,
                "purchase_cost": a.purchase_cost,
                "currency": a.currency,
                "location": a.location,
                "assigned_to": a.assigned_to,
            }
            for a in preview.assets
        ],
        "errors": preview.errors,
        "warnings": preview.warnings,
        "department_count": len(preview.departments),
        "employee_count": len(preview.employees),
        "asset_count": len(preview.assets),
    }


@router.get(
    "/me/onboarding/excel-template",
)
async def download_excel_template(
    current_user: User = Depends(get_current_user),
):
    """Return a comprehensive downloadable Excel template with Company, Departments, Employees, and Assets sheets."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    except ImportError:
        raise HTTPException(status_code=500, detail="openpyxl not installed.")

    wb = openpyxl.Workbook()

    header_font = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="10B981", end_color="10B981", fill_type="solid")  # Emerald brand
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # ── 1. Company sheet ──────────────────────────────────────────────────────────
    ws_company = wb.active
    ws_company.title = "Company"
    company_headers = [
        "company_name", "legal_name", "industry", "company_size",
        "website", "company_email", "company_phone",
        "country", "state", "city", "address", "postal_code", "tax_registration_number",
    ]
    for col, header in enumerate(company_headers, 1):
        cell = ws_company.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center
        ws_company.column_dimensions[cell.column_letter].width = 22

    sample_company = [
        "UniSora Technologies", "UniSora Global Technologies Inc.", "Technology & Software", "51–200 employees",
        "https://unisora.io", "contact@unisora.io", "+1 (555) 019-2834",
        "United States", "California", "San Francisco", "500 Howard Street, Suite 400", "94105", "US-94-3829102",
    ]
    for col, val in enumerate(sample_company, 1):
        ws_company.cell(row=2, column=col, value=val)

    # ── 2. Departments sheet ──────────────────────────────────────────────────────
    ws_dept = wb.create_sheet("Departments")
    dept_headers = ["department_name", "description"]
    for col, header in enumerate(dept_headers, 1):
        cell = ws_dept.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center
        ws_dept.column_dimensions[cell.column_letter].width = 30

    sample_depts = [
        ("Engineering", "Core software development, cloud infrastructure, and DevOps"),
        ("Product & Design", "UI/UX product design, research, and technical roadmaps"),
        ("Finance & Operations", "Accounting, budget planning, payroll, and compliance"),
        ("People Operations", "Talent recruitment, team onboarding, and HR management"),
        ("Sales & Marketing", "Revenue growth, digital marketing, and client partnerships"),
        ("Customer Success", "Technical support, account management, and client onboarding"),
    ]
    for row, (name, desc) in enumerate(sample_depts, 2):
        ws_dept.cell(row=row, column=1, value=name)
        ws_dept.cell(row=row, column=2, value=desc)

    # ── 3. Employees sheet ────────────────────────────────────────────────────────
    ws_emp = wb.create_sheet("Employees")
    emp_headers = ["employee_id", "full_name", "email", "phone_number", "department_name", "joining_date"]
    for col, header in enumerate(emp_headers, 1):
        cell = ws_emp.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center
        ws_emp.column_dimensions[cell.column_letter].width = 24

    sample_emps = [
        ("EMP-101", "Alex Morgan", "alex.morgan@unisora.test", "+1 (555) 011-2001", "Engineering", "2024-01-15"),
        ("EMP-102", "Elena Rostova", "elena.rostova@unisora.test", "+1 (555) 011-2002", "Product & Design", "2024-02-01"),
        ("EMP-103", "Marcus Vance", "marcus.vance@unisora.test", "+1 (555) 011-2003", "Finance & Operations", "2024-02-15"),
        ("EMP-104", "Sophia Chen", "sophia.chen@unisora.test", "+1 (555) 011-2004", "People Operations", "2024-03-01"),
        ("EMP-105", "David Kim", "david.kim@unisora.test", "+1 (555) 011-2005", "Sales & Marketing", "2024-03-15"),
        ("EMP-106", "Rachel Taylor", "rachel.taylor@unisora.test", "+1 (555) 011-2006", "Customer Success", "2024-04-01"),
    ]
    for row, emp in enumerate(sample_emps, 2):
        for col, val in enumerate(emp, 1):
            ws_emp.cell(row=row, column=col, value=val)

    # ── 4. IT Assets sheet ────────────────────────────────────────────────────────
    ws_asset = wb.create_sheet("Assets")
    asset_headers = [
        "asset_tag", "name", "asset_type", "manufacturer", "model",
        "serial_number", "purchase_cost", "currency", "location", "assigned_to",
    ]
    for col, header in enumerate(asset_headers, 1):
        cell = ws_asset.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center
        ws_asset.column_dimensions[cell.column_letter].width = 24

    sample_assets = [
        ("LT-101", "MacBook Pro 16 M3 Max", "Laptop", "Apple", "MacBookPro18,1", "C02G8491MD6R", "3499.00", "USD", "San Francisco HQ", "alex.morgan@unisora.test"),
        ("LT-102", "MacBook Air 15 M3", "Laptop", "Apple", "MacBookAir15,2", "C02G9102KD4T", "1699.00", "USD", "San Francisco HQ", "elena.rostova@unisora.test"),
        ("LT-103", "ThinkPad X1 Carbon Gen 11", "Laptop", "Lenovo", "21HM000EUS", "PF482910J", "1850.00", "USD", "San Francisco HQ", "marcus.vance@unisora.test"),
        ("MN-201", "Dell UltraSharp 27 4K", "Monitor", "Dell", "U2723QE", "CN-0K791X", "579.00", "USD", "Desk 4A", "alex.morgan@unisora.test"),
        ("PH-301", "iPhone 15 Pro Enterprise", "Mobile Phone", "Apple", "A3102", "DN7K9012PQ", "999.00", "USD", "Mobile Fleet", "sophia.chen@unisora.test"),
        ("MN-202", "LG 34 Curved UltraWide", "Monitor", "LG", "34WN80C-B", "204NTQJ482", "549.00", "USD", "Storage Room B", ""),
    ]
    for row, asset in enumerate(sample_assets, 2):
        for col, val in enumerate(asset, 1):
            ws_asset.cell(row=row, column=col, value=val)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=unisora_onboarding_template.xlsx"},
    )
