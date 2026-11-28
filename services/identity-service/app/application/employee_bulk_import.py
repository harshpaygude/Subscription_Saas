"""Bulk employee import processor decoupled from Asset and Subscription DB tables."""
from __future__ import annotations

import csv
import io
import secrets
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from unisora_kit import RequestContext
from app.domain.entities import UserEntity
from app.domain.ports import (
    AssetProvisioningPort,
    AuditEventPort,
    DepartmentRepository,
    LifecycleProvisioningPort,
    PasswordHasher,
    SubscriptionProvisioningPort,
    UserRepository,
)

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


def _clean_str(val: Any) -> str:
    return "" if val is None else str(val).strip()


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


def extract_rows(content: bytes, filename: str) -> List[Dict[str, Any]]:
    fname = filename.lower()
    if fname.endswith(".xlsx") or fname.endswith(".xls"):
        if not HAS_OPENPYXL:
            raise RuntimeError("openpyxl is required to parse Excel files.")
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        sheet_names_lower = {s.lower(): s for s in wb.sheetnames}
        target_sheet = wb[sheet_names_lower["employees"]] if "employees" in sheet_names_lower else wb.active
        raw_rows = list(target_sheet.iter_rows(values_only=True))
        if not raw_rows or len(raw_rows) < 2:
            return []
        headers = [_normalize_key(str(c)) for c in raw_rows[0] if c is not None]
        rows: List[Dict[str, Any]] = []
        for row_vals in raw_rows[1:]:
            if not any(row_vals):
                continue
            row_dict = {headers[idx]: row_vals[idx] for idx in range(len(headers)) if idx < len(row_vals)}
            if row_dict:
                rows.append(row_dict)
        return rows

    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []
    rows = []
    for raw_row in reader:
        norm = {_normalize_key(k): v for k, v in raw_row.items() if k is not None}
        if any(norm.values()):
            rows.append(norm)
    return rows


def process_employee_bulk_import(
    *,
    content: bytes,
    filename: str,
    ctx: RequestContext,
    users: UserRepository,
    departments: DepartmentRepository,
    hasher: PasswordHasher,
    lifecycle_port: LifecycleProvisioningPort,
    asset_port: AssetProvisioningPort,
    subscription_port: SubscriptionProvisioningPort,
    audit: AuditEventPort,
) -> Dict[str, Any]:
    rows = extract_rows(content, filename)
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

    org_id = ctx.organization_id
    dept_cache = {d.name.strip().lower(): d for d in departments.list_by_org(org_id)}
    user_cache: Dict[str, UserEntity] = {}
    for u in users.list_by_org(org_id):
        user_cache[u.email.strip().lower()] = u
        if u.employee_id:
            user_cache[u.employee_id.strip().lower()] = u

    created_emp_count = 0
    updated_emp_count = 0
    assets_to_import: List[Dict[str, Any]] = []
    user_lookup: Dict[str, int] = {}
    assigned_sub_count = 0

    for row in rows:
        emp_id = _clean_str(row.get("employee_id") or row.get("emp_id") or row.get("id"))
        email = _clean_str(row.get("email") or row.get("employee_email") or row.get("work_email")).lower()
        full_name = _clean_str(row.get("full_name") or row.get("name") or row.get("employee_name") or row.get("display_name"))
        dept_name = _clean_str(row.get("department") or row.get("department_name") or row.get("dept"))
        phone = _clean_str(row.get("phone_number") or row.get("phone") or row.get("mobile"))
        joined_at = _parse_date(row.get("joining_date") or row.get("joined_at") or row.get("start_date"))

        if not email and emp_id:
            email = f"{emp_id.lower()}@workspace.internal"
        elif not email and full_name:
            email = f"{full_name.lower().replace(' ', '.')}@workspace.internal"

        target_user: Optional[UserEntity] = None
        if email or emp_id:
            target_user = user_cache.get(email) or (user_cache.get(emp_id.lower()) if emp_id else None)
            if not target_user and email:
                global_user = users.get_by_email(email)
                if global_user and global_user.organization_id == org_id:
                    target_user = global_user
                else:
                    email_to_assign = email
                    if global_user:
                        base_local, domain = email.split("@", 1) if "@" in email else (email, "workspace.internal")
                        candidate = f"{base_local}+{org_id}@{domain}"
                        suffix = 1
                        while users.get_by_email(candidate):
                            candidate = f"{base_local}+{org_id}.{suffix}@{domain}"
                            suffix += 1
                        email_to_assign = candidate
                    target_user = users.create(
                        UserEntity(
                            id=None,
                            organization_id=org_id,
                            email=email_to_assign,
                            display_name=full_name or email.split("@")[0].capitalize(),
                            employee_id=emp_id or None,
                            phone_number=phone or None,
                            role="MEMBER",
                            password_hash=hasher.hash(secrets.token_urlsafe(24)),
                            created_at=datetime.utcnow(),
                        )
                    )
                    created_emp_count += 1
                assert target_user.id is not None
                user_cache[email] = target_user
                user_cache[target_user.email.lower()] = target_user
                if emp_id:
                    user_cache[emp_id.lower()] = target_user
                lifecycle_port.ensure_active_lifecycle(ctx, target_user.id, joined_at)
            elif target_user:
                changed = False
                if full_name and not target_user.display_name:
                    target_user.display_name = full_name
                    changed = True
                if emp_id and not target_user.employee_id:
                    target_user.employee_id = emp_id
                    user_cache[emp_id.lower()] = target_user
                    changed = True
                if phone and not target_user.phone_number:
                    target_user.phone_number = phone
                    changed = True
                if changed:
                    users.save(target_user)
                    updated_emp_count += 1
                assert target_user.id is not None
                lifecycle_port.ensure_active_lifecycle(ctx, target_user.id, joined_at)

            if target_user and target_user.id is not None:
                user_lookup[target_user.email.lower()] = target_user.id
                if email:
                    user_lookup[email] = target_user.id
                if emp_id:
                    user_lookup[emp_id.lower()] = target_user.id

            if target_user and target_user.id is not None and dept_name:
                dept_obj = dept_cache.get(dept_name.lower())
                if not dept_obj:
                    dept_obj = departments.create(org_id, dept_name, f"{dept_name} department")
                    dept_cache[dept_name.lower()] = dept_obj
                assert dept_obj.id is not None
                departments.ensure_active_membership(org_id, dept_obj.id, target_user.id, joined_at)

        # Collect asset descriptors for Asset Service
        asset_tag = _clean_str(row.get("asset_tag") or row.get("tag") or row.get("hardware_tag"))
        asset_name = _clean_str(row.get("asset_name") or row.get("hardware_name") or row.get("device_name") or row.get("asset"))
        if (asset_tag or asset_name) and target_user and target_user.id is not None:
            assets_to_import.append(
                {
                    "asset_tag": asset_tag or f"AST-{secrets.token_hex(3).upper()}",
                    "name": asset_name or "Hardware Asset",
                    "asset_type": _clean_str(row.get("asset_type") or row.get("device_type")) or "Laptop",
                    "manufacturer": _clean_str(row.get("manufacturer") or row.get("make") or row.get("brand")) or None,
                    "model": _clean_str(row.get("model") or row.get("model_number")) or None,
                    "serial_number": _clean_str(row.get("serial_number") or row.get("serial") or row.get("sn")) or None,
                    "purchase_cost": _clean_str(row.get("purchase_cost") or row.get("cost") or row.get("asset_cost")) or None,
                    "assigned_to": target_user.email.lower(),
                }
            )

        sub_name = _clean_str(
            row.get("subscription") or row.get("subscription_name") or row.get("provider") or row.get("saas_service") or row.get("software") or row.get("license")
        )
        if sub_name and target_user and target_user.id is not None:
            plan_name = _clean_str(row.get("plan") or row.get("license_plan") or row.get("tier")) or "Standard"
            sub_cost_raw = _clean_str(row.get("subscription_cost") or row.get("plan_cost") or row.get("price"))
            sub_cost = None
            if sub_cost_raw:
                try:
                    sub_cost = float(sub_cost_raw.replace("$", "").replace("₹", "").replace(",", "").strip())
                except Exception:
                    sub_cost = None
            if subscription_port.ensure_subscription_and_assign(ctx, target_user.id, sub_name, plan_name, sub_cost):
                assigned_sub_count += 1

    created_assets, assigned_assets = asset_port.create_and_assign_assets(ctx, assets_to_import, user_lookup)
    audit.record(
        organization_id=org_id,
        actor_id=ctx.user_id,
        action="employee.csv.imported",
        entity_type="employee_lifecycle",
        entity_id=0,
        details={
            "filename": filename,
            "created_employees": created_emp_count,
            "updated_employees": updated_emp_count,
            "created_assets": created_assets,
            "assigned_assets": assigned_assets,
            "assigned_subscriptions": assigned_sub_count,
            "total_rows": len(rows),
        },
    )
    return {
        "success": True,
        "message": f"Successfully processed {len(rows)} records: {created_emp_count} employees created, {assigned_assets} IT assets assigned, {assigned_sub_count} subscriptions allocated.",
        "created_employees": created_emp_count,
        "updated_employees": updated_emp_count,
        "created_assets": created_assets,
        "assigned_assets": assigned_assets,
        "assigned_subscriptions": assigned_sub_count,
        "total_processed": len(rows),
    }
