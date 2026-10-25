"""Per-client product catalog: list, validate and import."""

from __future__ import annotations

import csv
import io
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Client, Product, User
from ..schemas_catalog import ProductImportOut, ProductOut
from ..services import catalog

router = APIRouter(prefix="/clients/{client_id}/products", tags=["Catalog"])
MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 5000


def _client(db: Session, user: User, client_id: uuid.UUID) -> Client:
    client = db.scalar(select(Client).where(Client.id == client_id, Client.agency_id == user.agency_id))
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


def _rows(raw: bytes) -> list[dict]:
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds the 5 MB limit")
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail="File has no data rows")
    if len(rows) > MAX_ROWS:
        raise HTTPException(status_code=400, detail=f"File exceeds {MAX_ROWS} rows")
    mapping = catalog.map_headers(list(reader.fieldnames or []))
    if "title" not in mapping and "sku" not in mapping:
        raise HTTPException(status_code=400, detail="File needs a title or sku column")
    return [{field: row.get(column, "") for field, column in mapping.items()} for row in rows]


@router.get("", response_model=list[ProductOut])
def list_products(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    return db.scalars(
        select(Product).where(Product.client_id == client.id).order_by(Product.created_at.desc()).limit(500)
    ).all()


@router.post("/validate", response_model=ProductImportOut)
async def validate_file(
    client_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    rows = _rows(await file.read())
    return catalog.import_rows(db, agency_id=client.agency_id, client_id=client.id, rows=rows, dry_run=True)


@router.post("/import", response_model=ProductImportOut)
async def import_file(
    client_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    rows = _rows(await file.read())
    return catalog.import_rows(db, agency_id=client.agency_id, client_id=client.id, rows=rows)
