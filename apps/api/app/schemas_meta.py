"""Schemas for Meta Developer Tools MCP diagnostics (no secrets)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MetaMcpStatusOut(BaseModel):
    enabled: bool
    mock_mode: bool
    manage_enabled: bool
    url_configured: bool
    token_configured: bool
    meta_app_id: str | None = None
    message: str | None = None


class MetaHealthOut(BaseModel):
    overall_status: str
    enabled: bool = True
    mock_mode: bool = False
    app_id: str | None = None
    fetched_at: str | None = None
    time_range: str | None = None
    message: str | None = None
    app: dict = Field(default_factory=dict)
    api_usage: dict = Field(default_factory=dict)
    rate_limits: dict = Field(default_factory=dict)
    webhooks: dict = Field(default_factory=dict)
    app_review: dict = Field(default_factory=dict)
    compliance: dict = Field(default_factory=dict)
    deprecations: dict = Field(default_factory=dict)
    alerts: list[dict] = Field(default_factory=list)
    manage_enabled: bool = False


class MetaDiagnosticsOut(BaseModel):
    status: str
    checks: list[dict]
    summary: dict
    health: dict | None = None


class MetaWebhookInspectOut(BaseModel):
    app_id: str | None = None
    fetched_at: str | None = None
    manage_enabled: bool = False
    expected: list[str] = Field(default_factory=list)
    present: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    extra: list[str] = Field(default_factory=list)
    subscriptions: list = Field(default_factory=list)
    callback_url: str | None = None
    raw_summary: dict = Field(default_factory=dict)


class MetaWebhookRepairPreviewOut(BaseModel):
    manage_enabled: bool
    changes: list[dict]
    missing: list[str]
    extra_untouched: list[str]
    note: str


class MetaWebhookRepairIn(BaseModel):
    confirm: bool = False


class MetaWebhookTestIn(BaseModel):
    field: str = "messages"


class MetaWebhookTestOut(BaseModel):
    test_id: str
    status: str
    meta_request_accepted: bool
    openlivery_received: bool
    latency_ms: int | None = None
    event_type: str
    error: str | None = None
    steps: dict = Field(default_factory=dict)


class MetaWebhookTestHistoryOut(BaseModel):
    id: UUID
    test_id: str
    event_type: str
    status: str
    requested_at: datetime
    received_at: datetime | None = None
    latency_ms: int | None = None
    error: str | None = None

    model_config = {"from_attributes": True}
