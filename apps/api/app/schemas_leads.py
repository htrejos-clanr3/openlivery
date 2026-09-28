"""Schemas for per-client automatic lead capture and commercial leads."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class LeadStageOut(BaseModel):
    id: UUID
    name: str
    slug: str
    position: int

    model_config = {"from_attributes": True}


class LeadPipelineOut(BaseModel):
    id: UUID
    name: str
    is_default: bool
    stages: list[LeadStageOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class AssigneeOut(BaseModel):
    id: UUID
    name: str
    email: str

    model_config = {"from_attributes": True}


class LeadCaptureSettingsOut(BaseModel):
    id: UUID
    client_id: UUID
    enabled: bool
    sources: list[str] = Field(default_factory=list)
    default_pipeline_id: UUID | None = None
    default_stage_id: UUID | None = None
    default_assignee_user_id: UUID | None = None
    auto_tags: list[str] = Field(default_factory=list)
    notify_on_new_lead: bool
    ingest_token: str
    last_ingest_at: datetime | None = None
    last_ingest_status: str | None = None
    leads_created_count: int = 0
    automation_config: dict[str, Any] = Field(default_factory=dict)
    pipeline: LeadPipelineOut | None = None
    assignees: list[AssigneeOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class LeadCaptureSettingsUpdate(BaseModel):
    enabled: bool | None = None
    sources: list[str] | None = None
    default_pipeline_id: UUID | None = None
    default_stage_id: UUID | None = None
    default_assignee_user_id: UUID | None = None
    auto_tags: list[str] | None = None
    notify_on_new_lead: bool | None = None
    automation_config: dict[str, Any] | None = None


class ContactOut(BaseModel):
    id: UUID
    client_id: UUID
    name: str
    company: str = ""
    email: str | None = None
    phone: str | None = None
    channel_identifier: str | None = None
    source: str

    model_config = {"from_attributes": True}


class LeadActivityOut(BaseModel):
    id: UUID
    kind: str
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LeadOut(BaseModel):
    id: UUID
    client_id: UUID
    source: str
    tags: list[str] = Field(default_factory=list)
    contact: ContactOut
    conversation_id: UUID | None = None
    pipeline_id: UUID | None = None
    stage_id: UUID | None = None
    stage_name: str | None = None
    stage_slug: str | None = None
    assigned_user_id: UUID | None = None
    assignee_name: str | None = None
    notes: str = ""
    next_action: str = ""
    score: int | None = None
    last_activity_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    activities: list[LeadActivityOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class LeadCreateIn(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    source: str = "form"
    channel_identifier: str | None = None
    stage_id: UUID | None = None
    assigned_user_id: UUID | None = None
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    next_action: str | None = None


class LeadUpdateIn(BaseModel):
    stage_id: UUID | None = None
    assigned_user_id: UUID | None = None
    tags: list[str] | None = None
    notes: str | None = None
    next_action: str | None = None
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None


class LeadActivityIn(BaseModel):
    message: str
    kind: str = "note"


class LeadStatsOut(BaseModel):
    new_count: int
    qualified_count: int
    unassigned_count: int
    stale_count: int
    total_count: int


class LeadCaptureEventOut(BaseModel):
    id: UUID
    client_id: UUID
    source: str
    status: str
    error_message: str | None = None
    lead_id: UUID | None = None
    contact_id: UUID | None = None
    conversation_id: UUID | None = None
    attempt_count: int
    payload: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadNotificationOut(BaseModel):
    id: UUID
    client_id: UUID
    lead_id: UUID
    kind: str
    read_at: datetime | None = None
    created_at: datetime
    contact_name: str = ""
    source: str = ""

    model_config = {"from_attributes": True}


class PublicLeadIn(BaseModel):
    source: str = "form"
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    channel_identifier: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
