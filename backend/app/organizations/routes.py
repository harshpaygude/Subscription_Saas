import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.organizations.schemas import (
    OrganizationCreate,
    OrganizationProfileUpdate,
    OrganizationResponse,
    OnboardingSubmit,
)
from app.organizations.service import (
    create_organization,
    get_organization,
)
from app.auth.dependencies import get_current_user
from app.database.models import Department, User


router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"],
)


@router.post(
    "",
    response_model=OrganizationResponse,
)
async def create_organization_endpoint(
    organization_data: OrganizationCreate,
    db: Session = Depends(get_db),
):
    return create_organization(db, organization_data)


@router.get(
    "/{organization_id}",
    response_model=OrganizationResponse,
)
async def get_organization_endpoint(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Organization not found")

    organization = get_organization(db, organization_id)

    if organization is None:
        raise HTTPException(
            status_code=404,
            detail="Organization not found",
        )

    return organization


@router.get(
    "/me/onboarding-status",
    response_model=dict,
)
async def get_onboarding_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return whether onboarding has been completed for the current user's organization."""
    org = get_organization(db, current_user.organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {
        "onboarding_completed": org.onboarding_completed,
        "onboarding_completed_at": org.onboarding_completed_at.isoformat() if org.onboarding_completed_at else None,
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
    """Submit company onboarding: save profile + departments + mark as completed."""
    from app.auth.policies import require_admin
    require_admin(current_user)

    org = get_organization(db, current_user.organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Update company profile
    for field, value in payload.company.model_dump(exclude_unset=True).items():
        setattr(org, field, value)

    # Create departments (skip duplicates gracefully)
    for dept_input in payload.departments:
        existing = (
            db.query(Department)
            .filter(
                Department.organization_id == current_user.organization_id,
                Department.name == dept_input.name,
            )
            .first()
        )
        if not existing:
            dept = Department(
                organization_id=current_user.organization_id,
                name=dept_input.name,
                description=dept_input.description,
            )
            db.add(dept)

    # Mark onboarding completed
    org.onboarding_completed = True
    org.onboarding_completed_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(org)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A department with this name already exists.")
    except Exception:
        db.rollback()
        raise

    return org


from fastapi import UploadFile, File
from app.organizations.excel_import import parse_excel_workbook


@router.post(
    "/me/onboarding/parse-excel",
    response_model=dict,
)
async def parse_onboarding_excel(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Parse an uploaded Excel workbook and return a preview without saving."""
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
        "errors": preview.errors,
        "warnings": preview.warnings,
        "department_count": len(preview.departments),
        "employee_count": len(preview.employees),
    }


@router.get(
    "/me/onboarding/excel-template",
)
async def download_excel_template(
    current_user: User = Depends(get_current_user),
):
    """Return a downloadable Excel template for company onboarding."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        from fastapi.responses import StreamingResponse
    except ImportError:
        raise HTTPException(status_code=500, detail="openpyxl not installed.")

    wb = openpyxl.Workbook()

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="5146E5", end_color="5146E5", fill_type="solid")

    # ── Company sheet ──────────────────────────────────────────────────────────
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
        cell.alignment = Alignment(horizontal="center")
        ws_company.column_dimensions[cell.column_letter].width = 22

    # Sample data row
    sample_company = [
        "Acme Corporation", "Acme Corp Ltd.", "Technology", "51-200 employees",
        "https://acme.com", "info@acme.com", "+1-555-000-1234",
        "United States", "California", "San Francisco", "123 Market St", "94105", "",
    ]
    for col, val in enumerate(sample_company, 1):
        ws_company.cell(row=2, column=col, value=val)

    # ── Departments sheet ──────────────────────────────────────────────────────
    ws_dept = wb.create_sheet("Departments")
    dept_headers = ["department_name", "description"]
    for col, header in enumerate(dept_headers, 1):
        cell = ws_dept.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        ws_dept.column_dimensions[cell.column_letter].width = 28

    sample_depts = [
        ("Human Resources", "Manages recruitment and employee relations"),
        ("Finance", "Handles accounting and financial planning"),
        ("IT", "Manages technology infrastructure"),
        ("Operations", "Oversees day-to-day business operations"),
        ("Marketing", "Drives brand awareness and campaigns"),
        ("Sales", "Manages client acquisition and revenue"),
    ]
    for row, (name, desc) in enumerate(sample_depts, 2):
        ws_dept.cell(row=row, column=1, value=name)
        ws_dept.cell(row=row, column=2, value=desc)

    # ── Employees sheet ────────────────────────────────────────────────────────
    ws_emp = wb.create_sheet("Employees")
    emp_headers = ["employee_id", "full_name", "email", "phone_number", "department_name", "joining_date"]
    for col, header in enumerate(emp_headers, 1):
        cell = ws_emp.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        ws_emp.column_dimensions[cell.column_letter].width = 22

    sample_emps = [
        ("EMP001", "Alice Johnson", "alice@acme.com", "+1-555-001-0001", "Human Resources", "2024-01-15"),
        ("EMP002", "Bob Smith", "bob@acme.com", "+1-555-001-0002", "IT", "2024-02-01"),
    ]
    for row, emp in enumerate(sample_emps, 2):
        for col, val in enumerate(emp, 1):
            ws_emp.cell(row=row, column=col, value=val)

    # Stream response
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=unisora_onboarding_template.xlsx"},
    )
