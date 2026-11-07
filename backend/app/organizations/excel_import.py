"""
Excel workbook import parser for company onboarding.
Parses Company, Departments, Employees, and IT Assets sheets.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Any

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


REQUIRED_COMPANY_COLS = {"company_name"}
REQUIRED_DEPT_COLS = {"department_name"}
REQUIRED_ASSET_COLS = {"asset_tag", "name"}

OPTIONAL_COMPANY_COLS = {
    "legal_name", "industry", "company_size", "website",
    "company_email", "company_phone", "country", "state",
    "city", "address", "postal_code", "tax_registration_number",
}
OPTIONAL_EMPLOYEE_COLS = {
    "employee_id", "full_name", "email", "phone_number",
    "department_name", "joining_date",
}
OPTIONAL_ASSET_COLS = {
    "asset_type", "manufacturer", "model", "serial_number",
    "purchase_cost", "currency", "location", "assigned_to",
}


@dataclass
class ParsedCompany:
    company_name: str = ""
    legal_name: str | None = None
    industry: str | None = None
    company_size: str | None = None
    website: str | None = None
    company_email: str | None = None
    company_phone: str | None = None
    country: str | None = None
    state: str | None = None
    city: str | None = None
    address: str | None = None
    postal_code: str | None = None
    tax_registration_number: str | None = None


@dataclass
class ParsedDepartment:
    name: str = ""
    description: str | None = None


@dataclass
class ParsedEmployee:
    employee_id: str = ""
    full_name: str = ""
    email: str = ""
    phone_number: str | None = None
    department_name: str | None = None
    joining_date: str | None = None


@dataclass
class ParsedAsset:
    asset_tag: str = ""
    name: str = ""
    asset_type: str = "Laptop"
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    purchase_cost: str | None = None
    currency: str = "USD"
    location: str | None = None
    assigned_to: str | None = None  # Email or employee_id


@dataclass
class ParsedSubscription:
    provider: str = ""
    name: str = ""
    plan: str | None = None
    amount: str | None = None
    currency: str = "USD"
    billing_interval: str = "monthly"
    renewal_type: str = "AUTOPAY"
    start_date: str | None = None
    next_renewal_date: str | None = None
    status: str = "ACTIVE"
    note: str | None = None


@dataclass
class ParsedIntegration:
    provider_id: str = ""
    provider_name: str = ""
    category: str = "cloud"
    status: str = "CONNECTED"
    account_or_tenant_id: str | None = None
    notes: str | None = None


@dataclass
class ImportPreview:
    company: ParsedCompany | None = None
    departments: list[ParsedDepartment] = field(default_factory=list)
    employees: list[ParsedEmployee] = field(default_factory=list)
    assets: list[ParsedAsset] = field(default_factory=list)
    subscriptions: list[ParsedSubscription] = field(default_factory=list)
    integrations: list[ParsedIntegration] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    valid: bool = True


def _cell_str(cell: Any) -> str | None:
    if cell is None:
        return None
    v = str(cell).strip()
    return v if v else None


def _normalize_header(h: Any) -> str:
    if h is None:
        return ""
    return str(h).strip().lower().replace(" ", "_").replace("-", "_")


def parse_excel_workbook(content: bytes) -> ImportPreview:
    if not HAS_OPENPYXL:
        preview = ImportPreview()
        preview.errors.append("openpyxl is not installed on the server.")
        preview.valid = False
        return preview

    preview = ImportPreview()

    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:
        preview.errors.append(f"Could not open Excel file: {exc}")
        preview.valid = False
        return preview

    sheet_names_lower = {name.strip().lower(): name for name in wb.sheetnames}

    # ── 1. Company sheet ────────────────────────────────────────────────────────
    company_key = next((k for k in sheet_names_lower if "company" in k or "organization" in k), None)
    if company_key is None:
        preview.errors.append("No 'Company' sheet found in the workbook.")
        preview.valid = False
    else:
        ws = wb[sheet_names_lower[company_key]]
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) < 2:
            preview.errors.append("Company sheet must have a header row and at least one data row.")
            preview.valid = False
        else:
            headers = [_normalize_header(h) for h in rows[0]]
            # Fallback aliases for company header
            headers = [
                "company_name" if h in ("name", "organization", "organization_name", "company") else h
                for h in headers
            ]
            missing = REQUIRED_COMPANY_COLS - set(headers)
            if missing:
                preview.errors.append(f"Company sheet is missing required columns: {', '.join(sorted(missing))}")
                preview.valid = False
            else:
                row = rows[1]
                row_dict = {headers[i]: _cell_str(row[i]) for i in range(len(headers))}
                company_name = row_dict.get("company_name")
                if not company_name:
                    preview.errors.append("Company sheet: 'company_name' is empty in the first data row.")
                    preview.valid = False
                else:
                    preview.company = ParsedCompany(
                        company_name=company_name,
                        legal_name=row_dict.get("legal_name"),
                        industry=row_dict.get("industry"),
                        company_size=row_dict.get("company_size"),
                        website=row_dict.get("website"),
                        company_email=row_dict.get("company_email"),
                        company_phone=row_dict.get("company_phone"),
                        country=row_dict.get("country"),
                        state=row_dict.get("state"),
                        city=row_dict.get("city"),
                        address=row_dict.get("address"),
                        postal_code=row_dict.get("postal_code"),
                        tax_registration_number=row_dict.get("tax_registration_number"),
                    )

    # ── 2. Departments sheet ───────────────────────────────────────────────────
    dept_key = next((k for k in sheet_names_lower if "department" in k), None)
    if dept_key is None:
        preview.warnings.append("No 'Departments' sheet found. No departments will be imported.")
    else:
        ws = wb[sheet_names_lower[dept_key]]
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) < 2:
            preview.warnings.append("Departments sheet has no data rows.")
        else:
            headers = [_normalize_header(h) for h in rows[0]]
            headers = [
                "department_name" if h in ("name", "department", "dept_name", "dept") else h
                for h in headers
            ]
            missing = REQUIRED_DEPT_COLS - set(headers)
            if missing:
                preview.errors.append(f"Departments sheet is missing required columns: {', '.join(sorted(missing))}")
                preview.valid = False
            else:
                seen_names: set[str] = set()
                for idx, row in enumerate(rows[1:], start=2):
                    row_dict = {headers[i]: _cell_str(row[i]) for i in range(len(headers))}
                    name = row_dict.get("department_name")
                    if not name:
                        continue
                    if name.lower() in seen_names:
                        preview.warnings.append(f"Departments row {idx}: duplicate department '{name}', skipped.")
                        continue
                    seen_names.add(name.lower())
                    preview.departments.append(ParsedDepartment(
                        name=name,
                        description=row_dict.get("description"),
                    ))

    # ── 3. Employees sheet (optional) ──────────────────────────────────────────
    emp_key = next((k for k in sheet_names_lower if "employee" in k or "staff" in k or "people" in k), None)
    if emp_key:
        ws = wb[sheet_names_lower[emp_key]]
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) >= 2:
            headers = [_normalize_header(h) for h in rows[0]]
            seen_ids: set[str] = set()
            seen_emails: set[str] = set()
            for idx, row in enumerate(rows[1:], start=2):
                row_dict = {headers[i]: _cell_str(row[i]) for i in range(len(headers))}
                emp_id = row_dict.get("employee_id") or row_dict.get("id") or row_dict.get("emp_id")
                email = row_dict.get("email") or row_dict.get("work_email") or row_dict.get("email_address")
                name = row_dict.get("full_name") or row_dict.get("name") or row_dict.get("employee_name")
                if not emp_id and not email and not name:
                    continue
                if not emp_id or not email or not name:
                    preview.warnings.append(f"Employees row {idx}: missing employee_id, full_name or email — skipped.")
                    continue
                if emp_id in seen_ids:
                    preview.warnings.append(f"Employees row {idx}: duplicate employee_id '{emp_id}' — skipped.")
                    continue
                if email.lower() in seen_emails:
                    preview.warnings.append(f"Employees row {idx}: duplicate email '{email}' — skipped.")
                    continue
                seen_ids.add(emp_id)
                seen_emails.add(email.lower())
                preview.employees.append(ParsedEmployee(
                    employee_id=emp_id,
                    full_name=name,
                    email=email,
                    phone_number=row_dict.get("phone_number") or row_dict.get("phone"),
                    department_name=row_dict.get("department_name") or row_dict.get("department"),
                    joining_date=row_dict.get("joining_date") or row_dict.get("join_date"),
                ))

    # ── 4. IT Assets sheet (optional) ──────────────────────────────────────────
    asset_key = next((k for k in sheet_names_lower if "asset" in k or "hardware" in k or "equipment" in k or "devices" in k), None)
    if asset_key:
        ws = wb[sheet_names_lower[asset_key]]
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) >= 2:
            headers = [_normalize_header(h) for h in rows[0]]
            seen_tags: set[str] = set()
            for idx, row in enumerate(rows[1:], start=2):
                row_dict = {headers[i]: _cell_str(row[i]) for i in range(len(headers))}
                tag = row_dict.get("asset_tag") or row_dict.get("tag") or row_dict.get("asset_id")
                name = row_dict.get("name") or row_dict.get("asset_name") or row_dict.get("device_name") or row_dict.get("model")
                if not tag and not name:
                    continue
                if not tag or not name:
                    preview.warnings.append(f"Assets row {idx}: missing asset_tag or name — skipped.")
                    continue
                if tag in seen_tags:
                    preview.warnings.append(f"Assets row {idx}: duplicate asset_tag '{tag}' — skipped.")
                    continue
                seen_tags.add(tag)
                preview.assets.append(ParsedAsset(
                    asset_tag=tag,
                    name=name,
                    asset_type=row_dict.get("asset_type") or row_dict.get("type") or "Laptop",
                    manufacturer=row_dict.get("manufacturer") or row_dict.get("brand"),
                    model=row_dict.get("model"),
                    serial_number=row_dict.get("serial_number") or row_dict.get("serial"),
                    purchase_cost=row_dict.get("purchase_cost") or row_dict.get("cost"),
                    currency=row_dict.get("currency") or "USD",
                    location=row_dict.get("location"),
                    assigned_to=row_dict.get("assigned_to") or row_dict.get("assigned_employee"),
                ))

    # ── 5. Subscriptions sheet (optional) ──────────────────────────────────────
    sub_key = next((k for k in sheet_names_lower if "sub" in k or "saas" in k or "software" in k), None)
    if sub_key:
        ws = wb[sheet_names_lower[sub_key]]
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) >= 2:
            headers = [_normalize_header(h) for h in rows[0]]
            for idx, row in enumerate(rows[1:], start=2):
                row_dict = {headers[i]: _cell_str(row[i]) for i in range(len(headers))}
                name = row_dict.get("name") or row_dict.get("subscription_name") or row_dict.get("service")
                provider = row_dict.get("provider") or row_dict.get("vendor") or (name.split()[0].lower() if name else "")
                if not name:
                    continue
                raw_interval = row_dict.get("billing_interval") or row_dict.get("billing_cycle") or "monthly"
                interval = "annual" if "year" in raw_interval.lower() or "annu" in raw_interval.lower() else "monthly"
                raw_renewal_type = row_dict.get("renewal_type") or row_dict.get("autopay") or "AUTOPAY"
                renewal_type = "MANUAL" if any(k in raw_renewal_type.lower() for k in ("man", "inv", "po", "false", "no")) else "AUTOPAY"
                
                preview.subscriptions.append(ParsedSubscription(
                    provider=provider.lower().strip(),
                    name=name.strip(),
                    plan=row_dict.get("plan") or row_dict.get("tier"),
                    amount=row_dict.get("amount") or row_dict.get("cost") or row_dict.get("price"),
                    currency=(row_dict.get("currency") or "USD").upper()[:3],
                    billing_interval=interval,
                    renewal_type=renewal_type,
                    start_date=row_dict.get("start_date") or row_dict.get("contract_start"),
                    next_renewal_date=row_dict.get("next_renewal_date") or row_dict.get("renewal_date"),
                    status=(row_dict.get("status") or "ACTIVE").upper(),
                    note=row_dict.get("note") or row_dict.get("notes") or row_dict.get("description"),
                ))

    # ── 6. Integrations sheet (optional) ───────────────────────────────────────
    int_key = next((k for k in sheet_names_lower if "integrat" in k or "connection" in k), None)
    if int_key:
        ws = wb[sheet_names_lower[int_key]]
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) >= 2:
            headers = [_normalize_header(h) for h in rows[0]]
            for idx, row in enumerate(rows[1:], start=2):
                row_dict = {headers[i]: _cell_str(row[i]) for i in range(len(headers))}
                provider_id = row_dict.get("provider_id") or row_dict.get("provider") or row_dict.get("id")
                provider_name = row_dict.get("provider_name") or row_dict.get("name") or provider_id
                if not provider_id and not provider_name:
                    continue
                preview.integrations.append(ParsedIntegration(
                    provider_id=(provider_id or provider_name).lower().strip(),
                    provider_name=(provider_name or provider_id).strip(),
                    category=row_dict.get("category") or "cloud",
                    status=(row_dict.get("status") or "CONNECTED").upper(),
                    account_or_tenant_id=row_dict.get("account_or_tenant_id") or row_dict.get("tenant_id") or row_dict.get("account_id"),
                    notes=row_dict.get("notes") or row_dict.get("note") or row_dict.get("description"),
                ))

    wb.close()
    return preview
