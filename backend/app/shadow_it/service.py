import csv
import io
import json
import re
from datetime import date, datetime
from decimal import Decimal
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from app.database.models import ShadowItEntry, User
from app.shadow_it.vendors import match_vendor_from_description

DEMO_BANK_TRANSACTIONS = [
    {"date": "2026-11-04", "description": "OPENAI *CHATGPT PLUS SUBSCRIPTION SAN FRANCISCO CA", "amount": 1650.00, "currency": "INR"},
    {"date": "2026-11-06", "description": "GITHUB *COPILOT FOR BUSINESS SAN FRANCISCO", "amount": 3800.00, "currency": "INR"},
    {"date": "2026-11-08", "description": "NOTION LABS INC MONTHLY WORKSPACE PLAN", "amount": 2400.00, "currency": "INR"},
    {"date": "2026-11-10", "description": "FIGMA DESIGN SEATS TEAM TIER MONTHLY", "amount": 4200.00, "currency": "INR"},
    {"date": "2026-11-12", "description": "DIGITALOCEAN CLOUD DROPLET COMPUTE NYC", "amount": 5500.00, "currency": "INR"},
    {"date": "2026-11-14", "description": "CURSOR ANYSphere PRO CODING ASSISTANT", "amount": 1800.00, "currency": "INR"},
    {"date": "2026-11-15", "description": "SLACK TECHNOLOGIES PRO WORKSPACE RECURRING", "amount": 6200.00, "currency": "INR"},
    {"date": "2026-11-17", "description": "CANVA PTY LTD PRO TEAM SUBSCRIPTION", "amount": 1299.00, "currency": "INR"},
    {"date": "2026-11-18", "description": "LOOM VIDEO RECORDING MONTHLY BUSINESS", "amount": 1500.00, "currency": "INR"},
    {"date": "2026-11-20", "description": "STRIPE PAYMENTS BILLING FEE MONTHLY", "amount": 8900.00, "currency": "INR"},
    {"date": "2026-11-20", "description": "ANTHROPIC CLAUDE API REFILL TOKENS", "amount": 7500.00, "currency": "INR"},
]

def clean_amount(val: Any) -> float:
    if val is None:
        return 0.0
    s = str(val).strip()
    s = re.sub(r"[^\d.-]", "", s)
    try:
        return abs(float(s))
    except ValueError:
        return 0.0

def parse_date(val: Any) -> Optional[date]:
    if not val:
        return None
    s = str(val).strip()
    # Try ISO YYYY-MM-DD
    match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass
    # Try DD-MM-YYYY or MM-DD-YYYY
    match = re.search(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", s)
    if match:
        try:
            return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        except ValueError:
            pass
    return date.today()

def parse_csv_transactions(csv_content: str) -> List[Dict[str, Any]]:
    """Flexibly parses a bank or credit card CSV statement."""
    f = io.StringIO(csv_content.strip())
    # Detect dialect
    sample = csv_content[:1024]
    delimiter = ";" if ";" in sample and "," not in sample else ","
    reader = csv.reader(f, delimiter=delimiter)
    
    headers = None
    rows = []
    for r in reader:
        if not r or all(not cell.strip() for cell in r):
            continue
        if headers is None:
            # Check if this row looks like header
            joined = " ".join(r).lower()
            if any(k in joined for k in ["date", "desc", "particular", "narration", "amount", "debit"]):
                headers = [h.strip().lower() for h in r]
                continue
            else:
                # Fallback headers
                headers = [f"col_{i}" for i in range(len(r))]
        rows.append(r)

    if not headers:
        return []

    # Map header indices
    date_idx = None
    desc_idx = None
    amount_idx = None

    for i, h in enumerate(headers):
        if any(k in h for k in ["date", "txn_date", "transaction date", "value date"]):
            if date_idx is None: date_idx = i
        elif any(k in h for k in ["desc", "narration", "particular", "merchant", "details", "remarks"]):
            if desc_idx is None: desc_idx = i
        elif any(k in h for k in ["debit", "withdrawal", "amount", "spend", "cost"]):
            if amount_idx is None: amount_idx = i

    # Fallbacks if columns not identified by name
    if desc_idx is None and len(headers) >= 2:
        desc_idx = 1
    if amount_idx is None and len(headers) >= 3:
        amount_idx = 2
    if date_idx is None:
        date_idx = 0

    transactions = []
    for r in rows:
        desc = r[desc_idx] if desc_idx is not None and desc_idx < len(r) else ""
        amt_str = r[amount_idx] if amount_idx is not None and amount_idx < len(r) else "0"
        dt_str = r[date_idx] if date_idx is not None and date_idx < len(r) else ""

        amt = clean_amount(amt_str)
        if amt > 0 and desc:
            transactions.append({
                "date": parse_date(dt_str) or date.today(),
                "description": desc.strip(),
                "amount": amt,
                "currency": "INR",
            })

    return transactions

def process_and_upsert_transactions(
    db: Session,
    actor: User,
    transactions: List[Dict[str, Any]],
) -> Tuple[int, int, List[ShadowItEntry]]:
    """Analyzes transactions, matches SaaS vendors, and saves or updates ShadowItEntry records."""
    matched_groups: Dict[str, Dict[str, Any]] = {}

    for tx in transactions:
        match = match_vendor_from_description(tx["description"])
        if not match:
            continue
        v_name = match["vendor_name"]
        if v_name not in matched_groups:
            matched_groups[v_name] = {
                "vendor_name": v_name,
                "category": match["category"],
                "risk_level": match["risk_level"],
                "total_amount": 0.0,
                "currency": tx.get("currency", "INR"),
                "count": 0,
                "first_seen": tx["date"],
                "last_seen": tx["date"],
                "raw_descriptions": set(),
            }
        g = matched_groups[v_name]
        g["total_amount"] += tx["amount"]
        g["count"] += 1
        g["raw_descriptions"].add(tx["description"])
        if tx["date"] < g["first_seen"]:
            g["first_seen"] = tx["date"]
        if tx["date"] > g["last_seen"]:
            g["last_seen"] = tx["date"]

    created_count = 0
    updated_count = 0
    resulting_entries: List[ShadowItEntry] = []

    for v_name, data in matched_groups.items():
        existing = db.query(ShadowItEntry).filter(
            ShadowItEntry.organization_id == actor.organization_id,
            ShadowItEntry.vendor_name == v_name,
        ).first()

        raw_desc_json = json.dumps(list(data["raw_descriptions"])[:10])

        if existing:
            existing.monthly_amount = Decimal(str(round(data["total_amount"], 2)))
            existing.transaction_count = data["count"]
            existing.last_seen = data["last_seen"]
            existing.raw_descriptions = raw_desc_json
            existing.risk_level = data["risk_level"]
            updated_count += 1
            resulting_entries.append(existing)
        else:
            entry = ShadowItEntry(
                organization_id=actor.organization_id,
                vendor_name=v_name,
                category=data["category"],
                monthly_amount=Decimal(str(round(data["total_amount"], 2))),
                currency=data["currency"],
                transaction_count=data["count"],
                first_seen=data["first_seen"],
                last_seen=data["last_seen"],
                risk_level=data["risk_level"],
                status="DISCOVERED",
                raw_descriptions=raw_desc_json,
            )
            db.add(entry)
            created_count += 1
            resulting_entries.append(entry)

    db.commit()
    for e in resulting_entries:
        db.refresh(e)

    return created_count, updated_count, resulting_entries

def get_shadow_it_stats(db: Session, org_id: int) -> Dict[str, Any]:
    entries = db.query(ShadowItEntry).filter(ShadowItEntry.organization_id == org_id).all()
    
    total_spend = sum(float(e.monthly_amount) for e in entries)
    high_risk = sum(1 for e in entries if e.risk_level == "HIGH")
    medium_risk = sum(1 for e in entries if e.risk_level == "MEDIUM")
    low_risk = sum(1 for e in entries if e.risk_level == "LOW")

    discovered = sum(1 for e in entries if e.status == "DISCOVERED")
    approved = sum(1 for e in entries if e.status == "APPROVED")
    blocked = sum(1 for e in entries if e.status == "BLOCKED")

    return {
        "total_monthly_spend": round(total_spend, 2),
        "currency": "INR",
        "vendor_count": len(entries),
        "high_risk_count": high_risk,
        "medium_risk_count": medium_risk,
        "low_risk_count": low_risk,
        "discovered_count": discovered,
        "approved_count": approved,
        "blocked_count": blocked,
    }
