from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.orm import Session
from app.auth.dependencies import get_current_user
from app.database.models import User, ShadowItEntry
from app.database.session import get_db
from app.shadow_it.schemas import (
    ShadowItEntryResponse,
    ShadowItStatsResponse,
    ShadowItUploadResponse,
)
from app.shadow_it.service import (
    parse_csv_transactions,
    process_and_upsert_transactions,
    get_shadow_it_stats,
    DEMO_BANK_TRANSACTIONS,
)

router = APIRouter(prefix="/shadow-it", tags=["Shadow IT Discovery"])

@router.get("/stats", response_model=ShadowItStatsResponse)
def stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_shadow_it_stats(db, current_user.organization_id)

@router.get("/entries", response_model=List[ShadowItEntryResponse])
def list_entries(
    status: Optional[str] = Query(None),
    risk: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(ShadowItEntry).filter(ShadowItEntry.organization_id == current_user.organization_id)
    if status and status.upper() != "ALL":
        q = q.filter(ShadowItEntry.status == status.upper())
    if risk and risk.upper() != "ALL":
        q = q.filter(ShadowItEntry.risk_level == risk.upper())
    return q.order_by(ShadowItEntry.monthly_amount.desc()).all()

@router.post("/upload", response_model=ShadowItUploadResponse)
async def upload_bank_statement(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        content_bytes = await file.read()
        content = content_bytes.decode("utf-8", errors="replace")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read uploaded CSV: {exc}")

    transactions = parse_csv_transactions(content)
    if not transactions:
        raise HTTPException(
            status_code=422,
            detail="No recognizable transactions found in the CSV. Please ensure the file has Date, Description, and Amount columns."
        )

    created, updated, entries = process_and_upsert_transactions(db, current_user, transactions)
    total_spend = sum(float(e.monthly_amount) for e in entries)

    return {
        "processed_transactions": len(transactions),
        "matched_vendors_count": len(entries),
        "new_entries_created": created,
        "entries_updated": updated,
        "total_monthly_spend_discovered": round(total_spend, 2),
        "currency": "INR",
        "entries": entries,
    }

@router.post("/demo-scan", response_model=ShadowItUploadResponse)
def run_demo_scan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Instantly scans realistic company credit card transactions for quick testing & demo."""
    created, updated, entries = process_and_upsert_transactions(db, current_user, DEMO_BANK_TRANSACTIONS)
    total_spend = sum(float(e.monthly_amount) for e in entries)

    return {
        "processed_transactions": len(DEMO_BANK_TRANSACTIONS),
        "matched_vendors_count": len(entries),
        "new_entries_created": created,
        "entries_updated": updated,
        "total_monthly_spend_discovered": round(total_spend, 2),
        "currency": "INR",
        "entries": entries,
    }

@router.put("/entries/{entry_id}/approve", response_model=ShadowItEntryResponse)
def approve_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = db.query(ShadowItEntry).filter(
        ShadowItEntry.id == entry_id,
        ShadowItEntry.organization_id == current_user.organization_id,
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Shadow IT record not found.")
    entry.status = "APPROVED"
    db.commit()
    db.refresh(entry)
    return entry

@router.put("/entries/{entry_id}/block", response_model=ShadowItEntryResponse)
def block_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = db.query(ShadowItEntry).filter(
        ShadowItEntry.id == entry_id,
        ShadowItEntry.organization_id == current_user.organization_id,
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Shadow IT record not found.")
    entry.status = "BLOCKED"
    db.commit()
    db.refresh(entry)
    return entry

@router.delete("/entries/{entry_id}", status_code=204)
def delete_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = db.query(ShadowItEntry).filter(
        ShadowItEntry.id == entry_id,
        ShadowItEntry.organization_id == current_user.organization_id,
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Shadow IT record not found.")
    db.delete(entry)
    db.commit()
    return None
