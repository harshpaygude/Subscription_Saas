"""Subscription & SaaS Contract Bulk Import Processor for CSV and Excel files."""
from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.domain.entities import SubscriptionEntity, SubscriptionLicenseEntity
from app.domain.ports import AuditEventPort, LicenseRepository, SubscriptionRepository

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
    return "MANUAL" if any(k in s for k in ("manual", "invoice", "po", "wire", "check", "false", "no")) else "AUTOPAY"


def _normalize_status(val: Any) -> str:
    s = _clean_str(val).upper()
    if "CANCEL" in s:
        return "CANCELLED"
    if "ARCHIV" in s:
        return "ARCHIVED"
    return "ACTIVE"


def _find_field(row: Dict[str, str], candidates: List[str]) -> str:
    for c in candidates:
        if c in row and row[c]:
            return row[c]
    for key, val in row.items():
        for c in candidates:
            if c in key and val:
                return val
    return ""


def parse_tabular_data(content: bytes, filename: str) -> List[Dict[str, str]]:
    fn_lower = filename.lower()
    rows: List[Dict[str, str]] = []

    if fn_lower.endswith(".xlsx") or fn_lower.endswith(".xlsm") or fn_lower.endswith(".xltx"):
        if not HAS_OPENPYXL:
            raise ValueError("openpyxl is not installed for Excel file processing.")
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        sheet = next((wb[n] for n in wb.sheetnames if any(k in n.lower() for k in ("subscription", "saas", "license", "tools"))), wb.active)
        raw_rows = list(sheet.iter_rows(values_only=True))
    else:
        text = ""
        for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                text = content.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if not text:
            text = content.decode("utf-8", errors="replace")
        try:
            dialect = csv.Sniffer().sniff(text[:4096])
        except Exception:
            dialect = csv.excel
        raw_rows = list(csv.reader(io.StringIO(text), dialect))

    if not raw_rows:
        return []

    header_idx = 0
    for idx, row in enumerate(raw_rows):
        if not row:
            continue
        cells = [_normalize_key(str(c)) for c in row if c is not None]
        if any(h in cells for h in ("name", "service", "subscription_name", "provider", "vendor")):
            header_idx = idx
            break

    headers = [_normalize_key(str(c)) if c is not None else f"col_{i}" for i, c in enumerate(raw_rows[header_idx])]
    for row in raw_rows[header_idx + 1 :]:
        if not row or all(c is None or str(c).strip() == "" for c in row):
            continue
        row_dict = {headers[i]: _clean_str(cell) for i, cell in enumerate(row) if i < len(headers) and headers[i]}
        if row_dict:
            rows.append(row_dict)
    return rows


def process_subscription_bulk_import(
    *,
    organization_id: int,
    actor_id: int,
    subscriptions: SubscriptionRepository,
    licenses: LicenseRepository,
    audit: AuditEventPort,
    file_bytes: bytes,
    filename: str,
) -> Dict[str, Any]:
    rows = parse_tabular_data(file_bytes, filename)
    if not rows:
        raise ValueError("The uploaded file does not contain any readable subscription rows.")

    imported_count = 0
    updated_count = 0
    errors: List[str] = []
    now = datetime.utcnow()

    for row_num, row in enumerate(rows, start=2):
        name = _find_field(row, ["subscription_name", "service_name", "name", "service", "tool", "product"])
        provider = _find_field(row, ["provider", "vendor", "service_provider", "company", "source"])
        if not name:
            errors.append(f"Row {row_num}: Missing required subscription/service name.")
            continue
        if not provider:
            provider = name.split()[0].lower()

        plan = _find_field(row, ["plan", "tier", "plan_tier", "edition", "license_type"]) or None
        amount = _parse_amount(_find_field(row, ["amount", "cost", "price", "annual_cost", "monthly_cost", "spend"]))
        currency = (_find_field(row, ["currency", "curr"]) or "USD").strip().upper()[:3]
        billing_interval = _normalize_interval(_find_field(row, ["billing_interval", "billing_cycle", "interval", "cycle", "frequency"]))
        start_date = _parse_date(_find_field(row, ["start_date", "contract_start", "started_at", "contract_date"]))
        next_renewal_date = _parse_date(_find_field(row, ["next_renewal_date", "renewal_date", "renewal", "expires_at", "contract_end", "expiry_date"]))
        renewal_type = _normalize_renewal_type(_find_field(row, ["renewal_type", "renewal_mode", "autopay", "payment_method", "auto_renew", "pay_type"]))
        status = _normalize_status(_find_field(row, ["status", "subscription_status", "state"]))
        note = _find_field(row, ["note", "notes", "description", "comments", "payment_details"]) or None
        seats_raw = _find_field(row, ["seats", "licenses", "capacity", "seat_count", "users"])

        existing = subscriptions.find_by_provider_and_name(organization_id, provider.strip(), name.strip())
        if existing:
            existing.plan = plan or existing.plan
            if amount is not None:
                existing.amount = amount
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
            target_sub = subscriptions.save(existing)
            updated_count += 1
        else:
            target_sub = subscriptions.create(
                SubscriptionEntity(
                    id=None,
                    organization_id=organization_id,
                    user_id=actor_id,
                    provider=provider.strip().lower(),
                    name=name.strip(),
                    plan=plan.strip() if plan else None,
                    amount=amount,
                    currency=currency,
                    billing_interval=billing_interval,
                    start_date=start_date,
                    next_renewal_date=next_renewal_date,
                    status=status,
                    cancellation_date=None,
                    source="bulk_import",
                    note=note.strip() if note else None,
                    renewal_type=renewal_type,
                    created_at=now,
                    updated_at=now,
                )
            )
            imported_count += 1

        if seats_raw and target_sub.id is not None:
            try:
                cap = int(seats_raw)
                if cap > 0 and not licenses.list_by_subscription(target_sub.id, organization_id):
                    licenses.create(
                        SubscriptionLicenseEntity(
                            id=None,
                            organization_id=organization_id,
                            subscription_id=target_sub.id,
                            reference=f"{target_sub.name} Seat Pool",
                            capacity=cap,
                            status="ACTIVE",
                            created_at=now,
                            updated_at=now,
                        )
                    )
            except Exception:
                pass

    audit.record(
        organization_id=organization_id,
        actor_id=actor_id,
        action="subscription.bulk_import",
        entity_type="subscription",
        entity_id=organization_id,
        details={"imported": imported_count, "updated": updated_count, "errors": len(errors), "filename": filename},
    )
    return {
        "success": True,
        "imported": imported_count,
        "updated": updated_count,
        "total_processed": imported_count + updated_count,
        "errors": errors,
    }


def generate_subscription_template_bytes(fmt: str = "xlsx") -> Tuple[bytes, str, str]:
    headers = [
        "provider", "name", "plan", "amount", "currency", "billing_interval",
        "renewal_type", "start_date", "next_renewal_date", "status", "seats", "note",
    ]
    today = date.today()
    sample_rows = [
        ("github", "GitHub Enterprise", "Enterprise Cloud (50 seats)", "1050.00", "USD", "monthly", "AUTOPAY", (today - timedelta(days=335)).isoformat(), (today + timedelta(days=1)).isoformat(), "ACTIVE", "50", "Renews tomorrow"),
        ("figma", "Figma Enterprise Suite", "Organization & FigJam", "18000.00", "USD", "annual", "MANUAL", (today - timedelta(days=364)).isoformat(), (today + timedelta(days=1)).isoformat(), "ACTIVE", "35", "Manual Invoice Net-30"),
        ("slack", "Slack Enterprise Grid", "Enterprise Grid Tier 1", "12500.00", "USD", "annual", "AUTOPAY", (today - timedelta(days=335)).isoformat(), (today + timedelta(days=30)).isoformat(), "ACTIVE", "60", "Auto-renews in 30 days"),
        ("datadog", "Datadog APM & Infra", "Pro Infrastructure (50 hosts)", "24000.00", "USD", "annual", "MANUAL", (today - timedelta(days=335)).isoformat(), (today + timedelta(days=30)).isoformat(), "ACTIVE", "50", "Vendor quote required"),
        ("openai", "OpenAI ChatGPT Team & API", "Team Tier 4 Usage Tier", "750.00", "USD", "monthly", "AUTOPAY", (today - timedelta(days=120)).isoformat(), (today + timedelta(days=60)).isoformat(), "ACTIVE", "25", "Auto-reload active"),
    ]

    if fmt.lower() == "csv":
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(headers)
        writer.writerows(sample_rows)
        return out.getvalue().encode("utf-8"), "text/csv", "unisora_subscriptions_template.csv"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Subscriptions"
    ws.append(headers)
    header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    center = Alignment(horizontal="center", vertical="center")
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
    for data_row in sample_rows:
        ws.append(data_row)
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "unisora_subscriptions_template.xlsx"
