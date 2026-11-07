"""
Subscription & SaaS Contract Bulk Import Processor for CSV and Excel (.xlsx, .xls) files.
Supports SaaS vendors, plan tiers, recurring amounts, renewal dates, and autopay vs manual renewal types.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.database.models import Subscription, SubscriptionLicense, User

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


def _parse_amount(val: Any) -> Optional[Decimal]:
    if not val:
        return None
    s = str(val).strip().replace("$", "").replace("€", "").replace("£", "").replace(",", "")
    try:
        return Decimal(s)
    except Exception:
        return None


def _normalize_interval(val: Any) -> str:
    s = _clean_str(val).lower()
    if not s:
        return "monthly"
    if "year" in s or "annu" in s:
        return "annual"
    if "quart" in s:
        return "quarterly"
    if "week" in s:
        return "weekly"
    return "monthly"


def _normalize_renewal_type(val: Any) -> str:
    s = _clean_str(val).lower()
    if not s:
        return "AUTOPAY"
    if any(k in s for k in ("manual", "invoice", "po", "wire", "check", "false", "no")):
        return "MANUAL"
    return "AUTOPAY"


def _normalize_status(val: Any) -> str:
    s = _clean_str(val).upper()
    if "CANCEL" in s:
        return "CANCELLED"
    if "ARCHIV" in s:
        return "ARCHIVED"
    return "ACTIVE"


def parse_tabular_data(content: bytes, filename: str) -> List[Dict[str, str]]:
    """Parse CSV or Excel content into list of lowercase-keyed row dictionaries."""
    fn_lower = filename.lower()
    rows: List[Dict[str, str]] = []

    if fn_lower.endswith(".xlsx") or fn_lower.endswith(".xlsm") or fn_lower.endswith(".xltx"):
        if not HAS_OPENPYXL:
            raise ValueError("openpyxl is not installed for Excel file processing.")
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        # Look for a sheet named Subscriptions or SaaS, or default to active sheet
        sheet = None
        for name in wb.sheetnames:
            if any(k in name.lower() for k in ("subscription", "saas", "license", "tools")):
                sheet = wb[name]
                break
        if sheet is None:
            sheet = wb.active

        raw_rows = list(sheet.iter_rows(values_only=True))
        if not raw_rows:
            return []

        header_idx = -1
        for idx, row in enumerate(raw_rows):
            if not row:
                continue
            cells = [_normalize_key(str(c)) for c in row if c is not None]
            if any(h in cells for h in ("name", "service", "subscription_name", "provider", "vendor")):
                header_idx = idx
                break

        if header_idx == -1:
            header_idx = 0

        raw_headers = raw_rows[header_idx]
        headers = [_normalize_key(str(c)) if c is not None else f"col_{i}" for i, c in enumerate(raw_headers)]

        for row in raw_rows[header_idx + 1:]:
            if not row or all(c is None or str(c).strip() == "" for c in row):
                continue
            row_dict: Dict[str, str] = {}
            for i, cell in enumerate(row):
                if i < len(headers) and headers[i]:
                    row_dict[headers[i]] = _clean_str(cell)
            if row_dict:
                rows.append(row_dict)
        return rows

    # Otherwise treat as CSV
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
    text = ""
    for enc in encodings:
        try:
            text = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if not text:
        text = content.decode("utf-8", errors="replace")

    dialect = csv.excel
    try:
        sample = text[:4096]
        dialect = csv.Sniffer().sniff(sample)
    except Exception:
        dialect = csv.excel

    reader = csv.reader(io.StringIO(text), dialect)
    raw_rows = list(reader)
    if not raw_rows:
        return []

    header_idx = -1
    for idx, row in enumerate(raw_rows):
        cells = [_normalize_key(c) for c in row if c]
        if any(h in cells for h in ("name", "service", "subscription_name", "provider", "vendor")):
            header_idx = idx
            break

    if header_idx == -1:
        header_idx = 0

    headers = [_normalize_key(c) if c else f"col_{i}" for i, c in enumerate(raw_rows[header_idx])]

    for row in raw_rows[header_idx + 1:]:
        if not row or all(not str(c).strip() for c in row):
            continue
        row_dict = {}
        for i, cell in enumerate(row):
            if i < len(headers) and headers[i]:
                row_dict[headers[i]] = _clean_str(cell)
        if row_dict:
            rows.append(row_dict)

    return rows


def find_field(row: Dict[str, str], candidates: List[str]) -> str:
    for c in candidates:
        if c in row and row[c]:
            return row[c]
    for key, val in row.items():
        for c in candidates:
            if c in key and val:
                return val
    return ""


def process_subscription_bulk_import(
    db: Session,
    actor: User,
    file_bytes: bytes,
    filename: str,
) -> Dict[str, Any]:
    """Parse and persist SaaS subscriptions in bulk."""
    rows = parse_tabular_data(file_bytes, filename)
    if not rows:
        raise ValueError("The uploaded file does not contain any readable subscription rows.")

    imported_count = 0
    updated_count = 0
    errors: List[str] = []

    for row_num, row in enumerate(rows, start=2):
        name = find_field(row, ["subscription_name", "service_name", "name", "service", "tool", "product"])
        provider = find_field(row, ["provider", "vendor", "service_provider", "company", "source"])

        if not name:
            errors.append(f"Row {row_num}: Missing required subscription/service name.")
            continue

        if not provider:
            # Fallback provider from name or lowercase token
            provider = name.split()[0].lower()

        plan = find_field(row, ["plan", "tier", "plan_tier", "edition", "license_type"]) or None
        amount_raw = find_field(row, ["amount", "cost", "price", "annual_cost", "monthly_cost", "spend"])
        amount = _parse_amount(amount_raw)
        currency = find_field(row, ["currency", "curr"]) or "USD"
        currency = currency.strip().upper()[:3]
        billing_interval = _normalize_interval(find_field(row, ["billing_interval", "billing_cycle", "interval", "cycle", "frequency"]))
        
        start_date = _parse_date(find_field(row, ["start_date", "contract_start", "started_at", "contract_date"]))
        next_renewal_date = _parse_date(find_field(row, ["next_renewal_date", "renewal_date", "renewal", "expires_at", "contract_end", "expiry_date"]))

        renewal_type_raw = find_field(row, ["renewal_type", "renewal_mode", "autopay", "payment_method", "auto_renew", "pay_type"])
        renewal_type = _normalize_renewal_type(renewal_type_raw)

        status_raw = find_field(row, ["status", "subscription_status", "state"])
        status = _normalize_status(status_raw)

        note = find_field(row, ["note", "notes", "description", "comments", "payment_details"]) or None
        seats_raw = find_field(row, ["seats", "licenses", "capacity", "seat_count", "users"])

        # Check existing subscription for this org
        existing = (
            db.query(Subscription)
            .filter(
                Subscription.organization_id == actor.organization_id,
                Subscription.provider.ilike(provider.strip()),
                Subscription.name.ilike(name.strip()),
            )
            .first()
        )

        if existing:
            existing.plan = plan or existing.plan
            if amount is not None:
                existing.amount = float(amount)
            existing.currency = currency
            existing.billing_interval = billing_interval
            if start_date:
                existing.start_date = start_date
            if next_renewal_date:
                existing.next_renewal_date = next_renewal_date
            existing.renewal_type = renewal_type
            existing.status = status
            if note:
                existing.note = f"{existing.note}\n{note}" if existing.note else note
            updated_count += 1
            target_sub = existing
        else:
            new_sub = Subscription(
                organization_id=actor.organization_id,
                user_id=actor.id,
                provider=provider.strip().lower(),
                name=name.strip(),
                plan=plan.strip() if plan else None,
                amount=float(amount) if amount is not None else None,
                currency=currency,
                billing_interval=billing_interval,
                start_date=start_date,
                next_renewal_date=next_renewal_date,
                status=status,
                renewal_type=renewal_type,
                source="bulk_import",
                note=note.strip() if note else None,
            )
            db.add(new_sub)
            db.flush()
            target_sub = new_sub
            imported_count += 1

        # If seats/capacity was specified, create initial license pool if none exists
        if seats_raw:
            try:
                capacity_int = int(seats_raw)
                if capacity_int > 0:
                    existing_lic = (
                        db.query(SubscriptionLicense)
                        .filter(
                            SubscriptionLicense.organization_id == actor.organization_id,
                            SubscriptionLicense.subscription_id == target_sub.id,
                        )
                        .first()
                    )
                    if not existing_lic:
                        db.add(
                            SubscriptionLicense(
                                organization_id=actor.organization_id,
                                subscription_id=target_sub.id,
                                reference=f"{target_sub.name} Seat Pool",
                                capacity=capacity_int,
                                status="ACTIVE",
                            )
                        )
            except Exception:
                pass

    db.commit()
    record_audit(
        db,
        actor,
        "subscription.bulk_import",
        "subscription",
        actor.organization_id,
        {
            "imported": imported_count,
            "updated": updated_count,
            "errors": len(errors),
            "filename": filename,
        },
    )

    return {
        "success": True,
        "imported": imported_count,
        "updated": updated_count,
        "total_processed": imported_count + updated_count,
        "errors": errors,
    }


def generate_subscription_template_bytes(fmt: str = "xlsx") -> Tuple[bytes, str, str]:
    """Generate sample subscription CSV or XLSX template containing realistic SaaS test cases."""
    headers = [
        "provider",
        "name",
        "plan",
        "amount",
        "currency",
        "billing_interval",
        "renewal_type",
        "start_date",
        "next_renewal_date",
        "status",
        "seats",
        "note",
    ]

    today = date.today()
    tomorrow = today.replace(day=today.day + 1) if today.day < 28 else today
    # Robust tomorrow & 30-day calculation
    from datetime import timedelta
    date_tomorrow = (today + timedelta(days=1)).isoformat()
    date_30d = (today + timedelta(days=30)).isoformat()
    date_60d = (today + timedelta(days=60)).isoformat()
    date_90d = (today + timedelta(days=90)).isoformat()
    date_180d = (today + timedelta(days=180)).isoformat()

    sample_rows = [
        # Test Case 1: 1 Day Prior + AUTOPAY
        (
            "github",
            "GitHub Enterprise",
            "Enterprise Cloud (50 seats)",
            "1050.00",
            "USD",
            "monthly",
            "AUTOPAY",
            (today - timedelta(days=335)).isoformat(),
            date_tomorrow,
            "ACTIVE",
            "50",
            "Corporate Amex ending in 4092. Renews tomorrow (1-day prior alert test case).",
        ),
        # Test Case 2: 1 Day Prior + MANUAL
        (
            "figma",
            "Figma Enterprise Suite",
            "Organization & FigJam",
            "18000.00",
            "USD",
            "annual",
            "MANUAL",
            (today - timedelta(days=364)).isoformat(),
            date_tomorrow,
            "ACTIVE",
            "35",
            "Manual Invoice Net-30. Purchase Order PO-2024-892 required (1-day prior alert test case).",
        ),
        # Test Case 3: 1 Month (30 Days) Prior + AUTOPAY
        (
            "slack",
            "Slack Enterprise Grid",
            "Enterprise Grid Tier 1",
            "12500.00",
            "USD",
            "annual",
            "AUTOPAY",
            (today - timedelta(days=335)).isoformat(),
            date_30d,
            "ACTIVE",
            "60",
            "Auto-renews via billing profile in 30 days (1-month prior alert test case).",
        ),
        # Test Case 4: 1 Month (30 Days) Prior + MANUAL
        (
            "datadog",
            "Datadog APM & Infra",
            "Pro Infrastructure (50 hosts)",
            "24000.00",
            "USD",
            "annual",
            "MANUAL",
            (today - timedelta(days=335)).isoformat(),
            date_30d,
            "ACTIVE",
            "50",
            "Vendor contract renewal quote required 30 days prior (1-month prior alert test case).",
        ),
        # Test Case 5: 60 Days Active + AUTOPAY
        (
            "openai",
            "OpenAI ChatGPT Team & API",
            "Team Tier 4 Usage Tier",
            "750.00",
            "USD",
            "monthly",
            "AUTOPAY",
            (today - timedelta(days=120)).isoformat(),
            date_60d,
            "ACTIVE",
            "25",
            "Auto-reload active with backup card.",
        ),
        # Test Case 6: 90 Days Active + AUTOPAY
        (
            "google",
            "Google Workspace Enterprise",
            "Enterprise Plus with Gemini",
            "7200.00",
            "USD",
            "annual",
            "AUTOPAY",
            (today - timedelta(days=275)).isoformat(),
            date_90d,
            "ACTIVE",
            "65",
            "Primary domain Google Workspace directory.",
        ),
        # Test Case 7: 180 Days Active + MANUAL
        (
            "microsoft",
            "Microsoft 365 E5",
            "Enterprise E5 Compliance Suite",
            "21600.00",
            "USD",
            "annual",
            "MANUAL",
            (today - timedelta(days=185)).isoformat(),
            date_180d,
            "ACTIVE",
            "40",
            "Enterprise agreement with Microsoft reseller.",
        ),
    ]

    if fmt.lower() == "csv":
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(headers)
        for r in sample_rows:
            writer.writerow(r)
        return out.getvalue().encode("utf-8"), "text/csv", "unisora_subscriptions_template.csv"

    # XLSX format
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Subscriptions"
    ws.views.sheetView[0].showGridLines = True

    header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    center = Alignment(horizontal="center", vertical="center")
    left = Alignment(horizontal="left", vertical="center")
    thin_border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0"),
    )

    ws.append(headers)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = thin_border
    ws.row_dimensions[1].height = 28

    data_font = Font(name="Arial", size=9)
    for row_idx, data_row in enumerate(sample_rows, start=2):
        ws.append(data_row)
        ws.row_dimensions[row_idx].height = 20
        for col_idx in range(1, len(data_row) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = data_font
            cell.alignment = left
            cell.border = thin_border

    col_widths = {
        "A": 16, "B": 28, "C": 30, "D": 14, "E": 12, "F": 16,
        "G": 16, "H": 14, "I": 18, "J": 14, "K": 10, "L": 45,
    }
    for col_letter, width in col_widths.items():
        ws.column_dimensions[col_letter].width = width

    bio = io.BytesIO()
    wb.save(bio)
    return (
        bio.getvalue(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "unisora_subscriptions_template.xlsx",
    )
