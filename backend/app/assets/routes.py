import io
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.policies import require_admin
from app.database.models import Asset, AssetAssignment, AssetMaintenance, User
from app.database.session import get_db
from app.assets.schemas import (
    AssetAssignmentCreate,
    AssetAssignmentResponse,
    AssetBulkImportResponse,
    AssetCreate,
    AssetResponse,
    AssetAssignmentReturn,
    AssetUpdate,
    MaintenanceCreate,
    MaintenanceResponse,
)
from app.assets.service import add_maintenance, assign_asset, get_asset, return_asset
from app.assets.csv_import import (
    generate_sample_asset_csv,
    generate_sample_asset_excel,
    process_asset_bulk_import,
)

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.get("", response_model=list[AssetResponse])
def list_assets(status_filter: str | None = Query(default=None, alias="status"), asset_type: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Asset).filter(Asset.organization_id == current_user.organization_id)
    if status_filter: query = query.filter(Asset.status == status_filter.upper())
    if asset_type: query = query.filter(Asset.asset_type == asset_type)
    return query.order_by(Asset.created_at.desc()).all()


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    item = Asset(organization_id=current_user.organization_id, **payload.model_dump())
    db.add(item)
    try: db.commit(); db.refresh(item); return item
    except IntegrityError: db.rollback(); raise HTTPException(409, "Asset tag already exists in this organization.")


@router.post("/import-csv", response_model=AssetBulkImportResponse)
@router.post("/import", response_model=AssetBulkImportResponse)
async def import_assets_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    if not file.filename:
        raise HTTPException(400, "A valid file is required.")
    fname = file.filename.lower()
    if not (fname.endswith(".csv") or fname.endswith(".xlsx") or fname.endswith(".xls")):
        raise HTTPException(400, "Only CSV (.csv) and Excel (.xlsx, .xls) files are supported.")
    try:
        content = await file.read()
        result = process_asset_bulk_import(content, file.filename, db, current_user)
        return result
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to import IT asset file: {str(e)}")


@router.get("/sample-template")
def download_asset_sample_template(
    format: str = Query("csv", pattern="^(csv|excel|xlsx)$"),
):
    fmt = format.lower()
    if fmt in ("excel", "xlsx"):
        excel_bytes = generate_sample_asset_excel()
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=unisora_it_assets_sample_template.xlsx"},
        )
    else:
        csv_str = generate_sample_asset_csv()
        return Response(
            content=csv_str,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=unisora_it_assets_sample_template.csv"},
        )



@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset_route(asset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = get_asset(db, current_user, asset_id)
    if not item: raise HTTPException(404, "Asset not found.")
    return item


@router.patch("/{asset_id}", response_model=AssetResponse)
def update_asset(asset_id: int, payload: AssetUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    item = get_asset(db, current_user, asset_id)
    if not item: raise HTTPException(404, "Asset not found.")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(item, key, value)
    db.commit(); db.refresh(item); return item


@router.post("/{asset_id}/assignments", response_model=AssetAssignmentResponse, status_code=status.HTTP_201_CREATED)
def assign_asset_route(asset_id: int, payload: AssetAssignmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    item = get_asset(db, current_user, asset_id)
    if not item: raise HTTPException(404, "Asset not found.")
    try:
        assignment = assign_asset(db, current_user, item, payload.user_id, expected_return_at=payload.expected_return_at, condition_at_issue=payload.condition_at_issue, handover_notes=payload.handover_notes)
        db.commit(); db.refresh(assignment); return assignment
    except ValueError as exc:
        db.rollback(); raise HTTPException(409, str(exc))


@router.get("/{asset_id}/assignments", response_model=list[AssetAssignmentResponse])
def list_asset_assignments(asset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = get_asset(db, current_user, asset_id)
    if not item: raise HTTPException(404, "Asset not found.")
    assignments = db.query(AssetAssignment).filter(AssetAssignment.asset_id == asset_id, AssetAssignment.organization_id == current_user.organization_id).order_by(AssetAssignment.assigned_at.desc()).all()
    user_map = {u.id: u for u in db.query(User).filter(User.organization_id == current_user.organization_id).all()}
    result: list[AssetAssignmentResponse] = []
    for a in assignments:
        resp = AssetAssignmentResponse.model_validate(a)
        u = user_map.get(a.user_id)
        if u:
            resp.user_name = u.display_name
            resp.user_email = u.email
            resp.user_employee_id = u.employee_id
        result.append(resp)
    return result



@router.post("/assignments/{assignment_id}/return", response_model=AssetAssignmentResponse)
def return_asset_route(assignment_id: int, payload: AssetAssignmentReturn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    assignment = db.query(AssetAssignment).filter(AssetAssignment.id == assignment_id, AssetAssignment.organization_id == current_user.organization_id, AssetAssignment.status == "ACTIVE").first()
    if not assignment: raise HTTPException(404, "Active asset assignment not found.")
    return_asset(db, current_user, assignment, payload.condition_at_return, payload.handover_notes)
    db.commit(); db.refresh(assignment); return assignment


@router.post("/{asset_id}/maintenance", response_model=MaintenanceResponse, status_code=status.HTTP_201_CREATED)
def create_maintenance(asset_id: int, payload: MaintenanceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    asset = get_asset(db, current_user, asset_id)
    if not asset: raise HTTPException(404, "Asset not found.")
    item = add_maintenance(db, current_user, asset, payload.model_dump())
    db.commit(); db.refresh(item); return item


@router.get("/{asset_id}/maintenance", response_model=list[MaintenanceResponse])
def list_maintenance(asset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    asset = get_asset(db, current_user, asset_id)
    if not asset: raise HTTPException(404, "Asset not found.")
    return db.query(AssetMaintenance).filter(AssetMaintenance.asset_id == asset_id, AssetMaintenance.organization_id == current_user.organization_id).order_by(AssetMaintenance.performed_at.desc()).all()

