"""Schemas for the UCP add-on."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class UcpConnectionOut(BaseModel):
    id: UUID
    status: str
    merchant_center_id: str
    profile_slug: str
    capabilities: list[str] = Field(default_factory=list)
    adapter_kind: str
    store_base_url: str
    addendum_version: str
    addendum_accepted_at: datetime | None = None
    last_sync_at: datetime | None = None
    last_error: str = ""
    products: int = 0
    eligible: int = 0

    model_config = {"from_attributes": True}


class UcpConnectionIn(BaseModel):
    merchant_center_id: str = ""
    adapter_kind: Literal["portal", "store"] = "portal"
    store_base_url: str = ""
    store_api_token: str = ""


class UcpConnectionUpdate(BaseModel):
    merchant_center_id: str | None = None
    adapter_kind: Literal["portal", "store"] | None = None
    store_base_url: str | None = None
    store_api_token: str | None = None


class UcpConnectOut(BaseModel):
    connection: UcpConnectionOut
    # Returned once, on creation. Only its hash is stored.
    api_key: str


class UcpProductOut(BaseModel):
    product_id: UUID
    sku: str
    title: str
    checkout_eligibility: bool
    publish_status: str
    last_error: str = ""
    merchant_item_id: str = ""
    notice_type: str = ""

    model_config = {"from_attributes": True}


class UcpSyncOut(BaseModel):
    synced: int
    eligible: int
    ineligible: int


class UcpAddendumIn(BaseModel):
    version: str = "1.0"


class UcpCartItemIn(BaseModel):
    id: str


class UcpCartLineIn(BaseModel):
    item: UcpCartItemIn
    quantity: int = 1


class UcpCartIn(BaseModel):
    line_items: list[UcpCartLineIn] = Field(default_factory=list)
