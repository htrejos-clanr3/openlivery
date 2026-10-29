import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Numeric, Boolean, DateTime, Float, ForeignKey, Integer, JSON, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


def new_public_id() -> str:
    return uuid.uuid4().hex


def new_domain_token() -> str:
    return uuid.uuid4().hex


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Agency(Base):
    __tablename__ = "agencies"
    meta_app_id: Mapped[str] = mapped_column(String(64), default="", server_default="")
    encrypted_meta_app_secret: Mapped[str | None] = mapped_column(Text, nullable=True)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(180))
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    brand_color: Mapped[str] = mapped_column(String(20), default="#075985")
    logo_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    logo_mime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    users: Mapped[list["User"]] = relationship(back_populates="agency", cascade="all, delete-orphan")

    @property
    def logo_url(self) -> str | None:
        return f"/api/agency/logo?v={int(self.created_at.timestamp())}" if self.logo_data else None


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(320), index=True)
    # Nullable when the user only signs in with Google (password OR Google).
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(30), default="admin")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    agency: Mapped[Agency] = relationship(back_populates="users")
    automation_runs: Mapped[list["UserAutomationRun"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    assigned_leads: Mapped[list["Lead"]] = relationship(back_populates="assignee", foreign_keys="Lead.assigned_user_id")
    assigned_conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="assigned_user", foreign_keys="Conversation.assigned_user_id"
    )
    lead_notifications: Mapped[list["LeadNotification"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def password_configured(self) -> bool:
        return bool(self.password_hash)


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    industry: Mapped[str] = mapped_column(String(160), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    general_context: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    portal_slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    portal_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    portal_title: Mapped[str] = mapped_column(String(180), default="")
    portal_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    portal_password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Optional custom domain for this client's portal. Verified via a DNS TXT
    # challenge; only verified domains are routed and get an on-demand cert.
    portal_domain: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    portal_domain_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    portal_domain_token: Mapped[str] = mapped_column(String(64), default="", server_default="")
    # Brand DNA for carousel generation (Pomelli-like).
    brand_primary_color: Mapped[str] = mapped_column(String(20), default="#075985", server_default="#075985")
    brand_secondary_color: Mapped[str] = mapped_column(String(20), default="#0f172a", server_default="#0f172a")
    brand_font: Mapped[str] = mapped_column(String(80), default="", server_default="")
    brand_voice: Mapped[str] = mapped_column(Text, default="", server_default="")
    brand_logo_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    brand_logo_mime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    agents: Mapped[list["Agent"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    portal_users: Mapped[list["PortalUser"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    carousels: Mapped[list["Carousel"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    whatsapp_channel: Mapped["WhatsAppChannel | None"] = relationship(
        back_populates="client", cascade="all, delete-orphan", uselist=False
    )
    whatsapp_cloud_channel: Mapped["WhatsAppCloudChannel | None"] = relationship(
        back_populates="client", cascade="all, delete-orphan", uselist=False
    )
    instagram_channel: Mapped["InstagramChannel | None"] = relationship(
        back_populates="client", cascade="all, delete-orphan", uselist=False
    )
    linkedin_channel: Mapped["LinkedInChannel | None"] = relationship(
        back_populates="client", cascade="all, delete-orphan", uselist=False
    )
    media_assets: Mapped[list["MediaAsset"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    content_items: Mapped[list["ContentItem"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    publications: Mapped[list["Publication"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    lead_capture_settings: Mapped["LeadCaptureSettings | None"] = relationship(
        back_populates="client", cascade="all, delete-orphan", uselist=False
    )
    lead_pipelines: Mapped[list["LeadPipeline"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    contacts: Mapped[list["Contact"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    leads: Mapped[list["Lead"]] = relationship(back_populates="client", cascade="all, delete-orphan")

    @property
    def portal_password_configured(self) -> bool:
        return bool(self.portal_password_hash)

    @property
    def brand_logo_url(self) -> str | None:
        if not self.brand_logo_data:
            return None
        return f"/api/clients/{self.id}/brand-logo?v={int(self.updated_at.timestamp())}"


class ProviderCredential(Base):
    """One AI provider API key per agency (bring your own key). provider is
    "openai" or "anthropic"; the base URL is resolved from the provider."""

    __tablename__ = "provider_credentials"
    __table_args__ = (UniqueConstraint("agency_id", "provider", name="uq_provider_credentials_agency_provider"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(30))
    encrypted_api_key: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    instructions: Mapped[str] = mapped_column(Text, default="")
    personality: Mapped[str] = mapped_column(Text, default="")
    # Structured business brief. Optional guided fields that compose into the
    # system prompt alongside the free-form instructions.
    brief_summary: Mapped[str] = mapped_column(Text, default="", server_default="")
    brief_products: Mapped[str] = mapped_column(Text, default="", server_default="")
    brief_audience: Mapped[str] = mapped_column(Text, default="", server_default="")
    brief_policies: Mapped[str] = mapped_column(Text, default="", server_default="")
    brief_goal: Mapped[str] = mapped_column(Text, default="", server_default="")
    brief_dos: Mapped[str] = mapped_column(Text, default="", server_default="")
    brief_donts: Mapped[str] = mapped_column(Text, default="", server_default="")
    # AI provider ("openai" or "anthropic"); the agency's key for that provider is used.
    provider: Mapped[str] = mapped_column(String(30), default="openai", server_default="openai")
    model: Mapped[str] = mapped_column(String(180), default="")
    # IANA timezone (e.g. "America/Bogota"); injected into the system prompt so
    # the agent knows the local date/time. "UTC" when unset.
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", server_default="UTC")
    manual_context: Mapped[str] = mapped_column(Text, default="")
    # Generation settings. Sampling params are applied best-effort by the AI
    # service (models that reject them fall back to their defaults).
    temperature: Mapped[float] = mapped_column(Float, default=0.7, server_default="0.7")
    max_tokens: Mapped[int] = mapped_column(Integer, default=2048, server_default="2048")
    # How many past messages are kept as conversation memory.
    memory_limit: Mapped[int] = mapped_column(Integer, default=30, server_default="30")
    # Multimodal capabilities. When enabled, inbound images are described by a
    # vision model and inbound audio is transcribed before reaching the agent.
    image_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    image_model: Mapped[str] = mapped_column(String(180), default="", server_default="")
    audio_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    audio_model: Mapped[str] = mapped_column(String(180), default="whisper-1", server_default="whisper-1")
    # Embeddable web chat widget.
    widget_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    widget_public_id: Mapped[str] = mapped_column(String(64), default=new_public_id, unique=True, index=True)
    widget_greeting: Mapped[str] = mapped_column(Text, default="", server_default="")
    widget_color: Mapped[str] = mapped_column(String(20), default="", server_default="")
    widget_position: Mapped[str] = mapped_column(String(10), default="right", server_default="right")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    client: Mapped[Client] = relationship(back_populates="agents")
    documents: Mapped[list["KnowledgeDocument"]] = relationship(back_populates="agent", cascade="all, delete-orphan")
    qa_pairs: Mapped[list["AgentQA"]] = relationship(back_populates="agent", cascade="all, delete-orphan", order_by="AgentQA.position")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="agent", cascade="all, delete-orphan")
    whatsapp_channels: Mapped[list["WhatsAppChannel"]] = relationship(back_populates="agent")
    whatsapp_cloud_channels: Mapped[list["WhatsAppCloudChannel"]] = relationship(back_populates="agent")
    tools: Mapped[list["AgentTool"]] = relationship(back_populates="agent", cascade="all, delete-orphan", order_by="AgentTool.created_at")


class AgentTool(Base):
    """A custom tool the agent can call: a user-defined HTTP endpoint
    ("http") or an external MCP server ("mcp")."""

    __tablename__ = "agent_tools"
    __table_args__ = (UniqueConstraint("agent_id", "name", name="uq_agent_tools_agent_name"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(10))
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # HTTP endpoint (may contain {param} path placeholders) or MCP server URL.
    url: Mapped[str] = mapped_column(Text, default="")
    # HTTP tools only.
    http_method: Mapped[str] = mapped_column(String(10), default="GET")
    prompt_instructions: Mapped[str] = mapped_column(Text, default="")
    body_params: Mapped[list] = mapped_column(JSON, default=list)
    query_params: Mapped[list] = mapped_column(JSON, default=list)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)
    # MCP servers only. cached_tools holds the last list_tools result so chat
    # requests never block on discovery; refreshed on save/test-connection.
    transport: Mapped[str] = mapped_column(String(20), default="streamable_http")
    cached_tools: Mapped[list] = mapped_column(JSON, default=list)
    tools_cached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # The full auth headers dict, encrypted at rest; never returned by the API.
    encrypted_headers: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    agent: Mapped[Agent] = relationship(back_populates="tools")


class WhatsAppChannel(Base):
    __tablename__ = "whatsapp_channels"
    __table_args__ = (UniqueConstraint("client_id", name="uq_whatsapp_channels_client_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="disconnected")
    phone_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    encrypted_auth_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted_qr: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    client: Mapped[Client] = relationship(back_populates="whatsapp_channel")
    agent: Mapped[Agent] = relationship(back_populates="whatsapp_channels")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="whatsapp_channel")


class WhatsAppCloudChannel(Base):
    """Official WhatsApp Business Cloud API channel (Meta Graph API). Coexists
    with the Baileys channel: a client can have one of each, on different
    numbers. Credentials are provided manually (bring your own Meta app)."""

    __tablename__ = "whatsapp_cloud_channels"
    __table_args__ = (UniqueConstraint("client_id", name="uq_whatsapp_cloud_channels_client_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="disconnected")
    phone_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    phone_number_id: Mapped[str] = mapped_column(String(80), default="", server_default="")
    waba_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    encrypted_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted_app_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Token the owner pastes into their Meta app's webhook config; it must be
    # re-displayable, so it is stored in plain text like portal_domain_token.
    webhook_verify_token: Mapped[str] = mapped_column(String(64), default=new_public_id, server_default="")
    # manual = BYO Meta app; managed/embedded = Fast Livery platform Meta app / signup.
    connection_mode: Mapped[str] = mapped_column(String(20), default="manual", server_default="manual")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    client: Mapped[Client] = relationship(back_populates="whatsapp_cloud_channel")
    agent: Mapped[Agent] = relationship(back_populates="whatsapp_cloud_channels")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="whatsapp_cloud_channel")


class AgentQA(Base):
    __tablename__ = "agent_qa"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    agent: Mapped[Agent] = relationship(back_populates="qa_pairs")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_data: Mapped[bytes] = mapped_column(LargeBinary)
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="processed")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    agent: Mapped[Agent] = relationship(back_populates="documents")
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text)
    # Embedding vector stored as a JSON array of floats (portable across any
    # Postgres; similarity is computed in Python). Swap to pgvector at scale.
    embedding: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(180))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("whatsapp_channel_id", "external_chat_id", name="uq_conversations_whatsapp_chat"),
        UniqueConstraint(
            "whatsapp_cloud_channel_id", "external_chat_id", name="uq_conversations_whatsapp_cloud_chat"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240), default="New conversation")
    mode: Mapped[str] = mapped_column(String(30), default="ai")
    channel: Mapped[str] = mapped_column(String(40), default="playground")
    whatsapp_channel_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("whatsapp_channels.id", ondelete="CASCADE"), nullable=True, index=True
    )
    whatsapp_cloud_channel_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("whatsapp_cloud_channels.id", ondelete="CASCADE"), nullable=True, index=True
    )
    external_chat_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    contact_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    operator_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    labels: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    agent: Mapped[Agent] = relationship(back_populates="conversations")
    assigned_user: Mapped[User | None] = relationship(
        back_populates="assigned_conversations", foreign_keys=[assigned_user_id]
    )
    whatsapp_channel: Mapped[WhatsAppChannel | None] = relationship(back_populates="conversations")
    whatsapp_cloud_channel: Mapped[WhatsAppCloudChannel | None] = relationship(back_populates="conversations")
    contact: Mapped["Contact | None"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    lead: Mapped["Lead | None"] = relationship(
        back_populates="conversation", uselist=False, foreign_keys="Lead.conversation_id"
    )

    @property
    def assigned_user_name(self) -> str | None:
        return self.assigned_user.name if self.assigned_user else None


class CannedReply(Base):
    __tablename__ = "canned_replies"
    __table_args__ = (UniqueConstraint("agency_id", "shortcode", name="uq_canned_replies_agency_shortcode"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    shortcode: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "external_message_id", name="uq_messages_conversation_external"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(30))
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[list] = mapped_column(JSON, default=list)
    # Tool usage behind an assistant reply: [{name, arguments, result_preview, is_error}].
    tool_calls: Mapped[list | None] = mapped_column(JSON, nullable=True)
    sender_type: Mapped[str] = mapped_column(String(30), default="visitor")
    sender_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    external_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class PortalUser(Base):
    """Registered portal user for a client. Auth: password OR Google (independent)."""

    __tablename__ = "portal_users"
    __table_args__ = (UniqueConstraint("client_id", "email", name="uq_portal_users_client_email"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(320), index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    client: Mapped[Client] = relationship(back_populates="portal_users")

    @property
    def password_configured(self) -> bool:
        return bool(self.password_hash)


class OAuthAccount(Base):
    """Google (or other) OAuth subject linked to an agency or portal user."""

    __tablename__ = "oauth_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "subject", name="uq_oauth_provider_subject"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    provider: Mapped[str] = mapped_column(String(30), default="google")
    subject: Mapped[str] = mapped_column(String(255), index=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    # Exactly one of these is set.
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    portal_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("portal_users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(320), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # agency | portal
    audience: Mapped[str] = mapped_column(String(20))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    portal_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("portal_users.id", ondelete="CASCADE"), nullable=True
    )
    # reset = forgot password; set = create password for Google-only account
    purpose: Mapped[str] = mapped_column(String(20), default="reset")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Carousel(Base):
    __tablename__ = "carousels"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    approved_by_portal_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("portal_users.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(180))
    brief: Mapped[str] = mapped_column(Text, default="")
    caption: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(10), default="es")
    # When True, AI expands title/brief using company DNA + RAG/embeddings.
    # When False, treat title/brief as literal copy to format into slides.
    interpret_prompt: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # Instagram format playbook: loyalty | reach | convert.
    content_goal: Mapped[str] = mapped_column(String(20), default="loyalty", server_default="loyalty")
    cta_instruction: Mapped[str] = mapped_column(String(180), default="", server_default="")
    hook_structure: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # once = single datetime (scheduled_at). weekly_window = weekdays + local time range.
    schedule_mode: Mapped[str] = mapped_column(String(20), default="once", server_default="once")
    schedule_weekdays: Mapped[list] = mapped_column(JSON, default=list)  # 0=Mon … 6=Sun
    schedule_window_start: Mapped[str] = mapped_column(String(5), default="08:00", server_default="08:00")
    schedule_window_end: Mapped[str] = mapped_column(String(5), default="10:00", server_default="10:00")
    schedule_timezone: Mapped[str] = mapped_column(String(64), default="America/Bogota", server_default="America/Bogota")
    # draft | in_review | approved | rejected | scheduled | published | failed
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    slide_count: Mapped[int] = mapped_column(Integer, default=8)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ig_media_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    linkedin_post_id: Mapped[str | None] = mapped_column(String(300), nullable=True)
    publish_results: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    publish_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("content_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    publication_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("publications.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    generating_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    client: Mapped[Client] = relationship(back_populates="carousels")
    slides: Mapped[list["CarouselSlide"]] = relationship(
        back_populates="carousel", cascade="all, delete-orphan", order_by="CarouselSlide.position"
    )
    events: Mapped[list["CarouselEvent"]] = relationship(back_populates="carousel", cascade="all, delete-orphan")


class CarouselSlide(Base):
    __tablename__ = "carousel_slides"
    __table_args__ = (UniqueConstraint("carousel_id", "position", name="uq_carousel_slides_position"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    carousel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("carousels.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    headline: Mapped[str] = mapped_column(String(240), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    cta: Mapped[str] = mapped_column(String(180), default="")
    layout_json: Mapped[dict] = mapped_column(JSON, default=dict)
    image_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    image_mime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Last prompt sent to the image model (agency-editable for retries).
    image_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Optional source product photo; used with /images/edits to clean bg and restage.
    product_image_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    product_image_mime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # pending | agency_ok | client_ok | rejected
    agency_status: Mapped[str] = mapped_column(String(30), default="pending")
    client_status: Mapped[str] = mapped_column(String(30), default="pending")
    client_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    carousel: Mapped[Carousel] = relationship(back_populates="slides")

    @property
    def image_url(self) -> str | None:
        if not self.image_data:
            return None
        return f"/api/carousels/{self.carousel_id}/slides/{self.id}/image?v={int(self.updated_at.timestamp())}"


class CarouselEvent(Base):
    __tablename__ = "carousel_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    carousel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("carousels.id", ondelete="CASCADE"), index=True)
    actor_type: Mapped[str] = mapped_column(String(30))  # agency | portal | system
    actor_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    carousel: Mapped[Carousel] = relationship(back_populates="events")


class InstagramChannel(Base):
    """Per-client Instagram professional account for Content Publishing (not DMs)."""

    __tablename__ = "instagram_channels"
    __table_args__ = (UniqueConstraint("client_id", name="uq_instagram_channels_client_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="disconnected")
    instagram_user_id: Mapped[str] = mapped_column(String(80), default="", server_default="")
    page_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    username: Mapped[str | None] = mapped_column(String(180), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    encrypted_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    granted_scopes: Mapped[list] = mapped_column(JSON, default=list)
    # oauth | manual | mock
    connection_mode: Mapped[str] = mapped_column(String(20), default="manual", server_default="manual")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    client: Mapped[Client] = relationship(back_populates="instagram_channel")


class LinkedInChannel(Base):
    """Per-client LinkedIn copy desk and personal-profile OAuth connection."""

    __tablename__ = "linkedin_channels"
    __table_args__ = (UniqueConstraint("client_id", name="uq_linkedin_channels_client_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    profile_url: Mapped[str] = mapped_column(String(400), default="", server_default="")
    display_name: Mapped[str] = mapped_column(String(180), default="", server_default="")
    voice_notes: Mapped[str] = mapped_column(Text, default="", server_default="")
    status: Mapped[str] = mapped_column(String(30), default="disconnected", server_default="disconnected")
    member_id: Mapped[str] = mapped_column(String(180), default="", server_default="")
    encrypted_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    granted_scopes: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    connection_mode: Mapped[str] = mapped_column(String(30), default="copy_paste", server_default="copy_paste")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    client: Mapped[Client] = relationship(back_populates="linkedin_channel")
    drafts: Mapped[list["LinkedInDraft"]] = relationship(
        back_populates="channel", cascade="all, delete-orphan"
    )


class LinkedInDraft(Base):
    __tablename__ = "linkedin_drafts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    channel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("linkedin_channels.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(30), default="post")
    idea: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    hook_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    human_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    verdict: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[str] = mapped_column(String(30), default="draft", server_default="draft")
    provider_post_id: Mapped[str | None] = mapped_column(String(300), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    channel: Mapped[LinkedInChannel] = relationship(back_populates="drafts")


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), default="")
    mime_type: Mapped[str] = mapped_column(String(100), default="application/octet-stream")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    file_data: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    client: Mapped[Client] = relationship(back_populates="media_assets")


class PostPiece(Base):
    """Channel-agnostic editorial unit (Instagram first; Facebook/LinkedIn later)."""

    __tablename__ = "post_pieces"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    title: Mapped[str] = mapped_column(String(180), default="")
    caption: Mapped[str] = mapped_column(Text, default="")
    hashtags: Mapped[str] = mapped_column(Text, default="")
    cta: Mapped[str] = mapped_column(String(240), default="")
    # IMAGE | CAROUSEL | REEL
    content_type: Mapped[str] = mapped_column(String(30), default="IMAGE", index=True)
    # DRAFT | READY | SCHEDULED | PUBLISHED | FAILED | ARCHIVED
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", index=True)
    timezone: Mapped[str] = mapped_column(String(80), default="UTC", server_default="UTC")
    ai_meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    client: Mapped[Client] = relationship(back_populates="content_items")
    media_links: Mapped[list["ContentMedia"]] = relationship(
        back_populates="content", cascade="all, delete-orphan", order_by="ContentMedia.position"
    )
    publications: Mapped[list["Publication"]] = relationship(back_populates="content", cascade="all, delete-orphan")


class ContentMedia(Base):
    __tablename__ = "content_media"
    __table_args__ = (UniqueConstraint("content_id", "position", name="uq_content_media_position"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    content_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("content_items.id", ondelete="CASCADE"), index=True)
    media_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("media_assets.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    content: Mapped[ContentItem] = relationship(back_populates="media_links")
    media: Mapped[MediaAsset] = relationship()


class Publication(Base):
    __tablename__ = "publications"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_publications_idempotency_key"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    content_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("content_items.id", ondelete="CASCADE"), index=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # instagram | facebook | linkedin (future)
    channel: Mapped[str] = mapped_column(String(40), default="instagram", index=True)
    provider_account_id: Mapped[str] = mapped_column(String(80), default="")
    # DRAFT | QUEUED | PROCESSING | PUBLISHED | FAILED | CANCELLED
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", index=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone: Mapped[str] = mapped_column(String(80), default="UTC", server_default="UTC")
    provider_publication_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_container_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_permalink: Mapped[str | None] = mapped_column(String(500), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(80), default=new_public_id)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # TRANSIENT | PERMANENT | AUTH | VALIDATION | RATE_LIMIT
    error_class: Mapped[str | None] = mapped_column(String(40), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    client: Mapped[Client] = relationship(back_populates="publications")
    content: Mapped[ContentItem] = relationship(back_populates="publications")


class UserAutomationRun(Base):
    """One DeepSeek automation execution, visible only to the user who ran it."""

    __tablename__ = "user_automation_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    user: Mapped[User] = relationship(back_populates="automation_runs")


class LeadPipeline(Base):
    """Per-client pipeline. tenant = client_id (plus agency_id)."""

    __tablename__ = "lead_pipelines"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), default="Principal")
    is_default: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    client: Mapped[Client] = relationship(back_populates="lead_pipelines")
    stages: Mapped[list["LeadStage"]] = relationship(
        back_populates="pipeline", cascade="all, delete-orphan", order_by="LeadStage.position"
    )


class LeadStage(Base):
    __tablename__ = "lead_stages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lead_pipelines.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    slug: Mapped[str] = mapped_column(String(40))
    position: Mapped[int] = mapped_column(Integer, default=0)

    pipeline: Mapped[LeadPipeline] = relationship(back_populates="stages")


class LeadCaptureSettings(Base):
    """Automatic lead capture switchboard for one client tenant."""

    __tablename__ = "lead_capture_settings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    sources: Mapped[list] = mapped_column(JSON, default=list)
    default_pipeline_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lead_pipelines.id", ondelete="SET NULL"), nullable=True
    )
    default_stage_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lead_stages.id", ondelete="SET NULL"), nullable=True
    )
    default_assignee_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    auto_tags: Mapped[list] = mapped_column(JSON, default=list)
    notify_on_new_lead: Mapped[bool] = mapped_column(Boolean, default=True)
    ingest_token: Mapped[str] = mapped_column(String(64), unique=True, index=True, default=new_public_id)
    last_ingest_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    automation_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    client: Mapped[Client] = relationship(back_populates="lead_capture_settings")
    default_pipeline: Mapped[LeadPipeline | None] = relationship(foreign_keys=[default_pipeline_id])
    default_stage: Mapped[LeadStage | None] = relationship(foreign_keys=[default_stage_id])
    default_assignee: Mapped[User | None] = relationship(foreign_keys=[default_assignee_user_id])


class Contact(Base):
    """Person belonging to one client tenant. Deduped by phone, email, or channel id."""

    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(180), default="")
    company: Mapped[str] = mapped_column(String(180), default="")
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    channel_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(40), default="")
    extra: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    client: Mapped[Client] = relationship(back_populates="contacts")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="contact")
    leads: Mapped[list["Lead"]] = relationship(back_populates="contact", cascade="all, delete-orphan")


class Lead(Base):
    """Opportunity for one contact inside one client tenant. A contact may have many leads."""

    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    contact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contacts.id", ondelete="CASCADE"), index=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    pipeline_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lead_pipelines.id", ondelete="SET NULL"), nullable=True
    )
    stage_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("lead_stages.id", ondelete="SET NULL"), nullable=True)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source: Mapped[str] = mapped_column(String(40), default="")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")
    next_action: Mapped[str] = mapped_column(String(240), default="")
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    client: Mapped[Client] = relationship(back_populates="leads")
    contact: Mapped[Contact] = relationship(back_populates="leads")
    conversation: Mapped[Conversation | None] = relationship(
        back_populates="lead", foreign_keys=[conversation_id]
    )
    pipeline: Mapped[LeadPipeline | None] = relationship()
    stage: Mapped[LeadStage | None] = relationship()
    assignee: Mapped[User | None] = relationship(back_populates="assigned_leads", foreign_keys=[assigned_user_id])
    notifications: Mapped[list["LeadNotification"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    activities: Mapped[list["LeadActivity"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan", order_by="LeadActivity.created_at.desc()"
    )


class LeadNotification(Base):
    __tablename__ = "lead_notifications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(40), default="new_lead")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    user: Mapped[User] = relationship(back_populates="lead_notifications")
    lead: Mapped[Lead] = relationship(back_populates="notifications")


class LeadActivity(Base):
    """Commercial history on a lead (capture, notes, stage changes)."""

    __tablename__ = "lead_activities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    kind: Mapped[str] = mapped_column(String(40), default="note")
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    lead: Mapped[Lead] = relationship(back_populates="activities")


class IdealCustomerProfile(Base):
    """The client's ideal customer, used to score leads deterministically."""

    __tablename__ = "ideal_customer_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), unique=True, index=True
    )
    sectors: Mapped[list] = mapped_column(JSON, default=list)
    cities: Mapped[list] = mapped_column(JSON, default=list)
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    disqualifiers: Mapped[list] = mapped_column(JSON, default=list)
    size_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    size_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hot_min: Mapped[int] = mapped_column(Integer, default=75, server_default="75")
    warm_min: Mapped[int] = mapped_column(Integer, default=45, server_default="45")
    auto_qualify: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    client: Mapped[Client] = relationship()


class Product(Base):
    """Canonical product of one client. Destinations consume it, never own it."""

    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("client_id", "sku", name="uq_products_client_sku"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    sku: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="")
    availability: Mapped[str] = mapped_column(String(20), default="in_stock")
    image_url: Mapped[str] = mapped_column(String(600), default="")
    url: Mapped[str] = mapped_column(String(600), default="")
    gtin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    brand: Mapped[str] = mapped_column(String(120), default="")
    category: Mapped[str] = mapped_column(String(160), default="")
    source: Mapped[str] = mapped_column(String(20), default="file")
    status: Mapped[str] = mapped_column(String(20), default="valid")
    messages: Mapped[list] = mapped_column(JSON, default=list)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class LeadCaptureEvent(Base):
    """Audit row for each capture attempt. Failed rows can be retried."""

    __tablename__ = "lead_capture_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(40), default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="success", index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("leads.id", ondelete="SET NULL"), nullable=True)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class LegalAcceptance(Base):
    """Audit log of platform, channel-connect, and publish consents."""

    __tablename__ = "legal_acceptances"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True)
    acceptance_type: Mapped[str] = mapped_column(String(40), index=True)
    document_key: Mapped[str] = mapped_column(String(80), index=True)
    document_version: Mapped[str] = mapped_column(String(40), default="")
    channel: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)




class MetaWebhookTest(Base):
    """History of Meta DevTools MCP webhook test probes (diagnostics only)."""

    __tablename__ = "meta_webhook_tests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    test_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    app_id: Mapped[str] = mapped_column(String(80), default="")
    event_type: Mapped[str] = mapped_column(String(80), default="messages")
    # requested | sent | received | processed | failed
    status: Mapped[str] = mapped_column(String(30), default="requested")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
