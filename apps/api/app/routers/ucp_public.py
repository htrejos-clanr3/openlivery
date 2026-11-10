"""Public UCP routes: business profile and Cart API, resolved by Host."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Client
from ..models_ucp import UcpConnection
from ..schemas_ucp import UcpCartIn
from ..services import ucp as ucp_service

public_router = APIRouter(tags=["UCP Public"])

UCP_PREFIX = "/ucp/v1"


def _host(request: Request) -> str:
    return (request.headers.get("host") or "").split(":")[0].strip().lower()


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _resolve(request: Request, db: Session) -> tuple[Client, UcpConnection] | None:
    host = _host(request)
    if not host:
        return None
    client = db.scalar(
        select(Client).where(
            Client.portal_domain == host,
            Client.portal_domain_verified.is_(True),
        )
    )
    if not client:
        return None
    connection = db.scalar(
        select(UcpConnection).where(UcpConnection.client_id == client.id)
    )
    if not connection or connection.status == "suspended":
        return None
    return client, connection


def _api_key(request: Request) -> str:
    key = (request.headers.get("x-api-key") or "").strip()
    if key:
        return key
    auth = (request.headers.get("authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return ""


@public_router.get("/.well-known/ucp")
def ucp_profile(request: Request, db: Session = Depends(get_db)):
    resolved = _resolve(request, db)
    if not resolved:
        return JSONResponse(status_code=404, content={"detail": "Unknown UCP merchant"})
    _, connection = resolved
    return JSONResponse(
        content=ucp_service.build_profile(connection, _base_url(request)),
        media_type="application/json",
    )


@public_router.post(f"{UCP_PREFIX}/carts")
def create_cart(payload: UcpCartIn, request: Request, db: Session = Depends(get_db)):
    resolved = _resolve(request, db)
    if not resolved:
        return JSONResponse(
            status_code=404, content=ucp_service.cart_error("unknown_merchant", "Merchant not found")
        )
    client, connection = resolved

    if not ucp_service.api_key_matches(_api_key(request), connection.api_key_hash):
        return JSONResponse(
            status_code=401, content=ucp_service.cart_error("unauthorized", "Invalid API key")
        )

    lines = [{"id": line.item.id, "quantity": line.quantity} for line in payload.line_items]
    result, error = ucp_service.create_cart(
        db, connection, client, lines, _base_url(request)
    )
    if error:
        db.rollback()
        return JSONResponse(
            status_code=400,
            content=ucp_service.cart_error(error, f"Cart could not be created: {error}"),
        )
    db.commit()
    return JSONResponse(content=result, status_code=200)
