"""IT Asset Bulk Import Processor decoupled from Identity DB tables."""
from __future__ import annotations

import csv
import io
import re
import secrets
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set

from unisora_kit import RequestContext
from app.domain.entities import AssetAssignmentEntity, AssetEntity
from app.domain.ports import (
    AssetAssignmentRepository,
    AssetRepository,
    AuditEventPort,
    IdentityLookupPort,
)

try:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


def _clean_str(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    return "" if s.lower() in ("none", "null", "nan", "n/a", "undefined") else s


def _normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", key.strip().lower()).strip("_")


def _parse_date(val: Any) -> Optional[date]:
    if not val:
        return None
    if isinstance(val, (datetime, date)):
        return val if isinstance(val, date) else val.date()
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ("none", "null", "nan", "n/a"):
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(val_str[:10], fmt).date()
        except Exception:
            continue
    try:
        return date.fromisoformat(val_str[:10])
    except Exception:
        return None


def _parse_cost(val: Any) -> Optional[Decimal]:
    if val is None:
        return None
    val_str = str(val).strip().replace("$", "").replace("€", "").replace("£", "").replace("₹", "").replace(",", "")
    if not val_str or val_str.lower() in ("none", "null", "nan", "n/a"):
        return None
    try:
        return Decimal(val_str)
    except Exception:
        return None


def _infer_asset_type(name: str, given_type: str = "", sheet_name: str = "") -> str:
    if given_type:
        gt_lower = given_type.strip().lower()
        for keywords, label in [
            (("laptop", "notebook", "macbook"), "Laptop"),
            (("headset", "headphone", "earbud", "audio"), "Headset"),
            (("monitor", "display", "screen"), "Monitor"),
            (("phone", "mobile"), "Mobile Phone"),
            (("tablet", "ipad"), "Tablet"),
            (("keyboard",), "Keyboard"),
            (("mouse",), "Mouse"),
            (("dock", "hub"), "Docking Station"),
            (("peripheral", "accessory"), "Peripheral"),
        ]:
            if any(k in gt_lower for k in keywords):
                return label
        return given_type.strip()

    combined = f"{sheet_name} {name}".lower()
    for keywords, label in [
        (("macbook", "thinkpad", "latitude", "zenbook", "laptop", "notebook", "chromebook"), "Laptop"),
        (("headset", "headphone", "earphone", "airpods", "jabra", "bose", "sony wh", "poly", "audio"), "Headset"),
        (("ultrasharp", "monitor", "display", "studio display", "screen"), "Monitor"),
        (("iphone", "pixel", "galaxy", "smartphone", "mobile phone", "phone"), "Mobile Phone"),
        (("ipad", "surface pro", "galaxy tab", "tablet"), "Tablet"),
        (("keyboard", "keychron", "magic keyboard"), "Keyboard"),
        (("mouse", "trackpad", "mx master"), "Mouse"),
        (("caldigit", "thunderbolt dock", "docking", "dock"), "Docking Station"),
    ]:
        if any(k in combined for k in keywords):
            return label
    return "Hardware Asset"


def _extract_items_from_row(row: Dict[str, Any], sheet_name: str = "") -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    assigned_to = _clean_str(
        row.get("assigned_to") or row.get("assigned_employee") or row.get("employee") or row.get("custody_of") or row.get("assigned_user")
    )
    email = _clean_str(row.get("email") or row.get("employee_email") or row.get("work_email")).lower()
    emp_id = _clean_str(row.get("employee_id") or row.get("emp_id") or row.get("id"))
    emp_name = _clean_str(row.get("full_name") or row.get("name") or row.get("employee_name") or row.get("display_name"))

    device_prefixes = [
        ("laptop", "Laptop"), ("headset", "Headset"), ("monitor", "Monitor"),
        ("phone", "Mobile Phone"), ("tablet", "Tablet"), ("keyboard", "Keyboard"),
        ("mouse", "Mouse"), ("dock", "Docking Station"), ("accessory", "Peripheral"),
    ]
    found_wide = False
    for pfx, dev_type in device_prefixes:
        dev_tag = _clean_str(row.get(f"{pfx}_tag") or row.get(f"{pfx}_asset_tag") or row.get(f"{pfx}_id"))
        dev_name = _clean_str(row.get(f"{pfx}_name") or row.get(f"{pfx}_model") or row.get(pfx))
        dev_mfr = _clean_str(row.get(f"{pfx}_manufacturer") or row.get(f"{pfx}_brand") or row.get(f"{pfx}_make"))
        dev_model = _clean_str(row.get(f"{pfx}_model_number") or row.get(f"{pfx}_model"))
        dev_serial = _clean_str(row.get(f"{pfx}_serial") or row.get(f"{pfx}_serial_number") or row.get(f"{pfx}_sn"))
        dev_cost = _clean_str(row.get(f"{pfx}_cost") or row.get(f"{pfx}_price") or row.get(f"{pfx}_purchase_cost"))
        if dev_tag or dev_name or dev_serial:
            found_wide = True
            items.append({
                "asset_tag": dev_tag,
                "name": dev_name or f"{dev_mfr} {dev_model}".strip() or f"{dev_type} Device",
                "asset_type": dev_type,
                "manufacturer": dev_mfr,
                "model": dev_model or (dev_name if not dev_mfr else ""),
                "serial_number": dev_serial,
                "purchase_cost": dev_cost,
                "currency": _clean_str(row.get("currency") or "USD"),
                "location": _clean_str(row.get(f"{pfx}_location") or row.get("location")),
                "handover_notes": f"{dev_type} issued to employee.",
                "assigned_to": assigned_to or email or emp_id or emp_name,
                "employee_id": emp_id,
                "employee_email": email,
                "employee_name": emp_name,
            })

    for num in range(1, 10):
        a_tag = _clean_str(row.get(f"asset_{num}_tag") or row.get(f"asset_{num}") or row.get(f"device_{num}_tag"))
        a_name = _clean_str(row.get(f"asset_{num}_name") or row.get(f"device_{num}_name"))
        a_type = _clean_str(row.get(f"asset_{num}_type") or row.get(f"device_{num}_type"))
        a_serial = _clean_str(row.get(f"asset_{num}_serial") or row.get(f"device_{num}_serial"))
        a_cost = _clean_str(row.get(f"asset_{num}_cost") or row.get(f"device_{num}_cost"))
        if a_tag or a_name or a_serial:
            found_wide = True
            resolved_type = _infer_asset_type(a_name, a_type, sheet_name)
            items.append({
                "asset_tag": a_tag,
                "name": a_name or f"{resolved_type} {num}",
                "asset_type": resolved_type,
                "manufacturer": _clean_str(row.get(f"asset_{num}_manufacturer")),
                "model": _clean_str(row.get(f"asset_{num}_model")),
                "serial_number": a_serial,
                "purchase_cost": a_cost,
                "currency": _clean_str(row.get("currency") or "USD"),
                "location": _clean_str(row.get("location")),
                "handover_notes": f"Asset {num} issued to employee.",
                "assigned_to": assigned_to or email or emp_id or emp_name,
                "employee_id": emp_id,
                "employee_email": email,
                "employee_name": emp_name,
            })

    if found_wide:
        return items

    raw_tag = _clean_str(row.get("asset_tag") or row.get("tag") or row.get("asset_id") or row.get("hardware_tag") or row.get("device_tag") or row.get("barcode"))
    raw_name = _clean_str(row.get("name") or row.get("asset_name") or row.get("device_name") or row.get("hardware_name") or row.get("title") or row.get("equipment"))
    raw_type = _clean_str(row.get("asset_type") or row.get("type") or row.get("device_type") or row.get("category") or row.get("hardware_type"))
    mfr = _clean_str(row.get("manufacturer") or row.get("brand") or row.get("make") or row.get("vendor"))
    model = _clean_str(row.get("model") or row.get("model_number") or row.get("model_name"))
    raw_serial = _clean_str(row.get("serial_number") or row.get("serial") or row.get("sn") or row.get("s_n") or row.get("serial_no"))
    cost = _clean_str(row.get("purchase_cost") or row.get("cost") or row.get("price") or row.get("asset_cost") or row.get("purchase_price"))
    if not raw_tag and not raw_name and not raw_serial:
        return []

    resolved_type = _infer_asset_type(raw_name, raw_type, sheet_name)
    items.append({
        "asset_tag": raw_tag,
        "name": raw_name or f"{mfr} {model}".strip() or f"{resolved_type} Hardware",
        "asset_type": resolved_type,
        "manufacturer": mfr,
        "model": model,
        "serial_number": raw_serial,
        "purchase_cost": cost,
        "currency": _clean_str(row.get("currency") or "USD"),
        "purchase_date": row.get("purchase_date") or row.get("purchased_at") or row.get("buy_date"),
        "warranty_expiry": row.get("warranty_expiry") or row.get("warranty") or row.get("warranty_date"),
        "location": _clean_str(row.get("location") or row.get("office") or row.get("site") or row.get("desk")),
        "handover_notes": _clean_str(row.get("handover_notes") or row.get("notes") or row.get("condition_at_issue") or row.get("condition") or row.get("comments")),
        "assigned_to": assigned_to or email or emp_id or emp_name,
        "employee_id": emp_id,
        "employee_email": email,
        "employee_name": emp_name,
    })
    return items


def _extract_from_excel(content: bytes) -> List[Dict[str, Any]]:
    if not HAS_OPENPYXL:
        raise RuntimeError("openpyxl is required to parse Excel files.")
    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    all_items: List[Dict[str, Any]] = []
    sheet_names_lower = {s.strip().lower(): s for s in wb.sheetnames}
    candidates = [
        real for low, real in sheet_names_lower.items()
        if low not in ("company", "departments")
        and any(kw in low for kw in ("asset", "hardware", "device", "equipment", "laptop", "headset", "monitor", "roster"))
    ]
    if not candidates:
        candidates = [next((n for n in wb.sheetnames if n.strip().lower() not in ("company", "departments")), wb.active.title)]

    for title in candidates:
        rows = list(wb[title].iter_rows(values_only=True))
        if len(rows) < 2:
            continue
        headers = [_normalize_key(str(c)) for c in rows[0] if c is not None]
        for row_vals in rows[1:]:
            if not any(row_vals):
                continue
            row_dict = {headers[idx]: row_vals[idx] for idx in range(len(headers)) if idx < len(row_vals)}
            if any(row_dict.values()):
                all_items.extend(_extract_items_from_row(row_dict, sheet_name=title))
    wb.close()
    return all_items


def _extract_from_csv(content: bytes) -> List[Dict[str, Any]]:
    text = ""
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if not text:
        text = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []
    all_items: List[Dict[str, Any]] = []
    for raw_row in reader:
        norm_row = {_normalize_key(k): v for k, v in raw_row.items() if k is not None}
        if any(norm_row.values()):
            all_items.extend(_extract_items_from_row(norm_row))
    return all_items


def process_asset_bulk_import(
    *,
    content: bytes,
    filename: str,
    ctx: RequestContext,
    assets: AssetRepository,
    assignments: AssetAssignmentRepository,
    identity_lookup: IdentityLookupPort,
    audit: AuditEventPort,
) -> Dict[str, Any]:
    fname = filename.lower()
    raw_items = _extract_from_excel(content) if (fname.endswith(".xlsx") or fname.endswith(".xls")) else _extract_from_csv(content)
    if not raw_items:
        return {
            "success": False,
            "message": "No valid IT hardware or asset rows found in the uploaded file.",
            "created_assets": 0,
            "updated_assets": 0,
            "assigned_assets": 0,
            "employees_matched": 0,
            "total_processed": 0,
            "warnings": ["Check that your file includes columns such as Asset Tag, Asset Name, Asset Type, and optional Assigned Employee."],
        }

    org_id = ctx.organization_id
    created_count = 0
    updated_count = 0
    assigned_count = 0
    assigned_employees: Set[int] = set()
    warnings: List[str] = []

    users_by_ref: Dict[str, int] = {}
    for u in identity_lookup.list_org_users(ctx):
        uid = int(u["id"])
        if u.get("email"):
            users_by_ref[str(u["email"]).strip().lower()] = uid
        if u.get("employee_id"):
            users_by_ref[str(u["employee_id"]).strip().lower()] = uid
        if u.get("display_name"):
            users_by_ref[str(u["display_name"]).strip().lower()] = uid

    assets_by_tag = {a.asset_tag.strip().lower(): a for a in assets.list_filtered(org_id)}
    now = datetime.utcnow()

    for idx, item in enumerate(raw_items, start=1):
        asset_tag = _clean_str(item.get("asset_tag"))
        name = _clean_str(item.get("name"))
        asset_type = _clean_str(item.get("asset_type")) or "Hardware Asset"
        manufacturer = _clean_str(item.get("manufacturer")) or None
        model = _clean_str(item.get("model")) or None
        serial_number = _clean_str(item.get("serial_number")) or None
        purchase_cost = _parse_cost(item.get("purchase_cost"))
        currency = (_clean_str(item.get("currency")) or "USD").upper()[:3]
        purchase_date = _parse_date(item.get("purchase_date"))
        warranty_expiry = _parse_date(item.get("warranty_expiry"))
        location = _clean_str(item.get("location")) or None
        notes = _clean_str(item.get("handover_notes")) or None

        if not asset_tag:
            pfx = {"Laptop": "LT", "Headset": "HD", "Monitor": "MN", "Mobile Phone": "PH", "Tablet": "TB"}.get(asset_type, "AST")
            asset_tag = f"{pfx}-{secrets.token_hex(3).upper()}"
            warnings.append(f"Row {idx} ('{name}'): missing asset_tag, generated '{asset_tag}'.")

        tag_key = asset_tag.lower()
        target_user_id: Optional[int] = None
        assigned_ref = _clean_str(
            item.get("assigned_to") or item.get("employee_email") or item.get("email") or item.get("employee_id") or item.get("employee_name")
        )
        if assigned_ref:
            ref_lower = assigned_ref.lower()
            target_user_id = users_by_ref.get(ref_lower)
            if target_user_id is None:
                emp_email = item.get("employee_email") or item.get("email")
                emp_name = item.get("employee_name") or item.get("assigned_to")
                emp_num = item.get("employee_id")
                if not emp_email:
                    if "@" in assigned_ref:
                        emp_email = assigned_ref
                    elif emp_num:
                        emp_email = f"{emp_num.lower()}@workspace.internal"
                    else:
                        slug = re.sub(r"[^a-z0-9]+", ".", assigned_ref.lower()).strip(".")
                        emp_email = f"{slug}@workspace.internal"
                provisioned = identity_lookup.provision_user(
                    ctx, email=emp_email, display_name=emp_name or assigned_ref, employee_id=emp_num or None
                )
                target_user_id = int(provisioned["id"])
                users_by_ref[ref_lower] = target_user_id
                users_by_ref[str(provisioned["email"]).lower()] = target_user_id

        asset_obj = assets_by_tag.get(tag_key)
        if asset_obj:
            if name:
                asset_obj.name = name
            if asset_type and asset_obj.asset_type == "Hardware Asset":
                asset_obj.asset_type = asset_type
            if manufacturer:
                asset_obj.manufacturer = manufacturer
            if model:
                asset_obj.model = model
            if serial_number:
                asset_obj.serial_number = serial_number
            if purchase_cost is not None:
                asset_obj.purchase_cost = purchase_cost
            if location:
                asset_obj.location = location
            if purchase_date:
                asset_obj.purchase_date = purchase_date
            if warranty_expiry:
                asset_obj.warranty_expiry = warranty_expiry
            asset_obj = assets.save(asset_obj)
            updated_count += 1
        else:
            asset_obj = assets.create(
                AssetEntity(
                    id=None,
                    organization_id=org_id,
                    asset_tag=asset_tag,
                    asset_type=asset_type,
                    name=name or f"{manufacturer or ''} {model or ''}".strip() or f"{asset_type} Equipment",
                    manufacturer=manufacturer,
                    model=model,
                    serial_number=serial_number,
                    purchase_date=purchase_date,
                    purchase_cost=purchase_cost,
                    currency=currency,
                    warranty_expiry=warranty_expiry,
                    status="AVAILABLE",
                    location=location,
                    created_at=now,
                    updated_at=now,
                )
            )
            assets_by_tag[tag_key] = asset_obj
            created_count += 1
            assert asset_obj.id is not None
            audit.record(
                organization_id=org_id,
                actor_id=ctx.user_id,
                action="asset.created",
                entity_type="asset",
                entity_id=asset_obj.id,
                details={"asset_tag": asset_tag, "source": "bulk_import"},
            )

        assert asset_obj.id is not None
        if target_user_id is not None:
            existing_asgn = assignments.get_active_for_asset_locked(asset_obj.id, org_id)
            if existing_asgn and existing_asgn.user_id != target_user_id:
                existing_asgn.status = "RETURNED"
                existing_asgn.returned_at = datetime.utcnow()
                existing_asgn.handover_notes = "Transferred custody via bulk import."
                assignments.save(existing_asgn)
                existing_asgn = None

            if not existing_asgn:
                assignments.create(
                    AssetAssignmentEntity(
                        id=None,
                        organization_id=org_id,
                        asset_id=asset_obj.id,
                        user_id=target_user_id,
                        assigned_by=ctx.user_id,
                        assigned_at=now,
                        expected_return_at=None,
                        returned_at=None,
                        returned_by=None,
                        condition_at_issue=None,
                        condition_at_return=None,
                        handover_notes=notes or f"Assigned {asset_type} custody via bulk import.",
                        status="ACTIVE",
                    )
                )
                asset_obj.status = "ASSIGNED"
                assets.save(asset_obj)
                assigned_count += 1
            elif notes:
                existing_asgn.handover_notes = notes
                assignments.save(existing_asgn)

            assigned_employees.add(target_user_id)
            audit.record(
                organization_id=org_id,
                actor_id=ctx.user_id,
                action="asset.assigned",
                entity_type="asset",
                entity_id=asset_obj.id,
                details={"user_id": target_user_id, "asset_tag": asset_obj.asset_tag, "source": "bulk_import"},
            )

    return {
        "success": True,
        "message": f"Successfully processed {len(raw_items)} IT hardware assets: {created_count} registered to inventory, {updated_count} updated, and {assigned_count} asset assignments linked across {len(assigned_employees)} employees.",
        "created_assets": created_count,
        "updated_assets": updated_count,
        "assigned_assets": assigned_count,
        "employees_matched": len(assigned_employees),
        "total_processed": len(raw_items),
        "warnings": warnings[:10],
    }


def generate_sample_asset_csv() -> str:
    rows = [
        "Asset Tag,Asset Name,Asset Type,Manufacturer,Model,Serial Number,Purchase Cost,Currency,Location,Status,Assigned Employee Email,Assigned Employee Name,Employee ID,Handover Notes",
        "LT-101,MacBook Pro 16 M3 Max,Laptop,Apple,A2991,SN-APL-8821,3499.00,USD,San Francisco HQ,Assigned,alex.rivera@acme.com,Alex Rivera,EMP101,Primary work laptop",
        "HD-101,Jabra Evolve2 65 Wireless,Headset,Jabra,Evolve2-65,SN-JBR-9912,249.00,USD,San Francisco HQ,Assigned,alex.rivera@acme.com,Alex Rivera,EMP101,Wireless ANC headset",
        "MN-101,Dell UltraSharp 27 4K USB-C,Monitor,Dell,U2723QE,SN-DLL-4412,579.00,USD,Desk 4A,Assigned,alex.rivera@acme.com,Alex Rivera,EMP101,External 4K display",
        "LT-104,Dell Latitude 5540,Laptop,Dell,5540-I7,SN-DLL-1092,1299.00,USD,IT Storage Room,Available,,,,Ready for next onboarding batch",
    ]
    return "\n".join(rows) + "\n"


def generate_sample_asset_excel() -> bytes:
    if not HAS_OPENPYXL:
        raise RuntimeError("openpyxl is required to generate Excel files.")
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "IT Assets"
    headers = [
        "asset_tag", "name", "asset_type", "manufacturer", "model", "serial_number",
        "purchase_cost", "currency", "location", "status", "assigned_to", "employee_name", "employee_id", "handover_notes",
    ]
    ws1.append(headers)
    header_font = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="0EA5E9", end_color="0EA5E9", fill_type="solid")
    for col_idx in range(1, len(headers) + 1):
        c = ws1.cell(row=1, column=col_idx)
        c.font = header_font
        c.fill = header_fill
        c.alignment = Alignment(horizontal="center", vertical="center")
    sample_rows = [
        ("LT-101", "MacBook Pro 16 M3 Max", "Laptop", "Apple", "A2991", "SN-APL-8821", "3499.00", "USD", "San Francisco HQ", "Assigned", "alex.rivera@acme.com", "Alex Rivera", "EMP101", "Primary laptop"),
        ("HD-101", "Jabra Evolve2 65 Wireless", "Headset", "Jabra", "Evolve2-65", "SN-JBR-9912", "249.00", "USD", "San Francisco HQ", "Assigned", "alex.rivera@acme.com", "Alex Rivera", "EMP101", "Wireless headset"),
        ("MN-101", "Dell UltraSharp 27 4K", "Monitor", "Dell", "U2723QE", "SN-DLL-4412", "579.00", "USD", "Desk 4A", "Assigned", "alex.rivera@acme.com", "Alex Rivera", "EMP101", "4K display"),
        ("LT-104", "Dell Latitude 5540", "Laptop", "Dell", "5540-I7", "SN-DLL-1092", "1299.00", "USD", "Storage Room B", "Available", "", "", "", "In stock"),
    ]
    for r in sample_rows:
        ws1.append(r)
    ws2 = wb.create_sheet("Multi-Device Roster")
    ws2.append(["employee_id", "full_name", "email", "laptop_tag", "laptop_name", "headset_tag", "headset_name"])
    ws2.append(["EMP101", "Alex Rivera", "alex.rivera@acme.com", "LT-101", "MacBook Pro 16", "HD-101", "Jabra Evolve2 65"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
