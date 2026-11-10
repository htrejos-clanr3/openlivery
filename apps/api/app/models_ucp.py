"""UCP add-on models.

One integration per client. The client stays the Merchant of Record; Fast
Livery only publishes product data and receives carts from Google surfaces.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base
from .models import new_uuid, now_utc


CONNECTION_STATUSES = ("draft", "pending_review", "active", "suspended")
PUBLISH_STATUSES = ("draft", "eligible", "ineligible", "sent", "approved", "rejected")


class UcpConnection(Base):
    """UCP integration settings for one client."""

    __tablename__ = "ucp_connections"
    __table_args__ = (UniqueConstraint("client_id", name="uq_ucp_connections_client"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")
    merchant_center_id: Mapped[str] = mapped_column(String(64), default="", server_default="")
    profile_slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    api_key_hash: Mapped[str] = mapped_column(String(64), default="", server_default="")
    capabilities: Mapped[list] = mapped_column(JSON, default=list)
    # "portal" (Fast Livery cart) or "store" (the client's own cart API).
    adapter_kind: Mapped[str] = mapped_column(String(20), default="portal", server_default="portal")
    store_base_url: Mapped[str] = mapped_column(String(600), default="", server_default="")
    encrypted_store_credentials: Mapped[str | None] = mapped_column(Text, nullable=True)
    addendum_version: Mapped[str] = mapped_column(String(40), default="", server_default="")
    addendum_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc
    )


class UcpProduct(Base):
    """Per-product UCP eligibility and publication state."""

    __tablename__ = "ucp_products"
    __table_args__ = (UniqueConstraint("product_id", name="uq_ucp_products_product"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ucp_connections.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    merchant_item_id: Mapped[str] = mapped_column(String(120), default="", server_default="")
    checkout_eligibility: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    notice_type: Mapped[str] = mapped_column(String(40), default="", server_default="")
    notice_message: Mapped[str] = mapped_column(Text, default="", server_default="")
    publish_status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")
    last_error: Mapped[str] = mapped_column(Text, default="", server_default="")
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UcpCartSession(Base):
    """A cart received from Google and handed off to the merchant checkout."""

    __tablename__ = "ucp_cart_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ucp_connections.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="open", server_default="open")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    continue_url: Mapped[str] = mapped_column(Text, default="", server_default="")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class UcpEvent(Base):
    """Audit trail for every public UCP call. Sensitive payloads are redacted."""

    __tablename__ = "ucp_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ucp_connections.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(40))
    request: Mapped[dict] = mapped_column(JSON, default=dict)
    response: Mapped[dict] = mapped_column(JSON, default=dict)
    status_code: Mapped[int] = mapped_column(default=200)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
