"""Pydantic schemas for Instagram publishing + editorial content."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .schemas_legal import ChannelConnectConsentIn, HumanPublishApprovalIn


class InstagramChannelOut(BaseModel):
    id: UUID
    client_id: UUID
    status: str
    instagram_user_id: str
    page_id: str | None = None
    username: str | None = None
    display_name: str | None = None
    access_token_configured: bool = False
    token_expires_at: datetime | None = None
    granted_scopes: list[str] = Field(default_factory=list)
    connection_mode: str = "manual"
    last_error: str | None = None
    is_enabled: bool = True
    last_connected_at: datetime | None = None
    publish_permission: bool = False

    model_config = {"from_attributes": True}


class InstagramChannelManualUpdate(BaseModel):
    instagram_user_id: str
    page_id: str | None = None
    username: str | None = None
    display_name: str | None = None
    access_token: str | None = None
    granted_scopes: list[str] | None = None


class InstagramOAuthOptionsOut(BaseModel):
    oauth_available: bool
    mock_mode: bool
    meta_app_id: str | None = None
    graph_version: str
    scopes: list[str]
    redirect_path: str
    blocked_reason: str | None = None


class InstagramOAuthSessionIn(BaseModel):
    consent: ChannelConnectConsentIn


class InstagramOAuthSessionOut(BaseModel):
    state: str
    dialog_url: str | None = None
    mock_mode: bool = False


class InstagramOAuthCompleteIn(BaseModel):
    code: str | None = None
    state: str
    use_mock: bool = False
    # When multiple IG accounts are linked, client picks one after discovery.
    instagram_user_id: str | None = None


class InstagramAccountChoiceOut(BaseModel):
    page_id: str | None = None
    page_name: str | None = None
    instagram_user_id: str
    username: str | None = None
    display_name: str | None = None


class InstagramHealthOut(BaseModel):
    ui_status: str
    account_ok: bool
    token_ok: bool
    publish_permission_ok: bool
    api_ok: bool
    mock_mode: bool
    details: dict = Field(default_factory=dict)


class InstagramPublishingLimitOut(BaseModel):
    quota_usage: int | None = None
    quota_total: int | None = None
    quota_duration: int | None = None
    available: bool = False


class MediaAssetOut(BaseModel):
    id: UUID
    client_id: UUID
    file_name: str
    mime_type: str
    file_size: int
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    created_at: datetime
    preview_url: str | None = None

    model_config = {"from_attributes": True}


class ContentMediaOut(BaseModel):
    media_id: UUID
    position: int
    file_name: str | None = None
    mime_type: str | None = None
    preview_url: str | None = None


class ContentItemCreate(BaseModel):
    content_type: str = "IMAGE"
    title: str = ""
    caption: str = ""
    hashtags: str = ""
    cta: str = ""
    timezone: str = "UTC"
    media_ids: list[UUID] = Field(default_factory=list)


class ContentItemUpdate(BaseModel):
    title: str | None = None
    caption: str | None = None
    hashtags: str | None = None
    cta: str | None = None
    timezone: str | None = None
    media_ids: list[UUID] | None = None
    status: str | None = None
    ai_meta: dict | None = None


class ContentItemOut(BaseModel):
    id: UUID
    client_id: UUID
    title: str
    caption: str
    hashtags: str
    cta: str
    content_type: str
    status: str
    timezone: str
    ai_meta: dict = Field(default_factory=dict)
    media: list[ContentMediaOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PublicationOut(BaseModel):
    id: UUID
    client_id: UUID
    content_id: UUID
    channel: str
    provider_account_id: str
    status: str
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    timezone: str
    provider_publication_id: str | None = None
    provider_container_id: str | None = None
    provider_permalink: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    error_class: str | None = None
    attempt_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PublishApprovalBody(HumanPublishApprovalIn):
    pass


class ScheduleRequest(HumanPublishApprovalIn):
    scheduled_at: datetime
    timezone: str = "UTC"


class GenerateContentRequest(BaseModel):
    content_type: str = "IMAGE"
    objective: str
    audience: str = ""
    user_instruction: str = ""
    slide_count: int = 7
    language: str = "es"
    content_goal: str = Field(default="loyalty", pattern=r"^(loyalty|reach|convert)$")
    cta_instruction: str = Field(default="", max_length=180)
    hook_structure: bool = True


class GenerateContentOut(BaseModel):
    title: str = ""
    caption: str = ""
    cta: str = ""
    hashtags: list[str] = Field(default_factory=list)
    visualSuggestion: str | None = None
    imagePrompt: str | None = None
    slides: list[dict] | None = None


class DashboardStatsOut(BaseModel):
    drafts: int = 0
    scheduled: int = 0
    published_month: int = 0
    failed: int = 0
