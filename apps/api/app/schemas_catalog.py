"""Schemas for the product catalog."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ProductMessageOut(BaseModel):
    level: str
    field: str
    message: str


class ProductOut(BaseModel):
    id: UUID
    sku: str
    title: str
    description: str = ""
    price: Decimal | None = None
    currency: str = ""
    availability: str
    image_url: str = ""
    url: str = ""
    gtin: str | None = None
    brand: str = ""
    category: str = ""
    source: str
    status: str
    messages: list[ProductMessageOut] = Field(default_factory=list)
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductRowOut(BaseModel):
    row: int
    sku: str
    status: str
    messages: list[ProductMessageOut] = Field(default_factory=list)


class ProductImportOut(BaseModel):
    created: int = 0
    updated: int = 0
    valid: int = 0
    warning: int = 0
    error: int = 0
    rows: list[ProductRowOut] = Field(default_factory=list)
