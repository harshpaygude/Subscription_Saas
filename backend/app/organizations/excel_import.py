"""
Excel workbook import parser for company onboarding.
Parses Company, Departments, and Employees sheets.
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
OPTIONAL_COMPANY_COLS = {
    "legal_name", "industry", "company_size", "website",
    "company_email", "company_phone", "country", "state",
    "city", "address", "postal_code", "tax_registration_number",
}
OPTIONAL_EMPLOYEE_COLS = {
    "employee_id", "full_name", "email", "phone_number",
    "department_name", "joining_date",
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
class ImportPreview:
    company: ParsedCompany | None = None
    departments: list[ParsedDepartment] = field(default_factory=list)
    employees: list[ParsedEmployee] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    valid: bool = True


def _cell_str(cell: Any) -> str | None:
    if cell is None:
        return None
    v = str(cell).strip()
    return v if v else None


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

    # ── Company sheet ──────────────────────────────────────────────────────────
    company_key = next((k for k in sheet_names_lower if "company" in k), None)
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
            headers = [str(h).strip().lower() if h is not None else "" for h in rows[0]]
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

    # ── Departments sheet ──────────────────────────────────────────────────────
    dept_key = next((k for k in sheet_names_lower if "department" in k), None)
    if dept_key is None:
        preview.warnings.append("No 'Departments' sheet found. No departments will be imported.")
    else:
        ws = wb[sheet_names_lower[dept_key]]
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) < 2:
            preview.warnings.append("Departments sheet has no data rows.")
        else:
            headers = [str(h).strip().lower() if h is not None else "" for h in rows[0]]
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
                        preview.warnings.append(f"Departments row {idx}: empty department_name, skipped.")
                        continue
                    if name.lower() in seen_names:
                        preview.warnings.append(f"Departments row {idx}: duplicate department '{name}', skipped.")
                        continue
                    seen_names.add(name.lower())
                    preview.departments.append(ParsedDepartment(
                        name=name,
                        description=row_dict.get("description"),
                    ))

    # ── Employees sheet (optional) ─────────────────────────────────────────────
    emp_key = next((k for k in sheet_names_lower if "employee" in k), None)
    if emp_key:
        ws = wb[sheet_names_lower[emp_key]]
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) >= 2:
            headers = [str(h).strip().lower() if h is not None else "" for h in rows[0]]
            seen_ids: set[str] = set()
            seen_emails: set[str] = set()
            for idx, row in enumerate(rows[1:], start=2):
                row_dict = {headers[i]: _cell_str(row[i]) for i in range(len(headers))}
                emp_id = row_dict.get("employee_id")
                email = row_dict.get("email")
                name = row_dict.get("full_name")
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
                    phone_number=row_dict.get("phone_number"),
                    department_name=row_dict.get("department_name"),
                    joining_date=row_dict.get("joining_date"),
                ))

    wb.close()
    return preview
