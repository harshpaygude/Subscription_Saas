"""
IT Asset Bulk Import Processor for CSV and Excel (.xlsx, .xls) files.
Supports multi-device 1-to-many relationships (e.g. employee issued Laptop, Headset, Monitor, Peripherals).
"""
from __future__ import annotations

import csv
import io
import re
import secrets
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.security import hash_password
from app.database.models import Asset, AssetAssignment, User

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
    if s.lower() in ("none", "null", "nan", "n/a", "undefined"):
        return ""
    return s


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
        gt = given_type.strip()
        gt_lower = gt.lower()
        if "laptop" in gt_lower or "notebook" in gt_lower or "macbook" in gt_lower:
            return "Laptop"
        if "headset" in gt_lower or "headphone" in gt_lower or "earbud" in gt_lower or "audio" in gt_lower:
            return "Headset"
        if "monitor" in gt_lower or "display" in gt_lower or "screen" in gt_lower:
            return "Monitor"
        if "phone" in gt_lower or "mobile" in gt_lower:
            return "Mobile Phone"
        if "tablet" in gt_lower or "ipad" in gt_lower:
            return "Tablet"
        if "keyboard" in gt_lower:
            return "Keyboard"
        if "mouse" in gt_lower:
            return "Mouse"
        if "dock" in gt_lower or "hub" in gt_lower:
            return "Docking Station"
        if "peripheral" in gt_lower or "accessory" in gt_lower:
            return "Peripheral"
        return gt

    s_lower = sheet_name.lower()
    if "laptop" in s_lower:
        return "Laptop"
    if "headset" in s_lower or "audio" in s_lower:
        return "Headset"
    if "monitor" in s_lower or "display" in s_lower:
        return "Monitor"
    if "phone" in s_lower or "mobile" in s_lower:
        return "Mobile Phone"

    n_lower = name.lower()
    if any(k in n_lower for k in ("macbook", "thinkpad", "latitude", "zenbook", "laptop", "notebook", "chromebook")):
        return "Laptop"
    if any(k in n_lower for k in ("headset", "headphone", "earphone", "airpods", "jabra", "bose", "sony wh", "poly")):
        return "Headset"
    if any(k in n_lower for k in ("ultrasharp", "monitor", "display", "studio display", "screen")):
        return "Monitor"
    if any(k in n_lower for k in ("iphone", "pixel", "galaxy", "smartphone", "mobile phone")):
        return "Mobile Phone"
    if any(k in n_lower for k in ("ipad", "surface pro", "galaxy tab", "tablet")):
        return "Tablet"
    if any(k in n_lower for k in ("keyboard", "keychron", "magic keyboard")):
        return "Keyboard"
    if any(k in n_lower for k in ("mouse", "trackpad", "mx master")):
        return "Mouse"
    if any(k in n_lower for k in ("caldigit", "thunderbolt dock", "docking", "dock")):
        return "Docking Station"
    return "Hardware Asset"


def _extract_items_from_row(row: Dict[str, Any], sheet_name: str = "") -> List[Dict[str, Any]]:
    """
    Extracts one or more asset records from a normalized row dictionary.
    Supports:
    1. Multi-column wide rows (e.g. laptop_tag, headset_tag, monitor_tag).
    2. Numbered asset columns (e.g. asset_1_tag, asset_2_tag).
    3. Delimited multi-value cells (e.g. asset_tag = "LT-101, HD-101").
    4. Standard single asset per row.
    """
    items: List[Dict[str, Any]] = []

    # Employee identity fields on this row
    assigned_to = _clean_str(
        row.get("assigned_to")
        or row.get("assigned_employee")
        or row.get("employee")
        or row.get("custody_of")
        or row.get("assigned_user")
    )
    email = _clean_str(row.get("email") or row.get("employee_email") or row.get("work_email")).lower()
    emp_id = _clean_str(row.get("employee_id") or row.get("emp_id") or row.get("id"))
    emp_name = _clean_str(
        row.get("full_name") or row.get("name") or row.get("employee_name") or row.get("display_name")
    )

    # Check for wide multi-device columns (e.g. laptop_*, headset_*, monitor_*, phone_*, dock_*)
    device_prefixes = [
        ("laptop", "Laptop"),
        ("headset", "Headset"),
        ("monitor", "Monitor"),
        ("phone", "Mobile Phone"),
        ("tablet", "Tablet"),
        ("keyboard", "Keyboard"),
        ("mouse", "Mouse"),
        ("dock", "Docking Station"),
        ("accessory", "Peripheral"),
    ]

    found_wide_asset = False
    for pfx, dev_type in device_prefixes:
        # Check if tag or name or model exists for this device
        dev_tag = _clean_str(row.get(f"{pfx}_tag") or row.get(f"{pfx}_asset_tag") or row.get(f"{pfx}_id"))
        dev_name = _clean_str(row.get(f"{pfx}_name") or row.get(f"{pfx}_model") or row.get(pfx))
        dev_mfr = _clean_str(row.get(f"{pfx}_manufacturer") or row.get(f"{pfx}_brand") or row.get(f"{pfx}_make"))
        dev_model = _clean_str(row.get(f"{pfx}_model_number") or row.get(f"{pfx}_model"))
        dev_serial = _clean_str(row.get(f"{pfx}_serial") or row.get(f"{pfx}_serial_number") or row.get(f"{pfx}_sn"))
        dev_cost = _clean_str(row.get(f"{pfx}_cost") or row.get(f"{pfx}_price") or row.get(f"{pfx}_purchase_cost"))

        if dev_tag or dev_name or dev_serial:
            found_wide_asset = True
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
                "status": "ASSIGNED" if (assigned_to or email or emp_id or emp_name) else "AVAILABLE",
                "handover_notes": f"{dev_type} issued to employee.",
                "assigned_to": assigned_to or email or emp_id or emp_name,
                "employee_id": emp_id,
                "employee_email": email,
                "employee_name": emp_name,
            })

    # Check for numbered asset columns (e.g. asset_1_*, asset_2_*, device_1_*)
    for num in range(1, 10):
        a_tag = _clean_str(row.get(f"asset_{num}_tag") or row.get(f"asset_{num}") or row.get(f"device_{num}_tag"))
        a_name = _clean_str(row.get(f"asset_{num}_name") or row.get(f"device_{num}_name"))
        a_type = _clean_str(row.get(f"asset_{num}_type") or row.get(f"device_{num}_type"))
        a_serial = _clean_str(row.get(f"asset_{num}_serial") or row.get(f"device_{num}_serial"))
        a_cost = _clean_str(row.get(f"asset_{num}_cost") or row.get(f"device_{num}_cost"))
        if a_tag or a_name or a_serial:
            found_wide_asset = True
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
                "status": "ASSIGNED" if (assigned_to or email or emp_id or emp_name) else "AVAILABLE",
                "handover_notes": f"Asset {num} issued to employee.",
                "assigned_to": assigned_to or email or emp_id or emp_name,
                "employee_id": emp_id,
                "employee_email": email,
                "employee_name": emp_name,
            })

    if found_wide_asset:
        return items

    # Standard tabular row: check for single or delimited asset info
    raw_tag = _clean_str(
        row.get("asset_tag")
        or row.get("tag")
        or row.get("asset_id")
        or row.get("hardware_tag")
        or row.get("device_tag")
        or row.get("barcode")
    )
    raw_name = _clean_str(
        row.get("name")
        or row.get("asset_name")
        or row.get("device_name")
        or row.get("hardware_name")
        or row.get("title")
        or row.get("equipment")
    )
    raw_type = _clean_str(
        row.get("asset_type")
        or row.get("type")
        or row.get("device_type")
        or row.get("category")
        or row.get("hardware_type")
    )
    mfr = _clean_str(row.get("manufacturer") or row.get("brand") or row.get("make") or row.get("vendor"))
    model = _clean_str(row.get("model") or row.get("model_number") or row.get("model_name"))
    raw_serial = _clean_str(
        row.get("serial_number")
        or row.get("serial")
        or row.get("sn")
        or row.get("s_n")
        or row.get("serial_no")
    )
    cost = _clean_str(
        row.get("purchase_cost")
        or row.get("cost")
        or row.get("price")
        or row.get("asset_cost")
        or row.get("purchase_price")
    )
    currency = _clean_str(row.get("currency") or "USD")
    pdate = row.get("purchase_date") or row.get("purchased_at") or row.get("buy_date")
    warranty = row.get("warranty_expiry") or row.get("warranty") or row.get("warranty_date")
    location = _clean_str(row.get("location") or row.get("office") or row.get("site") or row.get("desk"))
    status_str = _clean_str(row.get("status") or row.get("custody_status") or row.get("state"))
    notes = _clean_str(
        row.get("handover_notes")
        or row.get("notes")
        or row.get("condition_at_issue")
        or row.get("condition")
        or row.get("comments")
    )

    if not raw_tag and not raw_name and not raw_serial:
        return []

    # Check if tags or serials are comma/semicolon delimited for multi-asset in single cell
    if ("," in raw_tag or ";" in raw_tag) and not (" " in raw_tag and "," not in raw_tag):
        delims = re.split(r"[,;]+", raw_tag)
        names = re.split(r"[,;]+", raw_name) if ("," in raw_name or ";" in raw_name) else [raw_name] * len(delims)
        types = re.split(r"[,;]+", raw_type) if ("," in raw_type or ";" in raw_type) else [raw_type] * len(delims)
        serials = re.split(r"[,;]+", raw_serial) if ("," in raw_serial or ";" in raw_serial) else [raw_serial] * len(delims)

        for i, sub_tag in enumerate(delims):
            st = sub_tag.strip()
            if not st:
                continue
            snm = names[i].strip() if i < len(names) else raw_name
            stp = types[i].strip() if i < len(types) else raw_type
            ssr = serials[i].strip() if i < len(serials) else ""
            res_type = _infer_asset_type(snm, stp, sheet_name)
            items.append({
                "asset_tag": st,
                "name": snm or f"{res_type} Device",
                "asset_type": res_type,
                "manufacturer": mfr,
                "model": model,
                "serial_number": ssr,
                "purchase_cost": cost,
                "currency": currency,
                "purchase_date": pdate,
                "warranty_expiry": warranty,
                "location": location,
                "status": status_str,
                "handover_notes": notes,
                "assigned_to": assigned_to or email or emp_id or emp_name,
                "employee_id": emp_id,
                "employee_email": email,
                "employee_name": emp_name,
            })
        return items

    # Standard single item
    resolved_type = _infer_asset_type(raw_name, raw_type, sheet_name)
    resolved_name = raw_name or f"{mfr} {model}".strip() or f"{resolved_type} Hardware"

    items.append({
        "asset_tag": raw_tag,
        "name": resolved_name,
        "asset_type": resolved_type,
        "manufacturer": mfr,
        "model": model,
        "serial_number": raw_serial,
        "purchase_cost": cost,
        "currency": currency,
        "purchase_date": pdate,
        "warranty_expiry": warranty,
        "location": location,
        "status": status_str,
        "handover_notes": notes,
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

    # Identify sheets to process:
    # 1) If sheet is "Company" or "Departments", skip.
    # 2) If "Assets" or "IT Assets" or "Hardware" or "Devices" present, prioritize them.
    # 3) Also check category sheets like "Laptops", "Headsets", "Monitors".
    candidate_sheets: List[str] = []

    for name_lower, real_name in sheet_names_lower.items():
        if name_lower in ("company", "departments"):
            continue
        if any(kw in name_lower for kw in ("asset", "hardware", "device", "equipment", "laptop", "headset", "monitor", "roster")):
            candidate_sheets.append(real_name)

    if not candidate_sheets:
        # Default to first non-metadata sheet or active sheet
        for real_name in wb.sheetnames:
            if real_name.strip().lower() not in ("company", "departments"):
                candidate_sheets.append(real_name)
                break
        if not candidate_sheets:
            candidate_sheets.append(wb.active.title)

    for sheet_title in candidate_sheets:
        ws = wb[sheet_title]
        rows = list(ws.iter_rows(values_only=True))
        if not rows or len(rows) < 2:
            continue

        headers = [_normalize_key(str(c)) for c in rows[0] if c is not None]
        for row_vals in rows[1:]:
            if not any(row_vals):
                continue
            row_dict: Dict[str, Any] = {}
            for idx, h in enumerate(headers):
                if idx < len(row_vals):
                    row_dict[h] = row_vals[idx]

            if any(row_dict.values()):
                extracted = _extract_items_from_row(row_dict, sheet_name=sheet_title)
                all_items.extend(extracted)

    wb.close()
    return all_items


def _extract_from_csv(content: bytes) -> List[Dict[str, Any]]:
    # Attempt UTF-8 with BOM, then UTF-8, then Latin-1
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = content.decode("utf-8", errors="replace")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []

    all_items: List[Dict[str, Any]] = []
    for raw_row in reader:
        norm_row: Dict[str, Any] = {}
        for k, v in raw_row.items():
            if k is not None:
                norm_row[_normalize_key(k)] = v
        if any(norm_row.values()):
            extracted = _extract_items_from_row(norm_row)
            all_items.extend(extracted)

    return all_items


def process_asset_bulk_import(
    content: bytes,
    filename: str,
    db: Session,
    current_user: User,
) -> Dict[str, Any]:
    """
    Parses CSV or Excel file and registers IT Assets and establishes 1-to-many custody assignments to employees.
    """
    fname = filename.lower()
    if fname.endswith(".xlsx") or fname.endswith(".xls"):
        raw_items = _extract_from_excel(content)
    else:
        raw_items = _extract_from_csv(content)

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

    org_id = current_user.organization_id
    created_count = 0
    updated_count = 0
    assigned_count = 0
    assigned_employees: Set[int] = set()
    warnings: List[str] = []

    # Cache users in organization: by email, by employee_id, and by display_name
    users_by_email: Dict[str, User] = {}
    users_by_empid: Dict[str, User] = {}
    users_by_name: Dict[str, User] = {}

    for u in db.query(User).filter(User.organization_id == org_id).all():
        if u.email:
            users_by_email[u.email.strip().lower()] = u
        if u.employee_id:
            users_by_empid[u.employee_id.strip().lower()] = u
        if u.display_name:
            users_by_name[u.display_name.strip().lower()] = u

    # Cache existing assets by lowercase asset_tag
    assets_by_tag: Dict[str, Asset] = {
        a.asset_tag.strip().lower(): a
        for a in db.query(Asset).filter(Asset.organization_id == org_id).all()
    }

    # Process each asset item
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

        # Auto-generate asset_tag if missing
        if not asset_tag:
            prefix_map = {
                "Laptop": "LT",
                "Headset": "HD",
                "Monitor": "MN",
                "Mobile Phone": "PH",
                "Tablet": "TB",
                "Keyboard": "KB",
                "Mouse": "MS",
                "Docking Station": "DK",
                "Peripheral": "PR",
            }
            pfx = prefix_map.get(asset_type, "AST")
            asset_tag = f"{pfx}-{secrets.token_hex(3).upper()}"
            warnings.append(f"Row {idx} ('{name}'): missing asset_tag, generated '{asset_tag}'.")

        tag_key = asset_tag.lower()

        # Match or provision employee for custody assignment
        target_user: Optional[User] = None
        assigned_ref = _clean_str(
            item.get("assigned_to")
            or item.get("employee_email")
            or item.get("email")
            or item.get("employee_id")
            or item.get("employee_name")
        )

        if assigned_ref:
            ref_lower = assigned_ref.lower()
            if ref_lower in users_by_email:
                target_user = users_by_email[ref_lower]
            elif ref_lower in users_by_empid:
                target_user = users_by_empid[ref_lower]
            elif ref_lower in users_by_name:
                target_user = users_by_name[ref_lower]
            else:
                # Employee not in database yet: auto-provision user so 1-to-many assignment succeeds
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

                clean_email = emp_email.lower().strip()
                if clean_email in users_by_email:
                    target_user = users_by_email[clean_email]
                else:
                    global_user = db.query(User).filter(User.email.ilike(clean_email)).first()
                    if global_user and global_user.organization_id == org_id:
                        target_user = global_user
                        users_by_email[clean_email] = global_user
                    else:
                        email_to_assign = clean_email
                        if global_user:
                            at_sign = "@"
                            base_local, domain = clean_email.split(at_sign, 1) if at_sign in clean_email else (clean_email, "workspace.internal")
                            candidate = f"{base_local}+{org_id}@{domain}"
                            suffix = 1
                            while db.query(User).filter(User.email.ilike(candidate)).first():
                                candidate = f"{base_local}+{org_id}.{suffix}@{domain}"
                                suffix += 1
                            email_to_assign = candidate

                        new_user = User(
                            organization_id=org_id,
                            email=email_to_assign,
                            display_name=emp_name or assigned_ref,
                            employee_id=emp_num or None,
                            role="MEMBER",
                            password_hash=hash_password(secrets.token_urlsafe(24)),
                        )
                        db.add(new_user)
                        db.flush()
                        target_user = new_user
                        users_by_email[clean_email] = new_user
                        users_by_email[email_to_assign] = new_user
                        if emp_num:
                            users_by_empid[emp_num.lower()] = new_user
                        if new_user.display_name:
                            users_by_name[new_user.display_name.lower()] = new_user

        # Create or update Asset
        asset_obj = assets_by_tag.get(tag_key)
        if asset_obj:
            # Update fields
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
            asset_obj.updated_at = datetime.utcnow()
            updated_count += 1
        else:
            asset_obj = Asset(
                organization_id=org_id,
                asset_tag=asset_tag,
                name=name or f"{manufacturer or ''} {model or ''}".strip() or f"{asset_type} Equipment",
                asset_type=asset_type,
                manufacturer=manufacturer,
                model=model,
                serial_number=serial_number,
                purchase_cost=purchase_cost,
                currency=currency,
                purchase_date=purchase_date,
                warranty_expiry=warranty_expiry,
                location=location,
                status="AVAILABLE",
            )
            db.add(asset_obj)
            db.flush()
            assets_by_tag[tag_key] = asset_obj
            created_count += 1
            record_audit(db, current_user, "asset.created", "asset", asset_obj.id, {"asset_tag": asset_tag, "source": "bulk_import"})

        # Handle 1-to-many employee custody assignment
        if target_user:
            existing_assignment = (
                db.query(AssetAssignment)
                .filter(
                    AssetAssignment.organization_id == org_id,
                    AssetAssignment.asset_id == asset_obj.id,
                    AssetAssignment.status == "ACTIVE",
                )
                .first()
            )

            if existing_assignment:
                if existing_assignment.user_id != target_user.id:
                    # Device was transferred to a different employee
                    existing_assignment.status = "RETURNED"
                    existing_assignment.returned_at = datetime.utcnow()
                    existing_assignment.handover_notes = "Transferred custody via bulk import."

                    new_assignment = AssetAssignment(
                        organization_id=org_id,
                        asset_id=asset_obj.id,
                        user_id=target_user.id,
                        assigned_by=current_user.id,
                        status="ACTIVE",
                        handover_notes=notes or f"Assigned {asset_type} custody via bulk import.",
                    )
                    db.add(new_assignment)
                    asset_obj.status = "ASSIGNED"
                    assigned_count += 1
                else:
                    # Already in custody of this employee
                    if notes:
                        existing_assignment.handover_notes = notes
                    asset_obj.status = "ASSIGNED"
            else:
                # Fresh assignment
                new_assignment = AssetAssignment(
                    organization_id=org_id,
                    asset_id=asset_obj.id,
                    user_id=target_user.id,
                    assigned_by=current_user.id,
                    status="ACTIVE",
                    handover_notes=notes or f"Assigned {asset_type} custody via bulk import.",
                )
                db.add(new_assignment)
                asset_obj.status = "ASSIGNED"
                assigned_count += 1

            assigned_employees.add(target_user.id)
            record_audit(
                db,
                current_user,
                "asset.assigned",
                "asset",
                asset_obj.id,
                {"user_id": target_user.id, "asset_tag": asset_obj.asset_tag, "source": "bulk_import"},
            )

    db.commit()

    return {
        "success": True,
        "message": (
            f"Successfully processed {len(raw_items)} IT hardware assets: "
            f"{created_count} registered to inventory, {updated_count} updated, "
            f"and {assigned_count} asset assignments linked across {len(assigned_employees)} employees."
        ),
        "created_assets": created_count,
        "updated_assets": updated_count,
        "assigned_assets": assigned_count,
        "employees_matched": len(assigned_employees),
        "total_processed": len(raw_items),
        "warnings": warnings[:10],
    }


def generate_sample_asset_csv() -> str:
    """
    Generates a sample CSV illustrating 1-to-many IT asset provisioning to employees.
    Alex Rivera has 3 assets (Laptop, Headset, Monitor).
    Sophia Chen has 2 assets (Laptop, Headset).
    Marcus Vance has 2 assets (Laptop, Monitor).
    Additional assets are available in storage.
    """
    rows = [
        "Asset Tag,Asset Name,Asset Type,Manufacturer,Model,Serial Number,Purchase Cost,Currency,Location,Status,Assigned Employee Email,Assigned Employee Name,Employee ID,Handover Notes",
        "LT-101,MacBook Pro 16 M3 Max,Laptop,Apple,A2991,SN-APL-8821,3499.00,USD,San Francisco HQ,Assigned,alex.rivera@acme.com,Alex Rivera,EMP101,Primary work laptop with 64GB Unified Memory",
        "HD-101,Jabra Evolve2 65 Wireless,Headset,Jabra,Evolve2-65,SN-JBR-9912,249.00,USD,San Francisco HQ,Assigned,alex.rivera@acme.com,Alex Rivera,EMP101,ANC wireless headset with charging stand",
        "MN-101,Dell UltraSharp 27 4K USB-C,Monitor,Dell,U2723QE,SN-DLL-4412,579.00,USD,Desk 4A,Assigned,alex.rivera@acme.com,Alex Rivera,EMP101,External 4K display with 90W power delivery",
        "LT-102,Lenovo ThinkPad X1 Carbon Gen 11,Laptop,Lenovo,21HM000EUS,SN-LNV-7731,1899.00,USD,Austin Office,Assigned,sophia.chen@acme.com,Sophia Chen,EMP102,Ultrabook for engineering lead",
        "HD-102,Sony WH-1000XM5 ANC,Headset,Sony,WH-1000XM5,SN-SNY-3319,399.00,USD,Austin Office,Assigned,sophia.chen@acme.com,Sophia Chen,EMP102,Premium noise-canceling headphones",
        "LT-103,MacBook Air 15 M3,Laptop,Apple,A3114,SN-APL-2299,1499.00,USD,Remote,Assigned,marcus.vance@acme.com,Marcus Vance,EMP103,Design and documentation workstation",
        "MN-102,Apple Studio Display 27,Monitor,Apple,MK0U3LL/A,SN-APL-5520,1599.00,USD,Remote,Assigned,marcus.vance@acme.com,Marcus Vance,EMP103,5K Retina display with True Tone",
        "PH-101,iPhone 15 Pro Enterprise,Mobile Phone,Apple,A3102,SN-APL-7744,999.00,USD,San Francisco HQ,Assigned,alex.rivera@acme.com,Alex Rivera,EMP101,Company testing phone",
        "LT-104,Dell Latitude 5540,Laptop,Dell,5540-I7,SN-DLL-1092,1299.00,USD,IT Storage Room,Available,,,,Ready for next onboarding batch",
        "HD-103,Jabra Evolve 40 Stereo,Headset,Jabra,Evolve-40,SN-JBR-1188,89.00,USD,IT Storage Room,Available,,,,Wired USB headset in backup storage",
        "MN-103,LG 34 Curved UltraWide,Monitor,LG,34WN80C-B,SN-LG-9821,549.00,USD,IT Storage Room,Available,,,,Spare ultrawide display in storage room",
    ]
    return "\n".join(rows) + "\n"


def generate_sample_asset_excel() -> bytes:
    """
    Generates a beautifully styled multi-sheet Excel workbook illustrating 1-to-many IT asset assignments.
    """
    if not HAS_OPENPYXL:
        raise RuntimeError("openpyxl is required to generate Excel files.")

    wb = openpyxl.Workbook()

    header_font = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="0EA5E9", end_color="0EA5E9", fill_type="solid")  # Sky/Cyan accent
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center")
    border_thin = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0"),
    )

    # ── Sheet 1: IT Assets (Tabular 1-to-many) ──────────────────────────────────
    ws1 = wb.active
    ws1.title = "IT Assets"

    headers1 = [
        "asset_tag", "name", "asset_type", "manufacturer", "model",
        "serial_number", "purchase_cost", "currency", "location",
        "status", "assigned_to", "employee_name", "employee_id", "handover_notes",
    ]

    for col_idx, header in enumerate(headers1, 1):
        cell = ws1.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center
        ws1.column_dimensions[cell.column_letter].width = 22

    sample_assets = [
        ("LT-101", "MacBook Pro 16 M3 Max", "Laptop", "Apple", "A2991", "SN-APL-8821", "3499.00", "USD", "San Francisco HQ", "Assigned", "alex.rivera@acme.com", "Alex Rivera", "EMP101", "Primary work laptop (64GB RAM)"),
        ("HD-101", "Jabra Evolve2 65 Wireless", "Headset", "Jabra", "Evolve2-65", "SN-JBR-9912", "249.00", "USD", "San Francisco HQ", "Assigned", "alex.rivera@acme.com", "Alex Rivera", "EMP101", "Wireless ANC headset with stand"),
        ("MN-101", "Dell UltraSharp 27 4K USB-C", "Monitor", "Dell", "U2723QE", "SN-DLL-4412", "579.00", "USD", "Desk 4A", "Assigned", "alex.rivera@acme.com", "Alex Rivera", "EMP101", "4K Hub monitor with USB-C 90W"),
        ("LT-102", "Lenovo ThinkPad X1 Carbon Gen 11", "Laptop", "Lenovo", "21HM000EUS", "SN-LNV-7731", "1899.00", "USD", "Austin Office", "Assigned", "sophia.chen@acme.com", "Sophia Chen", "EMP102", "Engineering lead laptop"),
        ("HD-102", "Sony WH-1000XM5 ANC", "Headset", "Sony", "WH-1000XM5", "SN-SNY-3319", "399.00", "USD", "Austin Office", "Assigned", "sophia.chen@acme.com", "Sophia Chen", "EMP102", "Premium noise-canceling headphones"),
        ("LT-103", "MacBook Air 15 M3", "Laptop", "Apple", "A3114", "SN-APL-2299", "1499.00", "USD", "Remote", "Assigned", "marcus.vance@acme.com", "Marcus Vance", "EMP103", "Design workstation"),
        ("MN-102", "Apple Studio Display 27", "Monitor", "Apple", "MK0U3LL/A", "SN-APL-5520", "1599.00", "USD", "Remote", "Assigned", "marcus.vance@acme.com", "Marcus Vance", "EMP103", "5K Retina Studio Display"),
        ("PH-101", "iPhone 15 Pro Enterprise", "Mobile Phone", "Apple", "A3102", "SN-APL-7744", "999.00", "USD", "San Francisco HQ", "Assigned", "alex.rivera@acme.com", "Alex Rivera", "EMP101", "Company testing phone"),
        ("LT-104", "Dell Latitude 5540", "Laptop", "Dell", "5540-I7", "SN-DLL-1092", "1299.00", "USD", "Storage Room B", "Available", "", "", "", "Ready for new onboarding batch"),
        ("HD-103", "Jabra Evolve 40 Stereo", "Headset", "Jabra", "Evolve-40", "SN-JBR-1188", "89.00", "USD", "Storage Room B", "Available", "", "", "", "Spare wired headset in stock"),
        ("MN-103", "LG 34 Curved UltraWide", "Monitor", "LG", "34WN80C-B", "SN-LG-9821", "549.00", "USD", "Storage Room B", "Available", "", "", "", "Ultrawide display in stock"),
    ]

    for row_idx, row_data in enumerate(sample_assets, 2):
        for col_idx, val in enumerate(row_data, 1):
            cell = ws1.cell(row=row_idx, column=col_idx, value=val)
            cell.alignment = align_left
            cell.border = border_thin

    # ── Sheet 2: Wide Multi-Device Roster ───────────────────────────────────────
    ws2 = wb.create_sheet("Multi-Device Roster")
    headers2 = [
        "employee_id", "full_name", "email",
        "laptop_tag", "laptop_name", "laptop_serial", "laptop_cost",
        "headset_tag", "headset_name", "headset_serial", "headset_cost",
        "monitor_tag", "monitor_name", "monitor_serial", "monitor_cost",
    ]

    for col_idx, header in enumerate(headers2, 1):
        cell = ws2.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = PatternFill(start_color="6366F1", end_color="6366F1", fill_type="solid")  # Indigo header
        cell.alignment = align_center
        ws2.column_dimensions[cell.column_letter].width = 22

    sample_wide_roster = [
        ("EMP101", "Alex Rivera", "alex.rivera@acme.com", "LT-101", "MacBook Pro 16 M3 Max", "SN-APL-8821", "3499.00", "HD-101", "Jabra Evolve2 65", "SN-JBR-9912", "249.00", "MN-101", "Dell UltraSharp 27 4K", "SN-DLL-4412", "579.00"),
        ("EMP102", "Sophia Chen", "sophia.chen@acme.com", "LT-102", "ThinkPad X1 Carbon Gen 11", "SN-LNV-7731", "1899.00", "HD-102", "Sony WH-1000XM5", "SN-SNY-3319", "399.00", "", "", "", ""),
        ("EMP103", "Marcus Vance", "marcus.vance@acme.com", "LT-103", "MacBook Air 15 M3", "SN-APL-2299", "1499.00", "", "", "", "", "MN-102", "Apple Studio Display 27", "SN-APL-5520", "1599.00"),
    ]

    for row_idx, row_data in enumerate(sample_wide_roster, 2):
        for col_idx, val in enumerate(row_data, 1):
            cell = ws2.cell(row=row_idx, column=col_idx, value=val)
            cell.alignment = align_left
            cell.border = border_thin

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()
