export type User = {
  id: string;
  name: string;
  email: string;
  role: string;
  password_configured?: boolean;
  agency: Agency;
};

export type Agency = { id: string; name: string; slug: string; brand_color: string; logo_url: string | null };

export type AgentSummary = { id: string; name: string; description: string; is_active: boolean };

export type Client = {
  id: string;
  name: string;
  industry: string;
  description: string;
  general_context: string;
  is_active: boolean;
  portal_slug: string;
  portal_enabled: boolean;
  portal_title: string;
  portal_email: string | null;
  portal_password_configured: boolean;
  portal_domain: string | null;
  portal_domain_verified: boolean;
  brand_primary_color?: string;
  brand_secondary_color?: string;
  brand_font?: string;
  brand_voice?: string;
  brand_logo_url?: string | null;
  agents: AgentSummary[];
  created_at: string;
  updated_at: string;
};

export type CarouselSlide = {
  id: string;
  position: number;
  headline: string;
  body: string;
  cta: string;
  layout_json: Record<string, unknown>;
  image_url: string | null;
  agency_status: string;
  client_status: string;
  client_comment: string | null;
};

export type Carousel = {
  id: string;
  client_id: string;
  title: string;
  brief: string;
  caption: string;
  language: string;
  status: string;
  slide_count: number;
  scheduled_at: string | null;
  published_at: string | null;
  ig_media_id: string | null;
  publish_error: string | null;
  created_at: string;
  updated_at: string;
  slides: CarouselSlide[];
};

export type ClientDomain = {
  domain: string | null;
  verified: boolean;
  txt_host: string | null;
  txt_value: string | null;
};

export type Agent = {
  id: string;
  client_id: string;
  provider: string;
  name: string;
  description: string;
  instructions: string;
  personality: string;
  brief_summary: string;
  brief_products: string;
  brief_audience: string;
  brief_policies: string;
  brief_goal: string;
  brief_dos: string;
  brief_donts: string;
  model: string;
  timezone: string;
  manual_context: string;
  temperature: number;
  max_tokens: number;
  memory_limit: number;
  image_enabled: boolean;
  image_model: string;
  audio_enabled: boolean;
  audio_model: string;
  widget_enabled: boolean;
  widget_public_id: string;
  widget_greeting: string;
  widget_color: string;
  widget_position: string;
  is_active: boolean;
  client: Client;
  created_at: string;
  updated_at: string;
};

export type Provider = {
  provider: string;
  label: string;
  configured: boolean;
  api_key_masked: string;
};

export type ProviderTest = { ok: boolean; message: string; models: string[] };

export type KnowledgeDocument = {
  id: string;
  filename: string;
  status: "processed" | "error" | "pending";
  error_message: string | null;
  character_count: number;
  created_at: string;
};

export type QAPair = { id: string; question: string; answer: string };

export type ToolParam = { name: string; type: "string" | "number" | "integer" | "boolean"; description: string; required: boolean };
export type McpCachedTool = { name: string; description: string; input_schema?: Record<string, unknown> };
export type AgentTool = {
  id: string;
  agent_id: string;
  type: "http" | "mcp";
  name: string;
  description: string;
  enabled: boolean;
  url: string;
  http_method: string;
  prompt_instructions: string;
  body_params: ToolParam[];
  query_params: ToolParam[];
  timeout_seconds: number;
  transport: "sse" | "streamable_http";
  cached_tools: McpCachedTool[];
  tools_cached_at: string | null;
  has_headers: boolean;
  created_at: string;
  updated_at: string;
};
export type ToolCallMeta = { name: string; arguments: Record<string, unknown>; result_preview: string; is_error: boolean };

export type Source = { id: string; filename: string; excerpt: string };
export type Message = { id: string; role: "user" | "assistant"; content: string; sources: Source[]; tool_calls?: ToolCallMeta[] | null; sender_type: "visitor" | "ai" | "human"; sender_name: string | null; created_at: string };

export type ConversationInbox = {
  id: string;
  agent_id: string;
  agent_name: string;
  client_id: string;
  title: string;
  contact_name: string | null;
  channel: string;
  mode: "ai" | "human";
  preview: string;
  unread: boolean;
  unread_count: number;
  updated_at: string;
};
export type Conversation = {
  id: string;
  client_id: string;
  agent_id: string;
  title: string;
  mode: "ai" | "human";
  channel: string;
  external_chat_id: string | null;
  contact_name: string | null;
  created_at: string;
  updated_at: string;
  preview?: string;
  messages?: Message[];
};

export type WhatsAppChannel = {
  id: string;
  client_id: string;
  agent_id: string;
  status: "disconnected" | "connecting" | "qr" | "connected" | "reconnecting" | "error";
  phone_number: string | null;
  display_name: string | null;
  qr_code: string | null;
  last_error: string | null;
  is_enabled: boolean;
  has_session: boolean;
  last_connected_at: string | null;
  created_at: string;
  updated_at: string;
};

export type WhatsAppCloudChannel = {
  id: string;
  client_id: string;
  agent_id: string;
  status: "disconnected" | "connected" | "error";
  connection_mode?: "manual" | "managed" | "embedded";
  phone_number: string | null;
  display_name: string | null;
  phone_number_id: string;
  waba_id: string | null;
  has_access_token: boolean;
  has_app_secret: boolean;
  webhook_url: string;
  webhook_verify_token: string;
  last_error: string | null;
  error_message?: string | null;
  error_code?: string | null;
  is_enabled: boolean;
  last_connected_at: string | null;
  created_at: string;
  updated_at: string;
};

export type WhatsAppCloudHealth = {
  connected: boolean;
  ui_status: string;
  connection_mode: string;
  status: string;
  phone_number: string | null;
  display_name: string | null;
  phone_number_id: string | null;
  waba_id: string | null;
  waba_configured: boolean;
  token_configured: boolean;
  app_secret_configured: boolean;
  permissions_valid: boolean;
  webhook_configured: boolean;
  agent_assigned: boolean;
  is_enabled: boolean;
  graph_reachable: boolean;
  last_inbound_message_at: string | null;
  last_outbound_message_at: string | null;
  last_connected_at: string | null;
  last_error: string | null;
  error: { message: string; code: string; technical: string } | null;
};

export type WhatsAppSignupOptions = {
  managed_available: boolean;
  mock_mode: boolean;
  meta_app_id: string | null;
  meta_config_id: string | null;
  graph_version: string;
  blocked_reason: string | null;
};

export type WhatsAppSignupSession = {
  state: string;
  meta_app_id: string | null;
  meta_config_id: string | null;
  mock_mode: boolean;
  redirect_url: string | null;
  blocked_reason: string | null;
};

export type PortalPublic = {
  client_name: string;
  portal_title: string;
  portal_slug: string;
  agency_name: string;
  agency_brand_color: string;
  agency_logo_url: string | null;
};

export type InstagramChannel = {
  id: string;
  client_id: string;
  status: "disconnected" | "connected" | "error" | string;
  instagram_user_id: string;
  page_id: string | null;
  username: string | null;
  display_name: string | null;
  access_token_configured: boolean;
  token_expires_at: string | null;
  granted_scopes: string[];
  connection_mode: "oauth" | "manual" | "mock" | string;
  last_error: string | null;
  is_enabled: boolean;
  last_connected_at: string | null;
  publish_permission: boolean;
};

export type InstagramOAuthOptions = {
  oauth_available: boolean;
  mock_mode: boolean;
  meta_app_id: string | null;
  graph_version: string;
  scopes: string[];
  redirect_path: string;
  blocked_reason: string | null;
};

export type InstagramOAuthSession = {
  state: string;
  dialog_url: string | null;
  mock_mode: boolean;
};

export type InstagramHealth = {
  ui_status: string;
  account_ok: boolean;
  token_ok: boolean;
  publish_permission_ok: boolean;
  api_ok: boolean;
  mock_mode: boolean;
  details: Record<string, unknown>;
};

export type InstagramPublishingLimit = {
  quota_usage: number | null;
  quota_total: number | null;
  quota_duration: number | null;
  available: boolean;
};

export type InstagramMediaAsset = {
  id: string;
  client_id: string;
  file_name: string;
  mime_type: string;
  file_size: number;
  width: number | null;
  height: number | null;
  duration: number | null;
  created_at: string;
  preview_url: string | null;
};

export type InstagramContentMedia = {
  media_id: string;
  position: number;
  file_name: string | null;
  mime_type: string | null;
  preview_url: string | null;
};

export type InstagramContentItem = {
  id: string;
  client_id: string;
  title: string;
  caption: string;
  hashtags: string;
  cta: string;
  content_type: "IMAGE" | "CAROUSEL" | "REEL" | string;
  status: string;
  timezone: string;
  ai_meta: Record<string, unknown>;
  media: InstagramContentMedia[];
  created_at: string;
  updated_at: string;
};

export type InstagramPublication = {
  id: string;
  client_id: string;
  content_id: string;
  channel: string;
  provider_account_id: string;
  status: string;
  scheduled_at: string | null;
  published_at: string | null;
  timezone: string;
  provider_publication_id: string | null;
  provider_container_id: string | null;
  provider_permalink: string | null;
  error_code: string | null;
  error_message: string | null;
  error_class: string | null;
  attempt_count: number;
  created_at: string;
  updated_at: string;
};

export type InstagramDashboardStats = {
  drafts: number;
  scheduled: number;
  published_month: number;
  failed: number;
};

export type InstagramGenerateRequest = {
  content_type: string;
  objective: string;
  audience?: string;
  user_instruction?: string;
  slide_count?: number;
  language?: string;
};

export type InstagramGenerateResult = {
  title: string;
  caption: string;
  cta: string;
  hashtags: string[];
  visualSuggestion?: string | null;
  imagePrompt?: string | null;
  slides?: { headline?: string; body?: string; cta?: string }[] | null;
};
