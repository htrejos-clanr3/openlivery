"""UCP add-on: per-client setup, publishing and status (authenticated)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Client, LegalAcceptance, Product, User, now_utc
from ..models_ucp import UcpConnection, UcpProduct
from ..schemas_ucp import (
    UcpAddendumIn,
    UcpConnectOut,
    UcpConnectionIn,
    UcpConnectionOut,
    UcpConnectionUpdate,
    UcpProductOut,
    UcpSyncOut,
)
from ..security import encrypt_secret
from ..services import ucp as ucp_service

router = APIRouter(prefix="/clients/{client_id}/ucp", tags=["UCP"])

ADDENDUM_TYPE = "ucp_program_addendum"
ADDENDUM_KEY = "ucp_program_addendum"


def _client(db: Session, user: User, client_id: uuid.UUID) -> Client:
    client = db.scalar(
        select(Client).where(Client.id == client_id, Client.agency_id == user.agency_id)
    )
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


def _connection(db: Session, client: Client) -> UcpConnection:
    connection = db.scalar(select(UcpConnection).where(UcpConnection.client_id == client.id))
    if not connection:
        raise HTTPException(status_code=404, detail="UCP is not enabled for this client")
    return connection


def _out(db: Session, connection: UcpConnection) -> UcpConnectionOut:
    rows = db.scalars(
        select(UcpProduct).where(UcpProduct.connection_id == connection.id)
    ).all()
    return UcpConnectionOut(
        id=connection.id,
        status=connection.status,
        merchant_center_id=connection.merchant_center_id,
        profile_slug=connection.profile_slug,
        capabilities=connection.capabilities or [],
        adapter_kind=connection.adapter_kind,
        store_base_url=connection.store_base_url,
        addendum_version=connection.addendum_version,
        addendum_accepted_at=connection.addendum_accepted_at,
        last_sync_at=connection.last_sync_at,
        last_error=connection.last_error,
        products=len(rows),
        eligible=sum(1 for row in rows if row.checkout_eligibility),
    )


@router.get("", response_model=UcpConnectionOut)
def get_connection(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    return _out(db, _connection(db, client))


@router.post("", response_model=UcpConnectOut, status_code=201)
def create_connection(
    client_id: uuid.UUID,
    payload: UcpConnectionIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    existing = db.scalar(select(UcpConnection).where(UcpConnection.client_id == client.id))
    if existing:
        raise HTTPException(status_code=409, detail="UCP is already enabled for this client")

    raw_key, key_hash = ucp_service.new_api_key()
    connection = UcpConnection(
        agency_id=user.agency_id,
        client_id=client.id,
        status="draft",
        merchant_center_id=payload.merchant_center_id.strip(),
        profile_slug=f"ucp-{uuid.uuid4().hex[:10]}",
        api_key_hash=key_hash,
        capabilities=[ucp_service.CART_CAPABILITY],
        adapter_kind=payload.adapter_kind,
        store_base_url=payload.store_base_url.strip(),
        encrypted_store_credentials=encrypt_secret(payload.store_api_token)
        if payload.store_api_token
        else None,
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)
    return UcpConnectOut(connection=_out(db, connection), api_key=raw_key)


@router.patch("", response_model=UcpConnectionOut)
def update_connection(
    client_id: uuid.UUID,
    payload: UcpConnectionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    connection = _connection(db, client)
    if payload.merchant_center_id is not None:
        connection.merchant_center_id = payload.merchant_center_id.strip()
    if payload.adapter_kind is not None:
        connection.adapter_kind = payload.adapter_kind
    if payload.store_base_url is not None:
        connection.store_base_url = payload.store_base_url.strip()
    if payload.store_api_token:
        connection.encrypted_store_credentials = encrypt_secret(payload.store_api_token)
    db.commit()
    return _out(db, connection)


@router.post("/addendum", response_model=UcpConnectionOut)
def accept_addendum(
    client_id: uuid.UUID,
    payload: UcpAddendumIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    connection = _connection(db, client)
    now = now_utc()
    connection.addendum_version = payload.version
    connection.addendum_accepted_at = now
    if connection.status == "draft":
        connection.status = "pending_review"
    db.add(
        LegalAcceptance(
            agency_id=user.agency_id,
            user_id=user.id,
            client_id=client.id,
            acceptance_type=ADDENDUM_TYPE,
            document_key=ADDENDUM_KEY,
            document_version=payload.version,
            channel="ucp",
            metadata_json={"source": "ucp_addendum"},
            created_at=now,
        )
    )
    db.commit()
    return _out(db, connection)


@router.post("/sync", response_model=UcpSyncOut)
def sync(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    connection = _connection(db, client)
    result = ucp_service.sync_connection(db, connection, client)
    db.commit()
    return UcpSyncOut(**result)


@router.get("/products", response_model=list[UcpProductOut])
def list_products(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    connection = _connection(db, client)
    rows = db.execute(
        select(UcpProduct, Product)
        .join(Product, Product.id == UcpProduct.product_id)
        .where(UcpProduct.connection_id == connection.id)
        .order_by(Product.sku)
    ).all()
    return [
        UcpProductOut(
            product_id=product.id,
            sku=product.sku,
            title=product.title,
            checkout_eligibility=row.checkout_eligibility,
            publish_status=row.publish_status,
            last_error=row.last_error,
            merchant_item_id=row.merchant_item_id,
            notice_type=row.notice_type,
        )
        for row, product in rows
    ]
