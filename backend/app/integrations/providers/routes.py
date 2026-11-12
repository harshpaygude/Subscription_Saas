"""API routes for provider credential connections (GitHub, Slack, Stripe, GitLab, GCP, etc.)."""
from datetime import datetime
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.models import Connection, User
from app.database.session import get_db
from app.integrations.credentials import (
    CredentialStorageError,
    decrypt_credentials,
    encrypt_credentials,
)
from app.integrations.providers.client import (
    ProviderVerificationError,
    verify_provider_credentials,
)
from app.integrations.providers.schemas import (
    ProviderConnectRequest,
    ProviderConnectResponse,
    ProviderConnectionResponse,
    ProviderDetailsResponse,
    ProviderTestResponse,
)

router = APIRouter(prefix="/integrations", tags=["Service Integrations"])


def _standardize_provider_name(provider_id: str) -> str:
    return provider_id.upper().replace("-", "_")


def _parse_scopes_profile(scopes: Optional[str]) -> Dict[str, Any]:
    if not scopes:
        return {}
    try:
        return json.loads(scopes)
    except Exception:
        return {"raw_scopes": scopes}


def _to_response(conn: Connection) -> ProviderConnectionResponse:
    profile = _parse_scopes_profile(conn.scopes)
    return ProviderConnectionResponse(
        id=conn.id,
        provider=conn.provider,
        provider_tenant_id=conn.provider_tenant_id,
        status=conn.status,
        created_at=conn.created_at,
        updated_at=conn.updated_at,
        last_verified_at=conn.last_verified_at,
        profile_data=profile,
    )


def _owned_connection(connection_id: int, db: Session, user: User) -> Connection:
    conn = (
        db.query(Connection)
        .filter(
            Connection.id == connection_id,
            Connection.organization_id == user.organization_id,
        )
        .first()
    )
    if not conn:
        raise HTTPException(status_code=404, detail="Integration connection not found.")
    return conn


# ---------------------------------------------------------------------------
# ALL ACTIVE CONNECTIONS SUMMARY
# ---------------------------------------------------------------------------
@router.get("/all-active", response_model=List[ProviderConnectionResponse])
def list_all_active_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns all active connections for the current organization across all providers."""
    rows = (
        db.query(Connection)
        .filter(
            Connection.organization_id == current_user.organization_id,
            Connection.status == "ACTIVE",
        )
        .order_by(Connection.created_at.desc())
        .all()
    )
    return [_to_response(r) for r in rows]


# ---------------------------------------------------------------------------
# CONNECT PROVIDER
# ---------------------------------------------------------------------------
@router.post(
    "/{provider_id}/connections",
    response_model=ProviderConnectResponse,
    status_code=status.HTTP_201_CREATED,
)
def connect_provider(
    provider_id: str,
    data: ProviderConnectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prov_key = _standardize_provider_name(provider_id)
    raw_payload = data.dict()

    try:
        profile = verify_provider_credentials(provider_id, raw_payload)
        encrypted = encrypt_credentials(raw_payload)
    except ProviderVerificationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except CredentialStorageError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    account_id = profile.get("account_id") or profile.get("domain") or profile.get("team_name")
    scopes_json = json.dumps(profile)
    verified_at = datetime.utcnow()

    # Find existing connection for this organization and provider
    connection = (
        db.query(Connection)
        .filter(
            Connection.organization_id == current_user.organization_id,
            Connection.provider == prov_key,
        )
        .first()
    )

    if connection is None:
        connection = Connection(
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            provider=prov_key,
            provider_tenant_id=account_id,
            credentials_encrypted=encrypted,
            scopes=scopes_json,
            status="ACTIVE",
            last_verified_at=verified_at,
        )
        db.add(connection)
    else:
        connection.provider_tenant_id = account_id
        connection.credentials_encrypted = encrypted
        connection.scopes = scopes_json
        connection.status = "ACTIVE"
        connection.last_verified_at = verified_at
        connection.updated_at = verified_at

    db.commit()
    db.refresh(connection)

    return ProviderConnectResponse(
        connection=_to_response(connection),
        profile_data=profile,
        message=f"{provider_id.replace('-', ' ').title()} connected and verified successfully.",
    )


# ---------------------------------------------------------------------------
# LIST PROVIDER CONNECTIONS
# ---------------------------------------------------------------------------
@router.get("/{provider_id}/connections", response_model=List[ProviderConnectionResponse])
def list_provider_connections(
    provider_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prov_key = _standardize_provider_name(provider_id)
    rows = (
        db.query(Connection)
        .filter(
            Connection.organization_id == current_user.organization_id,
            Connection.provider == prov_key,
        )
        .order_by(Connection.created_at.desc())
        .all()
    )
    return [_to_response(r) for r in rows]


# ---------------------------------------------------------------------------
# GET PROVIDER DETAILS
# ---------------------------------------------------------------------------
@router.get(
    "/{provider_id}/connections/{connection_id}/details",
    response_model=ProviderDetailsResponse,
)
def get_provider_details(
    provider_id: str,
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conn = _owned_connection(connection_id, db, current_user)
    profile = _parse_scopes_profile(conn.scopes)

    # If scopes profile is empty, try re-verifying from decrypted credentials
    if not profile and conn.credentials_encrypted:
        try:
            creds = decrypt_credentials(conn.credentials_encrypted)
            profile = verify_provider_credentials(provider_id, creds)
            conn.scopes = json.dumps(profile)
            db.commit()
        except Exception:
            profile = {"account_id": conn.provider_tenant_id or provider_id}

    return ProviderDetailsResponse(
        connection_id=conn.id,
        provider=conn.provider,
        provider_tenant_id=conn.provider_tenant_id,
        status=conn.status,
        created_at=conn.created_at,
        last_verified_at=conn.last_verified_at,
        profile_data=profile,
    )


# ---------------------------------------------------------------------------
# TEST PROVIDER CONNECTION
# ---------------------------------------------------------------------------
@router.post(
    "/{provider_id}/connections/{connection_id}/test",
    response_model=ProviderTestResponse,
)
def test_provider_connection(
    provider_id: str,
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conn = _owned_connection(connection_id, db, current_user)
    try:
        creds = decrypt_credentials(conn.credentials_encrypted or "")
        profile = verify_provider_credentials(provider_id, creds)
    except (ProviderVerificationError, CredentialStorageError, Exception) as exc:
        conn.status = "ERROR"
        db.commit()
        return ProviderTestResponse(
            connection_id=conn.id,
            provider=conn.provider,
            status="ERROR",
            last_verified_at=datetime.utcnow(),
            message=f"Verification failed: {str(exc)}",
        )

    verified_at = datetime.utcnow()
    conn.status = "ACTIVE"
    conn.last_verified_at = verified_at
    conn.scopes = json.dumps(profile)
    db.commit()

    return ProviderTestResponse(
        connection_id=conn.id,
        provider=conn.provider,
        status="ACTIVE",
        last_verified_at=verified_at,
        message="Connection active and credentials verified successfully.",
        profile_data=profile,
    )


# ---------------------------------------------------------------------------
# DISCONNECT PROVIDER
# ---------------------------------------------------------------------------
@router.delete(
    "/{provider_id}/connections/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def disconnect_provider(
    provider_id: str,
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conn = _owned_connection(connection_id, db, current_user)
    db.delete(conn)
    db.commit()
    return None
