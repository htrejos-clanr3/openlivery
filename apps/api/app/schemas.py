import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .services.providers import PROVIDER_PATTERN


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    agency_name: str = Field(min_length=2, max_length=180)
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    accept_terms: bool = False
    accept_privacy: bool = False


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AgencyOut(ORMModel):
    id: uuid.UUID
    name: str
    slug: str
    brand_color: str
    logo_url: str | None = None


class AgencyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    slug: str | None = Field(default=None, min_length=2, max_length=180)
    brand_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class UserOut(ORMModel):
    id: uuid.UUID
    name: str
    email: EmailStr
    role: str
    password_configured: bool = True
    agency: AgencyOut


class ClientBase(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    industry: str = Field(default="", max_length=160)
    description: str = ""
    general_context: str = ""
    is_active: bool = True


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    industry: str | None = None
    description: str | None = None
    general_context: str | None = None
    is_active: bool | None = None
    brand_primary_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    brand_secondary_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    brand_font: str | None = Field(default=None, max_length=80)
    brand_voice: str | None = None


class ClientPortalUpdate(BaseModel):
    portal_enabled: bool | None = None
    portal_slug: str | None = Field(default=None, min_length=2, max_length=180)
    portal_title: str | None = Field(default=None, max_length=180)
    portal_email: EmailStr | None = None
    portal_password: str | None = Field(default=None, min_length=8, max_length=128)


class AgentSummary(ORMModel):
    id: uuid.UUID
    name: str
    description: str
    is_active: bool


class ClientOut(ORMModel):
    id: uuid.UUID
    name: str
    industry: str
    description: str
    general_context: str
    is_active: bool
    portal_slug: str
    portal_enabled: bool
    portal_title: str
    portal_email: EmailStr | None
    portal_password_configured: bool
    portal_domain: str | None
    portal_domain_verified: bool
    brand_primary_color: str = "#075985"
    brand_secondary_color: str = "#0f172a"
    brand_font: str = ""
    brand_voice: str = ""
    brand_logo_url: str | None = None
    created_at: datetime
    updated_at: datetime
    agents: list[AgentSummary] = []


class ClientDomainSet(BaseModel):
    # A DNS hostname, e.g. "chat.brand.com". Lowercased and validated as a host.
    # No look-around: pydantic v2's regex engine does not support it.
    domain: str = Field(
        min_length=3,
        max_length=255,
        pattern=r"^([A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?$",
    )


class ClientDomainOut(BaseModel):
    domain: str | None
    verified: bool
    # DNS records the operator/client must create.
    txt_host: str | None
    txt_value: str | None


class ProviderKeyUpdate(BaseModel):
    api_key: str = Field(min_length=1)


class ProviderOut(BaseModel):
    provider: str
    label: str
    configured: bool
    api_key_masked: str = ""


class ImageGenerationStatusOut(BaseModel):
    provider: str
    resolved_provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    size: str = "1024x1536"
    ready: bool = False
    reachable: bool = False
    supports_product_edit: bool = False
    ollama_can_generate_ads: bool = False
    message: str = ""
    install_hint: str = ""


class AgentBase(BaseModel):
    client_id: uuid.UUID
    name: str = Field(min_length=1, max_length=180)
    description: str = ""
    instructions: str = ""
    personality: str = ""
    brief_summary: str = ""
    brief_products: str = ""
    brief_audience: str = ""
    brief_policies: str = ""
    brief_goal: str = ""
    brief_dos: str = ""
    brief_donts: str = ""
    model: str = ""
    provider: str = Field(default="openai", pattern=PROVIDER_PATTERN)
    timezone: str = Field(default="UTC", max_length=64)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=32000)
    memory_limit: int = Field(default=30, ge=0, le=200)
    image_enabled: bool = False
    image_model: str = Field(default="", max_length=180)
    audio_enabled: bool = False
    audio_model: str = Field(default="whisper-1", max_length=180)
    widget_enabled: bool = False
    widget_greeting: str = Field(default="", max_length=2000)
    widget_color: str = Field(default="", max_length=20)
    widget_position: str = Field(default="right", pattern=r"^(right|left)$")
    is_active: bool = True


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    client_id: uuid.UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    instructions: str | None = None
    personality: str | None = None
    brief_summary: str | None = None
    brief_products: str | None = None
    brief_audience: str | None = None
    brief_policies: str | None = None
    brief_goal: str | None = None
    brief_dos: str | None = None
    brief_donts: str | None = None
    model: str | None = None
    provider: str | None = Field(default=None, pattern=PROVIDER_PATTERN)
    timezone: str | None = Field(default=None, max_length=64)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=32000)
    memory_limit: int | None = Field(default=None, ge=0, le=200)
    image_enabled: bool | None = None
    image_model: str | None = Field(default=None, max_length=180)
    audio_enabled: bool | None = None
    audio_model: str | None = Field(default=None, max_length=180)
    widget_enabled: bool | None = None
    widget_greeting: str | None = Field(default=None, max_length=2000)
    widget_color: str | None = Field(default=None, max_length=20)
    widget_position: str | None = Field(default=None, pattern=r"^(right|left)$")
    is_active: bool | None = None


class AgentOut(ORMModel):
    id: uuid.UUID
    client_id: uuid.UUID
    provider: str
    name: str
    description: str
    instructions: str
    personality: str
    brief_summary: str
    brief_products: str
    brief_audience: str
    brief_policies: str
    brief_goal: str
    brief_dos: str
    brief_donts: str
    model: str
    timezone: str
    manual_context: str
    temperature: float
    max_tokens: int
    memory_limit: int
    image_enabled: bool
    image_model: str
    audio_enabled: bool
    audio_model: str
    widget_enabled: bool
    widget_public_id: str
    widget_greeting: str
    widget_color: str
    widget_position: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    client: ClientOut


class ManualContextRequest(BaseModel):
    manual_context: str


class QAPairCreate(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    answer: str = Field(min_length=1, max_length=8000)


class QAPairOut(ORMModel):
    id: uuid.UUID
    question: str
    answer: str


class ModelCatalogOut(BaseModel):
    id: str
    provider: str
    label: str
    family: str
    context_window: int
    max_output_tokens: int
    supports_tools: bool
    supports_vision: bool
    input_price_per_1k: float
    output_price_per_1k: float
    badge: str = ""
    note: str = ""


class DocumentOut(ORMModel):
    id: uuid.UUID
    filename: str
    status: str
    error_message: str | None
    created_at: datetime
    character_count: int = 0


class ConversationCreate(BaseModel):
    agent_id: uuid.UUID


class ConversationOut(ORMModel):
    id: uuid.UUID
    client_id: uuid.UUID
    agent_id: uuid.UUID
    title: str
    mode: str
    channel: str
    external_chat_id: str | None = None
    contact_name: str | None = None
    created_at: datetime
    updated_at: datetime
    preview: str = ""


class SourceOut(BaseModel):
    id: str
    filename: str
    excerpt: str = ""


class MessageOut(ORMModel):
    id: uuid.UUID
    role: str
    content: str
    sources: list[dict] = []
    tool_calls: list[dict] | None = None
    sender_type: str
    sender_name: str | None
    external_message_id: str | None = None
    created_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = []


class ConversationInboxOut(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    agent_name: str
    client_id: uuid.UUID
    title: str
    contact_name: str | None = None
    channel: str
    mode: str
    preview: str = ""
    unread: bool = False
    unread_count: int = 0
    updated_at: datetime


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=50000)


class ConversationModeUpdate(BaseModel):
    mode: str = Field(pattern=r"^(ai|human)$")


class PortalLoginRequest(BaseModel):
    email: EmailStr
    password: str


class PortalPublicOut(BaseModel):
    client_name: str
    portal_title: str
    portal_slug: str
    agency_name: str
    agency_brand_color: str
    agency_logo_url: str | None


class PortalSessionOut(BaseModel):
    client_id: uuid.UUID
    client_name: str
    portal_slug: str
    agency_name: str
    portal_user_id: uuid.UUID | None = None
    portal_user_name: str | None = None
    portal_user_email: str | None = None
    password_configured: bool | None = None


class DashboardOut(BaseModel):
    clients: int
    active_clients: int
    agents: int
    active_agents: int
    conversations: int
    channels: int
    connected_channels: int
    recent_agents: list[AgentSummary]


class DailyPoint(BaseModel):
    date: str
    count: int


class TopAgent(BaseModel):
    id: uuid.UUID
    name: str
    conversations: int


class ModelUsage(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int


class DashboardMetrics(BaseModel):
    messages: int
    human_conversations: int
    by_channel: dict[str, int]
    daily_conversations: list[DailyPoint]
    top_agents: list[TopAgent]
    tokens_in: int
    tokens_out: int
    usage_by_model: list[ModelUsage]


class WhatsAppChannelUpdate(BaseModel):
    agent_id: uuid.UUID


class WhatsAppChannelOut(ORMModel):
    id: uuid.UUID
    client_id: uuid.UUID
    agent_id: uuid.UUID
    status: str
    phone_number: str | None
    display_name: str | None
    qr_code: str | None = None
    last_error: str | None
    is_enabled: bool
    has_session: bool = False
    last_connected_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WhatsAppInternalAuth(BaseModel):
    auth_state: dict


class WhatsAppInternalStatus(BaseModel):
    status: str = Field(pattern=r"^(disconnected|connecting|qr|connected|reconnecting|error)$")
    phone_number: str | None = None
    display_name: str | None = None
    qr_code: str | None = None
    error: str | None = None


class WidgetConfigOut(BaseModel):
    title: str
    greeting: str
    color: str
    position: str
    agency_name: str
    agency_logo_url: str | None = None


class WidgetMessageIn(BaseModel):
    session_id: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=8000)


class WidgetMessageOut(BaseModel):
    role: str
    content: str


class WidgetReply(BaseModel):
    mode: str
    reply: str | None = None
    messages: list[WidgetMessageOut] = []


class WhatsAppInbound(BaseModel):
    external_message_id: str = Field(min_length=1, max_length=255)
    remote_jid: str = Field(min_length=1, max_length=255)
    sender_name: str | None = Field(default=None, max_length=180)
    text: str = Field(default="", max_length=50000)
    # Optional media (base64) for voice notes / images, processed by the agent's
    # audio/image capabilities before reaching the model.
    media_kind: str | None = Field(default=None, pattern=r"^(image|audio)$")
    media_base64: str | None = None
    media_mime: str | None = Field(default=None, max_length=100)


class WhatsAppInboundResult(BaseModel):
    accepted: bool
    reply: str | None = None
    conversation_id: uuid.UUID | None = None
    mode: str | None = None
    outbound_message_id: uuid.UUID | None = None


class WhatsAppOutboundConfirm(BaseModel):
    message_id: uuid.UUID
    external_message_id: str = Field(min_length=1, max_length=255)


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(min_length=20)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    # agency | portal
    audience: str = Field(default="agency", pattern=r"^(agency|portal)$")
    portal_slug: str | None = None


class ForgotPasswordResponse(BaseModel):
    message: str
    # Present only when AUTH_EXPOSE_RESET_TOKEN=true (dev/tests).
    reset_token: str | None = None
    # google_only | reset_sent | unknown (always generic message to client)
    account_kind: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10)
    password: str = Field(min_length=8, max_length=128)


class SetPasswordRequest(BaseModel):
    token: str = Field(min_length=10)
    password: str = Field(min_length=8, max_length=128)


class AuthOptionsOut(BaseModel):
    google_enabled: bool
    google_client_id: str | None = None


class PortalUserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str | None = Field(default=None, min_length=8, max_length=128)


class PortalUserOut(ORMModel):
    id: uuid.UUID
    name: str
    email: EmailStr
    is_active: bool
    password_configured: bool
    created_at: datetime


class CarouselCreate(BaseModel):
    client_id: uuid.UUID
    title: str = Field(min_length=2, max_length=180)
    brief: str = ""
    language: str = Field(default="es", max_length=10)
    slide_count: int = Field(default=8, ge=3, le=12)
    generate: bool = True
    with_images: bool = True
    # True = AI interprets title/brief with company knowledge (RAG). False = use literal copy.
    interpret_prompt: bool = True


class CarouselGenerateRequest(BaseModel):
    with_images: bool = True
    interpret_prompt: bool | None = None
    # Always generate at least one image related to the description when OpenAI is available.
    ensure_min_image: bool = True


class CarouselSlideGenerateRequest(BaseModel):
    with_images: bool = True
    # When set, use this exact image prompt instead of the auto-built one.
    image_prompt: str | None = Field(default=None, max_length=3500)
    # When False, keep existing headline/body/cta and only (re)generate the image.
    regenerate_copy: bool = True


class CarouselSlideUpdate(BaseModel):
    headline: str | None = Field(default=None, max_length=240)
    body: str | None = None
    cta: str | None = Field(default=None, max_length=180)
    # Agency admin only: persist a custom image prompt for the next regenerate.
    image_prompt: str | None = Field(default=None, max_length=3500)


class CarouselSlideDecision(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)


class CarouselScheduleRequest(BaseModel):
    scheduled_at: datetime


class CarouselSlideOut(ORMModel):
    id: uuid.UUID
    position: int
    headline: str
    body: str
    cta: str
    layout_json: dict
    image_url: str | None = None
    # Present for agency sessions; portal responses omit these via router.
    image_prompt: str | None = None
    image_error: str | None = None
    product_image_url: str | None = None
    agency_status: str
    client_status: str
    client_comment: str | None = None


class GenerationUsageItem(BaseModel):
    kind: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_usd: float = 0
    count: int = 1
    label: str | None = None


class GenerationUsageOut(BaseModel):
    items: list[GenerationUsageItem] = []
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_usd: float = 0


class ImageCostQuoteOut(BaseModel):
    available: bool
    billable: bool
    provider: str
    model: str
    fallback_model: str | None = None
    size: str
    quality: str | None = None
    usd_per_image: float | None = None
    usd_per_image_fallback: float | None = None
    image_count: int
    usd_typical: float | None = None
    usd_if_fallback: float | None = None
    note: str = ""


class CarouselOut(ORMModel):
    id: uuid.UUID
    client_id: uuid.UUID
    title: str
    brief: str
    caption: str
    language: str
    status: str
    slide_count: int
    interpret_prompt: bool = True
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    ig_media_id: str | None = None
    publish_error: str | None = None
    content_item_id: uuid.UUID | None = None
    publication_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    generating_at: datetime | None = None
    is_generating: bool = False
    slides: list[CarouselSlideOut] = []
    generation_notes: list[str] = []
    generation_usage: GenerationUsageOut | None = None
