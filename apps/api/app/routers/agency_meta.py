"""Agency-level Meta app credentials: one app for the whole agency."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Agency, User, now_utc
from ..security import decrypt_secret, encrypt_secret

router = APIRouter(prefix="/agency/meta-app", tags=["Agency"])


class MetaAppIn(BaseModel):
    app_id: str = ""
    app_secret: str | None = None


@router.get("")
def get_meta_app(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    agency = db.get(Agency, user.agency_id)
    if not agency:
        raise HTTPException(status_code=404, detail="Agency not found")
    return {"app_id": agency.meta_app_id or "", "has_secret": bool(agency.encrypted_meta_app_secret)}


@router.put("")
def put_meta_app(payload: MetaAppIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    agency = db.get(Agency, user.agency_id)
    if not agency:
        raise HTTPException(status_code=404, detail="Agency not found")
    app_id = (payload.app_id or "").strip()
    if payload.app_secret is not None:
        secret = payload.app_secret.strip()
        if secret:
            agency.encrypted_meta_app_secret = encrypt_secret(secret)
    agency.meta_app_id = app_id[:64]
    agency.updated_at = now_utc()
    db.commit()

    verified = None
    if app_id and agency.encrypted_meta_app_secret:
        token = f"{app_id}|{decrypt_secret(agency.encrypted_meta_app_secret)}"
        base = get_settings().meta_graph_base_url.rstrip("/")
        try:
            with httpx.Client(timeout=8) as client:
                response = client.get(f"{base}/{app_id}", params={"fields": "id,name"}, headers={"Authorization": f"Bearer {token}"})
            verified = response.status_code == 200
        except Exception:  # noqa: BLE001
            verified = False
    return {"app_id": agency.meta_app_id, "has_secret": bool(agency.encrypted_meta_app_secret), "verified": verified}
