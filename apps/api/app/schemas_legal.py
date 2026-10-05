from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class LegalDocumentsOut(BaseModel):
    tos_version: str
    privacy_version: str
    tos_url: str
    privacy_url: str


class LegalPlatformStatusOut(BaseModel):
    documents: LegalDocumentsOut
    terms_accepted: bool
    privacy_accepted: bool
    platform_ready: bool


class LegalPlatformAcceptIn(BaseModel):
    accept_terms: bool = False
    accept_privacy: bool = False


class ChannelConnectConsentIn(BaseModel):
    channel: str = Field(pattern=r"^(instagram|whatsapp_cloud)$")
    client_id: uuid.UUID
    admin_confirmed: bool = False
    no_password_stored: bool = True
    ai_disclosure_acknowledged: bool = False


class HumanPublishApprovalIn(BaseModel):
    human_approved: bool = False
    reviewed_exact_content: bool = False
