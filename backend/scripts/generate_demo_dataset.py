#!/usr/bin/env python3
"""
Generate comprehensive, realistic SaaS Demo Datasets for UniSora:
- UniSora_Complete_SaaS_Demo_Dataset.xlsx
- UniSora_PRO_Sample_Onboarding.xlsx
- CSV exports for subscriptions, integrations, departments, employees, and assets.
"""
from __future__ import annotations

import csv
import io
import os
import shutil
from datetime import date, timedelta
from typing import Any, List, Tuple

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


def create_workbook():
    today = date.today()
    tomorrow = today + timedelta(days=1)
    in_30d = today + timedelta(days=30)
    in_60d = today + timedelta(days=60)
    in_90d = today + timedelta(days=90)
    in_120d = today + timedelta(days=120)
    in_180d = today + timedelta(days=180)
    in_210d = today + timedelta(days=210)
    in_270d = today + timedelta(days=270)

    fmt = lambda d: d.isoformat() if d else ""

    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    # Styles
    navy_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    indigo_fill = PatternFill(start_color="312E81", end_color="312E81", fill_type="solid")
    teal_fill = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid")
    amber_fill = PatternFill(start_color="D97706", end_color="D97706", fill_type="solid")
    gray_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

    header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    data_font = Font(name="Arial", size=9)
    bold_data_font = Font(name="Arial", size=9, bold=True)
    center = Alignment(horizontal="center", vertical="center")
    left = Alignment(horizontal="left", vertical="center")
    right = Alignment(horizontal="right", vertical="center")

    thin_border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0"),
    )

    def style_sheet(ws, headers, rows, header_fill, col_widths=None):
        ws.views.sheetView[0].showGridLines = True
        ws.append(headers)
        ws.row_dimensions[1].height = 28
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center
            cell.border = thin_border

        for r_idx, row_data in enumerate(rows, start=2):
            ws.append(list(row_data))
            ws.row_dimensions[r_idx].height = 22
            for c_idx in range(1, len(row_data) + 1):
                cell = ws.cell(row=r_idx, column=c_idx)
                cell.font = data_font
                cell.alignment = left
                cell.border = thin_border

        if col_widths:
            for col_idx, width in enumerate(col_widths, start=1):
                ws.column_dimensions[get_column_letter(col_idx)].width = width
        else:
            for col_idx in range(1, len(headers) + 1):
                ws.column_dimensions[get_column_letter(col_idx)].width = 20

    # 1. Company Sheet
    ws_company = wb.create_sheet(title="Company")
    company_headers = [
        "company_name", "legal_name", "industry", "company_size", "website",
        "company_email", "company_phone", "country", "state", "city",
        "address", "postal_code", "tax_registration_number"
    ]
    company_rows = [
        (
            "UniSora Technologies",
            "UniSora Global Technologies Inc.",
            "Technology & Software",
            "51–200 employees",
            "https://unisora.io",
            "ops@unisora.io",
            "+1 (555) 019-2834",
            "United States",
            "California",
            "San Francisco",
            "500 Howard Street, Suite 400",
            "94105",
            "US-94-3829102",
        )
    ]
    style_sheet(ws_company, company_headers, company_rows, navy_fill, [22, 32, 24, 18, 22, 24, 20, 16, 16, 18, 32, 14, 20])

    # 2. Departments Sheet
    ws_dept = wb.create_sheet(title="Departments")
    dept_headers = ["department_name", "description"]
    dept_rows = [
        ("Engineering", "Core software development, cloud infrastructure, DevOps, and microservices architecture"),
        ("Product & Design", "Product management, UI/UX design systems, user experience research, and prototyping"),
        ("Finance & Operations", "Accounting, SaaS procurement, audit, vendor relations, and billing governance"),
        ("People Operations (HR)", "Talent acquisition, employee lifecycle management, compliance, and workplace culture"),
        ("Sales & Marketing", "Revenue operations, growth marketing, client acquisition, and enterprise partnerships"),
        ("Security & Compliance", "InfoSec, SOC 2 Type II compliance, zero-trust access, and hardware fleet security"),
    ]
    style_sheet(ws_dept, dept_headers, dept_rows, indigo_fill, [26, 75])

    # 3. Employees Sheet
    ws_emp = wb.create_sheet(title="Employees")
    emp_headers = ["employee_id", "full_name", "email", "phone_number", "department_name", "joining_date"]
    emp_rows = [
        ("EMP-101", "Alex Morgan", "alex.morgan@unisora.test", "+1 (555) 011-2001", "Engineering", "2024-01-15"),
        ("EMP-102", "Elena Rostova", "elena.rostova@unisora.test", "+1 (555) 011-2002", "Product & Design", "2024-02-01"),
        ("EMP-103", "Marcus Vance", "marcus.vance@unisora.test", "+1 (555) 011-2003", "Finance & Operations", "2024-02-15"),
        ("EMP-104", "Sarah Jenkins", "sarah.jenkins@unisora.test", "+1 (555) 011-2004", "People Operations (HR)", "2024-03-01"),
        ("EMP-105", "David Kim", "david.kim@unisora.test", "+1 (555) 011-2005", "Sales & Marketing", "2024-03-15"),
        ("EMP-106", "Aisha Patel", "aisha.patel@unisora.test", "+1 (555) 011-2006", "Security & Compliance", "2024-04-01"),
    ]
    style_sheet(ws_emp, emp_headers, emp_rows, teal_fill, [16, 22, 30, 20, 26, 16])

    # 4. IT Assets Sheet (1-to-many hardware allocations)
    ws_assets = wb.create_sheet(title="Assets")
    asset_headers = [
        "asset_tag", "name", "asset_type", "manufacturer", "model",
        "serial_number", "purchase_cost", "currency", "location", "assigned_to"
    ]
    asset_rows = [
        # Alex Morgan (Engineering) - Laptop, Monitor, Headset, Mobile Testing Phone
        ("LT-101", "MacBook Pro 16 M3 Max", "Laptop", "Apple", "MacBookPro18,1", "C02G8491MD6R", "3499.00", "USD", "San Francisco HQ", "alex.morgan@unisora.test"),
        ("MN-101", "Dell UltraSharp 27 4K USB-C Hub", "Monitor", "Dell", "U2723QE", "SN-DLL-4412", "579.00", "USD", "Desk 4A", "alex.morgan@unisora.test"),
        ("HD-101", "Jabra Evolve2 65 Wireless ANC", "Headset", "Jabra", "Evolve2-65", "SN-JBR-9912", "249.00", "USD", "San Francisco HQ", "alex.morgan@unisora.test"),
        ("PH-101", "iPhone 15 Pro Enterprise Fleet", "Mobile Phone", "Apple", "A3102", "SN-APL-7744", "999.00", "USD", "San Francisco HQ", "alex.morgan@unisora.test"),

        # Elena Rostova (Product & Design) - Laptop, 5K Studio Display, Over-ear ANC Headset
        ("LT-102", "MacBook Air 15 M3", "Laptop", "Apple", "MacBookAir15,2", "C02G9102KD4T", "1699.00", "USD", "San Francisco HQ", "elena.rostova@unisora.test"),
        ("MN-102", "Apple Studio Display 27 5K", "Monitor", "Apple", "MK0U3LL/A", "SN-APL-5520", "1599.00", "USD", "Desk 4B", "elena.rostova@unisora.test"),
        ("HD-102", "Sony WH-1000XM5 ANC Headset", "Headset", "Sony", "WH-1000XM5", "SN-SNY-3319", "399.00", "USD", "San Francisco HQ", "elena.rostova@unisora.test"),

        # Marcus Vance (Finance & Ops) - ThinkPad X1 Carbon, Monitor
        ("LT-103", "ThinkPad X1 Carbon Gen 11", "Laptop", "Lenovo", "21HM000EUS", "PF482910J", "1850.00", "USD", "San Francisco HQ", "marcus.vance@unisora.test"),
        ("MN-103", "Dell 27 Video Conferencing Monitor", "Monitor", "Dell", "C2722DE", "SN-DLL-8819", "489.00", "USD", "Desk 2C", "marcus.vance@unisora.test"),

        # Sarah Jenkins (People Ops)
        ("LT-104", "MacBook Pro 14 M3 Pro", "Laptop", "Apple", "MacBookPro18,3", "C02G3301PD8M", "1999.00", "USD", "San Francisco HQ", "sarah.jenkins@unisora.test"),
        ("HD-104", "Poly Voyager Focus 2 ANC", "Headset", "Poly", "Voyager-F2", "SN-PLY-5521", "219.00", "USD", "San Francisco HQ", "sarah.jenkins@unisora.test"),

        # Available Spares in IT Storage
        ("LT-105", "Dell Latitude 5540 Core i7", "Laptop", "Dell", "5540-I7", "SN-DLL-1092", "1299.00", "USD", "IT Storage Room B", ""),
        ("MN-104", "LG 34 Curved UltraWide Monitor", "Monitor", "LG", "34WN80C-B", "SN-LG-9821", "549.00", "USD", "IT Storage Room B", ""),
        ("HD-105", "Jabra Evolve 40 Stereo USB", "Headset", "Jabra", "Evolve-40", "SN-JBR-1188", "89.00", "USD", "IT Storage Room B", ""),
    ]
    style_sheet(ws_assets, asset_headers, asset_rows, amber_fill, [14, 34, 16, 16, 18, 18, 16, 12, 22, 28])

    # 5. Subscriptions Sheet (Comprehensive SaaS test cases with Autopay vs Manual)
    ws_subs = wb.create_sheet(title="Subscriptions")
    subs_headers = [
        "provider", "name", "plan", "amount", "currency", "billing_interval",
        "renewal_type", "start_date", "next_renewal_date", "status", "seats", "note"
    ]
    subs_rows = [
        # TEST CASE 1: 1 Day Prior Renewal + AUTOPAY
        (
            "github",
            "GitHub Enterprise Cloud",
            "Enterprise Cloud (50 seats)",
            "1050.00",
            "USD",
            "monthly",
            "AUTOPAY",
            "2024-01-15",
            fmt(tomorrow),
            "ACTIVE",
            "50",
            "Corporate Amex ending 4092. Renews tomorrow via Auto-Pay (1-day prior alert test case).",
        ),
        # TEST CASE 2: 1 Day Prior Renewal + MANUAL
        (
            "figma",
            "Figma Enterprise Suite",
            "Organization & FigJam (35 seats)",
            "18000.00",
            "USD",
            "annual",
            "MANUAL",
            "2024-02-01",
            fmt(tomorrow),
            "ACTIVE",
            "35",
            "Manual Invoice Net-30. Purchase Order PO-2024-892 required before cutoff (1-day prior alert test case).",
        ),
        # TEST CASE 3: 1 Month (30 Days) Prior Renewal + AUTOPAY
        (
            "slack",
            "Slack Enterprise Grid",
            "Enterprise Grid Tier 1 (60 seats)",
            "12500.00",
            "USD",
            "annual",
            "AUTOPAY",
            "2024-01-01",
            fmt(in_30d),
            "ACTIVE",
            "60",
            "Auto-renews automatically via corporate billing profile in 30 days (1-month prior alert test case).",
        ),
        # TEST CASE 4: 1 Month (30 Days) Prior Renewal + MANUAL
        (
            "datadog",
            "Datadog APM & Infrastructure",
            "Enterprise Pro (50 hosts + Logs)",
            "24000.00",
            "USD",
            "annual",
            "MANUAL",
            "2024-01-01",
            fmt(in_30d),
            "ACTIVE",
            "50",
            "Vendor contract renewal quote and procurement sign-off required 30 days prior (1-month prior alert test case).",
        ),
        # TEST CASE 5: 60 Days Active + AUTOPAY
        (
            "openai",
            "OpenAI ChatGPT Team & API",
            "Team Tier 4 Usage Tier",
            "750.00",
            "USD",
            "monthly",
            "AUTOPAY",
            "2024-03-01",
            fmt(in_60d),
            "ACTIVE",
            "25",
            "Prepaid API balance auto-reload active with backup corporate card.",
        ),
        # TEST CASE 6: 90 Days Active + AUTOPAY
        (
            "google",
            "Google Workspace Enterprise",
            "Enterprise Plus with Gemini",
            "7200.00",
            "USD",
            "annual",
            "AUTOPAY",
            "2024-01-15",
            fmt(in_90d),
            "ACTIVE",
            "65",
            "Primary domain Google Workspace directory. Renews via Google Cloud Billing account.",
        ),
        # TEST CASE 7: 120 Days Active + MANUAL
        (
            "atlassian",
            "Atlassian Jira Software & Confluence",
            "Cloud Premium (100 users)",
            "16800.00",
            "USD",
            "annual",
            "MANUAL",
            "2024-02-15",
            fmt(in_120d),
            "ACTIVE",
            "100",
            "Annual enterprise agreement invoice with authorized Atlassian partner.",
        ),
        # TEST CASE 8: 180 Days Active + AUTOPAY
        (
            "aws",
            "AWS Business Support & Cloud Compute",
            "Business Support Tier Plan",
            "3200.00",
            "USD",
            "monthly",
            "AUTOPAY",
            "2024-01-01",
            fmt(in_180d),
            "ACTIVE",
            "15",
            "Direct monthly cloud billing auto-debit through AWS billing console.",
        ),
        # TEST CASE 9: 210 Days Active + MANUAL
        (
            "microsoft",
            "Microsoft 365 E5 Suite",
            "Enterprise E5 Compliance Suite",
            "21600.00",
            "USD",
            "annual",
            "MANUAL",
            "2024-02-15",
            fmt(in_210d),
            "ACTIVE",
            "40",
            "Enterprise agreement with Microsoft direct reseller. Wire invoice payment.",
        ),
        # TEST CASE 10: 270 Days Active + AUTOPAY
        (
            "notion",
            "Notion Enterprise Workspace",
            "Enterprise Plan with Notion AI",
            "3600.00",
            "USD",
            "annual",
            "AUTOPAY",
            "2024-03-01",
            fmt(in_270d),
            "ACTIVE",
            "50",
            "Company-wide wiki and project tracker. Auto-pay on file.",
        ),
        # TEST CASE 11: Cancelled Contract
        (
            "zoom",
            "Zoom Workplace Pro",
            "Business 50 Seats",
            "650.00",
            "USD",
            "monthly",
            "MANUAL",
            "2023-05-01",
            "",
            "CANCELLED",
            "0",
            "Cancelled in favor of Google Meet migration.",
        ),
    ]
    style_sheet(ws_subs, subs_headers, subs_rows, navy_fill, [14, 32, 28, 14, 12, 16, 16, 14, 18, 14, 10, 50])

    # 6. Integrations Sheet
    ws_intg = wb.create_sheet(title="Integrations")
    intg_headers = [
        "provider_id", "provider_name", "category", "status", "auth_type",
        "environment", "account_or_tenant_id", "allocated_spend_limit",
        "renewal_type", "renewal_notice_window", "notes"
    ]
    intg_rows = [
        ("aws", "Amazon Web Services", "cloud", "CONNECTED", "IAM Role / Access Key", "Production us-east-1", "arn:aws:iam::123456789012:root", "$15,000 / mo", "AUTOPAY", "30 days & 1 day prior", "Cost Explorer and Free Tier telemetry connected."),
        ("azure", "Microsoft Azure", "cloud", "CONNECTED", "Service Principal OAuth", "Production Tenant", "unisora-cloud.onmicrosoft.com", "$10,000 / mo", "AUTOPAY", "30 days & 1 day prior", "Azure subscriptions and Resource Group spend synced."),
        ("openai", "OpenAI / ChatGPT API", "ai", "CONNECTED", "Encrypted API Key", "Tier 4 Production", "org-unisora-production-ai", "$2,500 / mo", "AUTOPAY", "30 days & 1 day prior", "GPT-4o, o1, Text-Embedding-3 inference tracking."),
        ("anthropic", "Anthropic Claude", "ai", "CONNECTED", "Encrypted API Key", "Production API", "ant-org-unisora-demo", "$2,000 / mo", "AUTOPAY", "30 days & 1 day prior", "Claude 3.5 Sonnet and Haiku usage reporting."),
        ("gemini", "Google Gemini", "ai", "CONNECTED", "Google AI Studio API Key", "Production Project", "projects/unisora-demo-studio", "$1,500 / mo", "AUTOPAY", "30 days & 1 day prior", "Gemini 1.5 Pro and Flash token telemetry."),
        ("google-workspace", "Google Workspace", "productivity", "CONNECTED", "OAuth 2.0 Directory", "Enterprise Suite", "admin@unisora.io", "$1,000 / mo", "AUTOPAY", "30 days & 1 day prior", "65 active company user accounts and license seats."),
        ("slack", "Slack Enterprise Grid", "productivity", "CONNECTED", "Enterprise Grid Bot Token", "Primary Workspace", "T09283741-unisora", "$1,200 / mo", "AUTOPAY", "30 days & 1 day prior", "48 collaboration channels and employee accounts."),
        ("github", "GitHub Enterprise", "developer", "CONNECTED", "GitHub App / SAML SSO", "Organization Cloud", "unisora-technologies", "$1,500 / mo", "AUTOPAY", "30 days & 1 day prior", "12 private code repositories and 50 dev licenses."),
        ("datadog", "Datadog Infrastructure", "cloud", "CONNECTED", "Application API Key", "Production Observability", "datadog-unisora-prod", "$3,000 / mo", "MANUAL", "30 days & 1 day prior", "APM, host telemetry, and container log aggregation."),
        ("microsoft-365", "Microsoft 365", "productivity", "DISCONNECTED", "Microsoft Graph API", "Secondary Tenant", "m365-unisora-demo", "$2,000 / mo", "MANUAL", "30 days & 1 day prior", "Available for connection through OAuth."),
        ("stripe", "Stripe Billing & Payments", "billing", "DISCONNECTED", "Restricted API Key", "Live Production", "acct_1UnisoraProd992", "N/A", "MANUAL", "30 days & 1 day prior", "Available for invoicing and payment audit."),
    ]
    style_sheet(ws_intg, intg_headers, intg_rows, teal_fill, [18, 26, 16, 16, 24, 24, 30, 20, 16, 24, 45])

    # 7. Renewal_Alerts_Matrix Sheet (Documentation & Test Case Guide)
    ws_matrix = wb.create_sheet(title="Renewal_Alerts_Matrix")
    matrix_headers = [
        "test_case_id", "service_name", "provider", "billing_cycle",
        "renewal_type", "renewal_date", "days_remaining", "expected_alert_window",
        "alert_severity", "alert_title_preview", "alert_message_behavior"
    ]
    matrix_rows = [
        (
            "TC-REN-01",
            "GitHub Enterprise Cloud",
            "github",
            "monthly",
            "AUTOPAY",
            fmt(tomorrow),
            "1 day",
            "1-Day Prior Urgent Alert",
            "warning",
            "URGENT: GitHub Enterprise Cloud Auto-Renews Tomorrow (Auto-Pay)",
            "Alerts user that $1,050.00 will be auto-charged tomorrow to corporate card 4092. Prevents billing failure."
        ),
        (
            "TC-REN-02",
            "Figma Enterprise Suite",
            "figma",
            "annual",
            "MANUAL",
            fmt(tomorrow),
            "1 day",
            "1-Day Prior Urgent Alert",
            "warning",
            "ACTION REQUIRED: Figma Enterprise Suite Renews Tomorrow (Manual Invoice)",
            "Urgent action required! Notifies user that contract expires tomorrow and invoice must be settled immediately to prevent team deactivation."
        ),
        (
            "TC-REN-03",
            "Slack Enterprise Grid",
            "slack",
            "annual",
            "AUTOPAY",
            fmt(in_30d),
            "30 days",
            "1-Month Prior Advance Notice",
            "info",
            "Slack Enterprise Grid: 30-Day Renewal Notice (Auto-Pay)",
            "30-day advance notice that $12,500.00 will auto-charge in 1 month. Gives team time to review unassigned seats."
        ),
        (
            "TC-REN-04",
            "Datadog APM & Infrastructure",
            "datadog",
            "annual",
            "MANUAL",
            fmt(in_30d),
            "30 days",
            "1-Month Prior Advance Notice",
            "info",
            "Datadog APM & Infrastructure: 30-Day Renewal Notice (Manual Invoice)",
            "Reminds finance team that annual quote/purchase order ($24,000.00) must be approved 30 days prior."
        ),
        (
            "TC-REN-05",
            "OpenAI ChatGPT Team & API",
            "openai",
            "monthly",
            "AUTOPAY",
            fmt(in_60d),
            "60 days",
            "Normal Active (No Alert Yet)",
            "none",
            "—",
            "Active subscription; will trigger 30-day notice when clock reaches 30 days remaining."
        ),
        (
            "TC-REN-06",
            "Google Workspace Enterprise",
            "google",
            "annual",
            "AUTOPAY",
            fmt(in_90d),
            "90 days",
            "Normal Active (No Alert Yet)",
            "none",
            "—",
            "Active annual contract in standard active status."
        ),
    ]
    style_sheet(ws_matrix, matrix_headers, matrix_rows, indigo_fill, [14, 28, 14, 14, 16, 14, 16, 26, 16, 38, 55])

    return wb, subs_headers, subs_rows, intg_headers, intg_rows, dept_headers, dept_rows, emp_headers, emp_rows, asset_headers, asset_rows


def export_csv(filename, headers, rows):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for r in rows:
            writer.writerow(r)


def main():
    wb, s_h, s_r, i_h, i_r, d_h, d_r, e_h, e_r, a_h, a_r = create_workbook()

    # Paths to output
    os.makedirs("samples", exist_ok=True)
    os.makedirs("frontend/public", exist_ok=True)

    dest_xlsx = [
        "UniSora_PRO_Sample_Onboarding.xlsx",
        "samples/UniSora_PRO_Sample_Onboarding.xlsx",
        "frontend/public/UniSora_PRO_Sample_Onboarding.xlsx",
        "samples/UniSora_Complete_SaaS_Demo_Dataset.xlsx",
        "frontend/public/UniSora_Complete_SaaS_Demo_Dataset.xlsx",
    ]

    for p in dest_xlsx:
        wb.save(p)
        print(f"Saved Excel: {p}")

    # Export individual CSVs
    csv_mappings = [
        ("samples/subscriptions_demo_dataset.csv", s_h, s_r),
        ("frontend/public/subscriptions_demo_dataset.csv", s_h, s_r),
        ("samples/integrations_demo_dataset.csv", i_h, i_r),
        ("frontend/public/integrations_demo_dataset.csv", i_h, i_r),
        ("samples/departments_demo_dataset.csv", d_h, d_r),
        ("frontend/public/departments_demo_dataset.csv", d_h, d_r),
        ("samples/employees_demo_dataset.csv", e_h, e_r),
        ("frontend/public/employees_demo_dataset.csv", e_h, e_r),
        ("samples/assets_demo_dataset.csv", a_h, a_r),
        ("frontend/public/assets_demo_dataset.csv", a_h, a_r),
    ]

    for path, headers, rows in csv_mappings:
        export_csv(path, headers, rows)
        print(f"Saved CSV: {path}")


if __name__ == "__main__":
    main()
