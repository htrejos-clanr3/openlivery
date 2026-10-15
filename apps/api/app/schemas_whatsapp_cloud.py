import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from .schemas_legal import ChannelConnectConsentIn


class WhatsAppCloudChannelUpdate(BaseModel):
    agent_id: uuid.UUID
    phone_number_id: str | None = Field(default=None, max_length=80)
    waba_id: str | None = Field(default=None, max_length=80)
    # Secrets are write-only: omitted or blank values keep the stored ones.
    access_token: str | None = Field(default=None, max_length=4000)
    app_secret: str | None = Field(default=None, max_length=255)
    connection_mode: str | None = Field(default=None, pattern=r"^(manual|managed|embedded)$")


class WhatsAppCloudAgentUpdate(BaseModel):
    agent_id: uuid.UUID


class WhatsAppWebhookRegistrationOut(BaseModel):
    ok: bool
    code: str
    message: str
    host: str | None = None
    app_without_webhook: bool = False


class WhatsAppCloudChannelOut(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    agent_id: uuid.UUID
    status: str
    connection_mode: str = "manual"
    phone_number: str | None
    display_name: str | None
    phone_number_id: str
    waba_id: str | None
    has_access_token: bool
    has_app_secret: bool
    webhook_url: str
    webhook_verify_token: str
    last_error: str | None
    error_message: str | None = None
    error_code: str | None = None
    is_enabled: bool
    last_connected_at: datetime | None
    created_at: datetime
    updated_at: datetime
    webhook_registration: WhatsAppWebhookRegistrationOut | None = None


class WhatsAppTemplateOut(BaseModel):
    id: str | None = None
    name: str
    language: str | None = None
    status: str | None = None
    category: str | None = None
    components: list[dict] = Field(default_factory=list)


class WhatsAppTemplateListOut(BaseModel):
    templates: list[WhatsAppTemplateOut]
    count: int


class WhatsAppTemplateSendIn(BaseModel):
    to: str = Field(min_length=5, max_length=32)
    name: str = Field(min_length=1, max_length=512)
    language: str = Field(default="en_US", min_length=2, max_length=16)
    body_parameters: list[str] = Field(default_factory=list, max_length=20)


class WhatsAppTemplateSendOut(BaseModel):
    wamid: str | None = None
    to: str
    name: str
    language: str


class WhatsAppCloudHealthOut(BaseModel):
    connected: bool
    ui_status: str
    connection_mode: str
    status: str
    phone_number: str | None = None
    display_name: str | None = None
    phone_number_id: str | None = None
    waba_id: str | None = None
    waba_configured: bool
    token_configured: bool
    app_secret_configured: bool
    permissions_valid: bool
    webhook_configured: bool
    agent_assigned: bool
    is_enabled: bool
    graph_reachable: bool
    last_inbound_message_at: str | None = None
    last_outbound_message_at: str | None = None
    last_connected_at: str | None = None
    last_error: str | None = None
    error: dict | None = None
    meta_platform: dict | None = None


class WhatsAppSignupOptionsOut(BaseModel):
    managed_available: bool
    mock_mode: bool
    meta_app_id: str | None = None
    meta_config_id: str | None = None
    graph_version: str
    blocked_reason: str | None = None


class WhatsAppSignupSessionIn(BaseModel):
    consent: ChannelConnectConsentIn


class WhatsAppSignupSessionOut(BaseModel):
    state: str
    meta_app_id: str | None = None
    meta_config_id: str | None = None
    mock_mode: bool
    redirect_url: str | None = None
    blocked_reason: str | None = None


class WhatsAppSignupCompleteRequest(BaseModel):
    state: str = Field(min_length=10)
    code: str | None = Field(default=None, max_length=4000)
    # Embedded Signup may also pass phone_number_id / waba_id from the JS event.
    phone_number_id: str | None = Field(default=None, max_length=80)
    waba_id: str | None = Field(default=None, max_length=80)
    agent_id: uuid.UUID | None = None
    use_mock: bool = False


class WhatsAppSignupCompleteOut(BaseModel):
    channel: WhatsAppCloudChannelOut
    steps: list[dict]
