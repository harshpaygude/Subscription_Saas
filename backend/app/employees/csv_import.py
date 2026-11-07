"""
Multi-service Bulk Import Processor for Employees, IT Assets, and Subscriptions.
Supports both CSV and Excel (.xlsx, .xls) files.
"""
from __future__ import annotations

import csv
import io
import secrets
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.database.models import (
    Asset,
    AssetAssignment,
    Department,
    DepartmentMembership,
    EmployeeLifecycle,
    Subscription,
    SubscriptionAssignment,
    SubscriptionLicense,
    User,
)
from app.audit.service import record_audit

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


def _clean_str(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _normalize_key(key: str) -> str:
    return key.strip().lower().replace(" ", "_").replace("-", "_")


def _parse_date(val: Any) -> date:
    if not val:
        return date.today()
    if isinstance(val, (datetime, date)):
        return val if isinstance(val, date) else val.date()
    val_str = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(val_str[:10], fmt).date()
        except Exception:
            continue
    try:
        return date.fromisoformat(val_str[:10])
    except Exception:
        return date.today()


def _extract_rows_from_excel(content: bytes) -> List[Dict[str, Any]]:
    if not HAS_OPENPYXL:
        raise RuntimeError("openpyxl is required to parse Excel files.")

    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    all_rows: List[Dict[str, Any]] = []

    # Check if workbook has multiple standard sheets (e.g., Employees, IT Assets, Subscriptions)
    sheet_names_lower = {s.lower(): s for s in wb.sheetnames}
    
    if "employees" in sheet_names_lower:
        emp_sheet = wb[sheet_names_lower["employees"]]
        emp_rows = list(emp_sheet.iter_rows(values_only=True))
        if emp_rows and len(emp_rows) > 1:
            headers = [_normalize_key(str(c)) for c in emp_rows[0] if c is not None]
            for row_vals in emp_rows[1:]:
                if not any(row_vals):
                    continue
                row_dict = {}
                for idx, h in enumerate(headers):
                    if idx < len(row_vals):
                        row_dict[h] = row_vals[idx]
                if row_dict:
                    all_rows.append(row_dict)

        # Merge IT Assets sheet by matching assigned_to or email/employee_id
        if "it assets" in sheet_names_lower or "assets" in sheet_names_lower:
            asset_sheet_name = sheet_names_lower.get("it assets") or sheet_names_lower.get("assets")
            asset_sheet = wb[asset_sheet_name]
            asset_rows = list(asset_sheet.iter_rows(values_only=True))
            if asset_rows and len(asset_rows) > 1:
                asset_headers = [_normalize_key(str(c)) for c in asset_rows[0] if c is not None]
                for row_vals in asset_rows[1:]:
                    if not any(row_vals):
                        continue
                    a_dict = {}
                    for idx, h in enumerate(asset_headers):
                        if idx < len(row_vals):
                            a_dict[h] = row_vals[idx]
                    
                    assigned_key = _clean_str(a_dict.get("assigned_to") or a_dict.get("email") or a_dict.get("employee_id")).lower()
                    # Try to merge with existing employee row
                    matched = False
                    if assigned_key:
                        for erow in all_rows:
                            e_mail = _clean_str(erow.get("email")).lower()
                            e_id = _clean_str(erow.get("employee_id")).lower()
                            if assigned_key in (e_mail, e_id):
                                for k, v in a_dict.items():
                                    if k not in erow or not erow[k]:
                                        erow[k] = v
                                matched = True
                                break
                    if not matched:
                        all_rows.append(a_dict)

        # Merge Subscriptions sheet
        if "subscriptions" in sheet_names_lower:
            sub_sheet = wb[sheet_names_lower["subscriptions"]]
            sub_rows = list(sub_sheet.iter_rows(values_only=True))
            if sub_rows and len(sub_rows) > 1:
                sub_headers = [_normalize_key(str(c)) for c in sub_rows[0] if c is not None]
                for row_vals in sub_rows[1:]:
                    if not any(row_vals):
                        continue
                    s_dict = {}
                    for idx, h in enumerate(sub_headers):
                        if idx < len(row_vals):
                            s_dict[h] = row_vals[idx]
                    assigned_key = _clean_str(s_dict.get("assigned_to") or s_dict.get("email") or s_dict.get("employee_id")).lower()
                    if assigned_key:
                        for erow in all_rows:
                            e_mail = _clean_str(erow.get("email")).lower()
                            e_id = _clean_str(erow.get("employee_id")).lower()
                            if assigned_key in (e_mail, e_id):
                                for k, v in s_dict.items():
                                    if k not in erow or not erow[k]:
                                        erow[k] = v
                                break
    else:
        # Single active sheet
        sheet = wb.active
        rows = list(sheet.iter_rows(values_only=True))
        if rows and len(rows) > 1:
            headers = [_normalize_key(str(c)) for c in rows[0] if c is not None]
            for row_vals in rows[1:]:
                if not any(row_vals):
                    continue
                row_dict = {}
                for idx, h in enumerate(headers):
                    if idx < len(row_vals):
                        row_dict[h] = row_vals[idx]
                if row_dict:
                    all_rows.append(row_dict)

    return all_rows


def _extract_rows_from_csv(content: bytes) -> List[Dict[str, Any]]:
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    all_rows: List[Dict[str, Any]] = []
    if not reader.fieldnames:
        return []

    for raw_row in reader:
        norm_row: Dict[str, Any] = {}
        for k, v in raw_row.items():
            if k is not None:
                norm_row[_normalize_key(k)] = v
        if any(norm_row.values()):
            all_rows.append(norm_row)

    return all_rows


def process_bulk_import(
    content: bytes,
    filename: str,
    db: Session,
    current_user: User,
) -> Dict[str, Any]:
    """
    Parses CSV or Excel file and creates/updates:
    1. Employees (Users, EmployeeLifecycle, DepartmentMembership)
    2. IT Assets (Asset, AssetAssignment)
    3. Subscriptions (Subscription, SubscriptionLicense, SubscriptionAssignment)
    """
    fname = filename.lower()
    if fname.endswith(".xlsx") or fname.endswith(".xls"):
        rows = _extract_rows_from_excel(content)
    else:
        rows = _extract_rows_from_csv(content)

    if not rows:
        return {
            "success": False,
            "message": "No valid data rows found in file.",
            "created_employees": 0,
            "updated_employees": 0,
            "created_assets": 0,
            "assigned_assets": 0,
            "assigned_subscriptions": 0,
            "total_processed": 0,
        }

    org_id = current_user.organization_id
    created_emp_count = 0
    updated_emp_count = 0
    created_asset_count = 0
    assigned_asset_count = 0
    assigned_sub_count = 0

    # Cache departments to minimize queries
    dept_cache: Dict[str, Department] = {
        d.name.strip().lower(): d
        for d in db.query(Department).filter(Department.organization_id == org_id).all()
    }

    # Cache users in org
    user_cache: Dict[str, User] = {}
    for u in db.query(User).filter(User.organization_id == org_id).all():
        if u.email:
            user_cache[u.email.strip().lower()] = u
        if u.employee_id:
            user_cache[u.employee_id.strip().lower()] = u

    # Cache assets
    asset_cache: Dict[str, Asset] = {
        a.asset_tag.strip().lower(): a
        for a in db.query(Asset).filter(Asset.organization_id == org_id).all()
    }

    # Cache subscriptions
    sub_cache: Dict[str, Subscription] = {
        s.provider.strip().lower(): s
        for s in db.query(Subscription).filter(Subscription.organization_id == org_id).all()
    }

    for row in rows:
        # ==========================================
        # 1. PROCESS EMPLOYEE INFO
        # ==========================================
        emp_id = _clean_str(row.get("employee_id") or row.get("emp_id") or row.get("id"))
        email = _clean_str(row.get("email") or row.get("employee_email") or row.get("work_email")).lower()
        full_name = _clean_str(
            row.get("full_name") or row.get("name") or row.get("employee_name") or row.get("display_name")
        )
        dept_name = _clean_str(row.get("department") or row.get("department_name") or row.get("dept"))
        role = _clean_str(row.get("role") or row.get("designation") or row.get("job_title")) or "MEMBER"
        phone = _clean_str(row.get("phone_number") or row.get("phone") or row.get("mobile"))
        joining_raw = row.get("joining_date") or row.get("joined_at") or row.get("start_date")
        joined_at = _parse_date(joining_raw)

        # Fallback email if only name/ID provided
        if not email and emp_id:
            email = f"{emp_id.lower()}@workspace.internal"
        elif not email and full_name:
            clean_part = full_name.lower().replace(" ", ".")
            email = f"{clean_part}@workspace.internal"

        target_user: Optional[User] = None
        if email or emp_id:
            if email and email in user_cache:
                target_user = user_cache[email]
            elif emp_id and emp_id.lower() in user_cache:
                target_user = user_cache[emp_id.lower()]

            if not target_user and email:
                # Create user
                random_pass = hash_password(secrets.token_urlsafe(24))
                target_user = User(
                    organization_id=org_id,
                    email=email,
                    display_name=full_name or email.split("@")[0].capitalize(),
                    employee_id=emp_id or None,
                    phone_number=phone or None,
                    role="MEMBER",
                    password_hash=random_pass,
                )
                db.add(target_user)
                db.flush()
                created_emp_count += 1
                user_cache[email] = target_user
                if emp_id:
                    user_cache[emp_id.lower()] = target_user

                # Lifecycle record
                db.add(
                    EmployeeLifecycle(
                        organization_id=org_id,
                        user_id=target_user.id,
                        status="ACTIVE",
                        joined_at=joined_at,
                    )
                )
            elif target_user:
                # Update existing user details if new information supplied
                updated = False
                if full_name and not target_user.display_name:
                    target_user.display_name = full_name
                    updated = True
                if emp_id and not target_user.employee_id:
                    target_user.employee_id = emp_id
                    user_cache[emp_id.lower()] = target_user
                    updated = True
                if phone and not target_user.phone_number:
                    target_user.phone_number = phone
                    updated = True
                if updated:
                    updated_emp_count += 1

                # Ensure active lifecycle
                lc = (
                    db.query(EmployeeLifecycle)
                    .filter(EmployeeLifecycle.organization_id == org_id, EmployeeLifecycle.user_id == target_user.id)
                    .first()
                )
                if not lc:
                    db.add(
                        EmployeeLifecycle(
                            organization_id=org_id,
                            user_id=target_user.id,
                            status="ACTIVE",
                            joined_at=joined_at,
                        )
                    )

            # Department assignment
            if target_user and dept_name:
                dept_key = dept_name.lower()
                dept_obj = dept_cache.get(dept_key)
                if not dept_obj:
                    dept_obj = Department(
                        organization_id=org_id,
                        name=dept_name,
                        description=f"{dept_name} department",
                        is_active=True,
                    )
                    db.add(dept_obj)
                    db.flush()
                    dept_cache[dept_key] = dept_obj

                # Check membership
                mem = (
                    db.query(DepartmentMembership)
                    .filter(
                        DepartmentMembership.organization_id == org_id,
                        DepartmentMembership.department_id == dept_obj.id,
                        DepartmentMembership.user_id == target_user.id,
                        DepartmentMembership.is_active.is_(True),
                    )
                    .first()
                )
                if not mem:
                    db.add(
                        DepartmentMembership(
                            organization_id=org_id,
                            department_id=dept_obj.id,
                            user_id=target_user.id,
                            effective_from=joined_at,
                            is_active=True,
                        )
                    )

        # ==========================================
        # 2. PROCESS IT ASSET INFO (1-to-Many support)
        # ==========================================
        asset_tag = _clean_str(row.get("asset_tag") or row.get("tag") or row.get("hardware_tag"))
        asset_name = _clean_str(
            row.get("asset_name") or row.get("hardware_name") or row.get("device_name") or row.get("asset")
        )
        asset_type = _clean_str(row.get("asset_type") or row.get("device_type")) or "Laptop"
        manufacturer = _clean_str(row.get("manufacturer") or row.get("make") or row.get("brand"))
        model = _clean_str(row.get("model") or row.get("model_number"))
        serial_no = _clean_str(row.get("serial_number") or row.get("serial") or row.get("sn"))
        cost_raw = _clean_str(row.get("purchase_cost") or row.get("cost") or row.get("asset_cost"))

        # Collect all assets on this row (primary + wide device columns for 1-to-many support)
        row_assets: List[Tuple[str, str, str, str, str, str, str]] = []
        if asset_tag or asset_name:
            row_assets.append((asset_tag, asset_name, asset_type, manufacturer, model, serial_no, cost_raw))

        for pfx, dev_type in [("laptop", "Laptop"), ("headset", "Headset"), ("monitor", "Monitor"), ("phone", "Mobile Phone")]:
            d_tag = _clean_str(row.get(f"{pfx}_tag") or row.get(f"{pfx}_asset_tag") or row.get(f"{pfx}_id"))
            d_name = _clean_str(row.get(f"{pfx}_name") or row.get(f"{pfx}_model") or row.get(pfx))
            d_mfr = _clean_str(row.get(f"{pfx}_manufacturer") or row.get(f"{pfx}_brand"))
            d_model = _clean_str(row.get(f"{pfx}_model_number") or row.get(f"{pfx}_model"))
            d_serial = _clean_str(row.get(f"{pfx}_serial") or row.get(f"{pfx}_serial_number") or row.get(f"{pfx}_sn"))
            d_cost = _clean_str(row.get(f"{pfx}_cost") or row.get(f"{pfx}_price"))
            if d_tag or d_name or d_serial:
                if not any(a[0] and a[0].lower() == d_tag.lower() for a in row_assets if a[0]):
                    row_assets.append((d_tag, d_name or f"{d_mfr} {d_model}".strip() or f"{dev_type} Device", dev_type, d_mfr, d_model, d_serial, d_cost))

        for a_tag, a_name, a_type, a_mfr, a_model, a_sn, a_cost_raw in row_assets:
            tag_key = (a_tag or f"AST-{secrets.token_hex(3).upper()}").lower()
            asset_obj = asset_cache.get(tag_key)
            if not asset_obj:
                cost_num: Optional[float] = None
                if a_cost_raw:
                    try:
                        cost_num = float(a_cost_raw.replace("$", "").replace("₹", "").replace(",", "").strip())
                    except Exception:
                        cost_num = None

                asset_obj = Asset(
                    organization_id=org_id,
                    asset_tag=a_tag or tag_key.upper(),
                    name=a_name or f"{a_mfr} {a_model}".strip() or f"{a_type} Hardware",
                    asset_type=a_type,
                    manufacturer=a_mfr or None,
                    model=a_model or None,
                    serial_number=a_sn or None,
                    purchase_cost=cost_num,
                    currency="USD",
                    status="AVAILABLE",
                )
                db.add(asset_obj)
                db.flush()
                created_asset_count += 1
                asset_cache[tag_key] = asset_obj

            # If an employee exists for this row, assign the asset
            if target_user and asset_obj:
                existing_assignment = (
                    db.query(AssetAssignment)
                    .filter(
                        AssetAssignment.organization_id == org_id,
                        AssetAssignment.asset_id == asset_obj.id,
                        AssetAssignment.status == "ACTIVE",
                    )
                    .first()
                )
                if not existing_assignment:
                    asset_obj.status = "ASSIGNED"
                    db.add(
                        AssetAssignment(
                            organization_id=org_id,
                            asset_id=asset_obj.id,
                            user_id=target_user.id,
                            assigned_by=current_user.id,
                            status="ACTIVE",
                        )
                    )
                    assigned_asset_count += 1
                elif existing_assignment.user_id != target_user.id:
                    # Reassign to current target user
                    existing_assignment.status = "RETURNED"
                    existing_assignment.returned_at = datetime.utcnow()
                    db.add(
                        AssetAssignment(
                            organization_id=org_id,
                            asset_id=asset_obj.id,
                            user_id=target_user.id,
                            assigned_by=current_user.id,
                            status="ACTIVE",
                        )
                    )
                    assigned_asset_count += 1

        # ==========================================
        # 3. PROCESS SUBSCRIPTION / LICENSE INFO
        # ==========================================
        sub_name = _clean_str(
            row.get("subscription")
            or row.get("subscription_name")
            or row.get("provider")
            or row.get("saas_service")
            or row.get("software")
            or row.get("license")
        )
        plan_name = _clean_str(row.get("plan") or row.get("license_plan") or row.get("tier")) or "Standard"
        sub_cost_raw = _clean_str(row.get("subscription_cost") or row.get("plan_cost") or row.get("price"))

        if sub_name and target_user:
            sub_key = sub_name.lower()
            sub_obj = sub_cache.get(sub_key)
            if not sub_obj:
                cost_val: Optional[float] = None
                if sub_cost_raw:
                    try:
                        cost_val = float(sub_cost_raw.replace("$", "").replace("₹", "").replace(",", "").strip())
                    except Exception:
                        cost_val = None

                sub_obj = Subscription(
                    organization_id=org_id,
                    user_id=current_user.id,
                    provider=sub_name,
                    name=f"{sub_name} Workspace",
                    plan=plan_name,
                    amount=cost_val if cost_val is not None else 25.0,
                    currency="USD",
                    billing_interval="MONTHLY",
                    status="ACTIVE",
                    source="csv_import",
                )
                db.add(sub_obj)
                db.flush()
                sub_cache[sub_key] = sub_obj

            # Ensure subscription license exists
            license_obj = (
                db.query(SubscriptionLicense)
                .filter(
                    SubscriptionLicense.organization_id == org_id,
                    SubscriptionLicense.subscription_id == sub_obj.id,
                    SubscriptionLicense.status == "ACTIVE",
                )
                .first()
            )
            if not license_obj:
                license_obj = SubscriptionLicense(
                    organization_id=org_id,
                    subscription_id=sub_obj.id,
                    reference=f"{sub_name} Seat",
                    capacity=100,
                    status="ACTIVE",
                )
                db.add(license_obj)
                db.flush()

            # Assign subscription license to target_user
            existing_sub_assign = (
                db.query(SubscriptionAssignment)
                .filter(
                    SubscriptionAssignment.organization_id == org_id,
                    SubscriptionAssignment.subscription_id == sub_obj.id,
                    SubscriptionAssignment.user_id == target_user.id,
                    SubscriptionAssignment.status == "ACTIVE",
                )
                .first()
            )
            if not existing_sub_assign:
                db.add(
                    SubscriptionAssignment(
                        organization_id=org_id,
                        subscription_id=sub_obj.id,
                        license_id=license_obj.id,
                        user_id=target_user.id,
                        assigned_by=current_user.id,
                        status="ACTIVE",
                    )
                )
                assigned_sub_count += 1

    # Audit log
    record_audit(
        db,
        current_user,
        "employee.csv.imported",
        "employee_lifecycle",
        0,
        {
            "filename": filename,
            "created_employees": created_emp_count,
            "updated_employees": updated_emp_count,
            "created_assets": created_asset_count,
            "assigned_assets": assigned_asset_count,
            "assigned_subscriptions": assigned_sub_count,
            "total_rows": len(rows),
        },
    )

    db.commit()

    return {
        "success": True,
        "message": f"Successfully processed {len(rows)} records: {created_emp_count} employees created, {assigned_asset_count} IT assets assigned, {assigned_sub_count} subscriptions allocated.",
        "created_employees": created_emp_count,
        "updated_employees": updated_emp_count,
        "created_assets": created_asset_count,
        "assigned_assets": assigned_asset_count,
        "assigned_subscriptions": assigned_sub_count,
        "total_processed": len(rows),
    }
