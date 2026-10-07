"""LinkedIn copy desk and official personal-profile publishing."""

from datetime import datetime
import uuid

from pydantic import BaseModel, Field

from .schemas import ORMModel
from .schemas_legal import ChannelConnectConsentIn


class LinkedInChannelUpdate(BaseModel):
    profile_url: str | None = Field(default=None, max_length=400)
    display_name: str | None = Field(default=None, max_length=180)
    voice_notes: str | None = Field(default=None, max_length=12000)
    is_enabled: bool | None = None


class LinkedInChannelOut(ORMModel):
    id: uuid.UUID
    client_id: uuid.UUID
    profile_url: str = ""
    display_name: str = ""
    voice_notes: str = ""
    status: str = "disconnected"
    member_id: str = ""
    access_token_configured: bool = False
    granted_scopes: list[str] = Field(default_factory=list)
    token_expires_at: datetime | None = None
    last_error: str | None = None
    last_connected_at: datetime | None = None
    is_enabled: bool = True
    publishes: bool = False
    connection_mode: str = "copy_paste"
    updated_at: datetime


class LinkedInGeneratePostRequest(BaseModel):
    idea: str = Field(min_length=8, max_length=4000)
    language: str = Field(default="es", max_length=8)


class LinkedInHumanizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


class LinkedInProfileRequest(BaseModel):
    pasted: str = Field(min_length=20, max_length=20000)
    language: str = Field(default="es", max_length=8)


class LinkedInOAuthOptionsOut(BaseModel):
    oauth_available: bool
    mock_mode: bool
    client_id: str | None = None
    scopes: list[str]
    redirect_path: str
    api_version: str
    blocked_reason: str | None = None


class LinkedInOAuthSessionOut(BaseModel):
    state: str
    dialog_url: str | None = None
    mock_mode: bool = False


class LinkedInOAuthSessionIn(BaseModel):
    consent: ChannelConnectConsentIn


class LinkedInOAuthCompleteIn(BaseModel):
    state: str = Field(min_length=10)
    code: str | None = None
    use_mock: bool = False


class LinkedInPublishRequest(BaseModel):
    approved: bool
    text: str | None = Field(default=None, min_length=1, max_length=3000)


class LinkedInPublicationOut(BaseModel):
    draft_id: uuid.UUID
    status: str
    provider_post_id: str
    published_at: datetime
    text: str


class LinkedInDraftOut(ORMModel):
    id: uuid.UUID
    kind: str
    idea: str
    body: str
    hook_id: int | None = None
    human_score: float | None = None
    verdict: str = ""
    status: str = "draft"
    provider_post_id: str | None = None
    published_at: datetime | None = None
    created_at: datetime
