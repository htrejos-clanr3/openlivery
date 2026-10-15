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
  image_prompt?: string | null;
  image_error?: string | null;
  product_image_url?: string | null;
  agency_status: string;
  client_status: string;
  client_comment: string | null;
};

export type GenerationUsageItem = {
  kind: "copy" | "image" | string;
  provider: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  estimated_usd: number;
  count?: number;
  label?: string | null;
};

export type GenerationUsage = {
  items: GenerationUsageItem[];
  input_tokens: number;
  output_tokens: number;
  estimated_usd: number;
};

export type ImageCostQuote = {
  available: boolean;
  billable: boolean;
  provider: string;
  model: string;
  fallback_model?: string | null;
  size: string;
  quality?: string | null;
  usd_per_image: number | null;
  usd_per_image_fallback?: number | null;
  image_count: number;
  usd_typical: number | null;
  usd_if_fallback?: number | null;
  note: string;
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
  interpret_prompt?: boolean;
  content_goal?: "loyalty" | "reach" | "convert" | string;
  cta_instruction?: string;
  hook_structure?: boolean;
  generation_notes?: string[];
  generation_usage?: GenerationUsage | null;
  generating_at?: string | null;
  is_generating?: boolean;
  scheduled_at: string | null;
  published_at: string | null;
  ig_media_id: string | null;
  linkedin_post_id?: string | null;
  publish_results?: Record<string, { ok?: boolean; provider_id?: string; error?: string }>;
  publish_error: string | null;
  content_item_id?: string | null;
  publication_id?: string | null;
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

export type ImageGenerationStatus = {
  provider: string;
  resolved_provider: string | null;
  model: string | null;
  base_url: string | null;
  size: string;
  ready: boolean;
  reachable: boolean;
  supports_product_edit: boolean;
  ollama_can_generate_ads: boolean;
  message: string;
  install_hint: string;
};

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
  assigned_user_id: string | null;
  assigned_user_name: string | null;
  labels: string[];
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
  assigned_user_id: string | null;
  assigned_user_name: string | null;
  labels: string[];
  created_at: string;
  updated_at: string;
  preview?: string;
  messages?: Message[];
};

export type AgencyMember = { id: string; name: string; email: string };
export type CannedReply = { id: string; shortcode: string; title: string; body: string; updated_at: string };

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

export type WhatsAppWebhookRegistration = {
  ok: boolean;
  code: string;
  message: string;
  host?: string | null;
  app_without_webhook?: boolean;
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
  webhook_registration?: WhatsAppWebhookRegistration | null;
};

export type WhatsAppCloudTemplate = {
  id?: string | null;
  name: string;
  language?: string | null;
  status?: string | null;
  category?: string | null;
  components?: Record<string, unknown>[];
};

export type MetaPlatformNote = {
  scope: string;
  label: string;
  diagnostics_available: boolean;
  mock_mode: boolean;
  message: string;
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
  meta_platform?: MetaPlatformNote | null;
};

export type MetaMcpStatus = {
  enabled: boolean;
  mock_mode: boolean;
  manage_enabled: boolean;
  url_configured: boolean;
  token_configured: boolean;
  meta_app_id: string | null;
  message: string | null;
};

export type MetaHealthSection = {
  status?: string;
  percentage?: number | null;
  call_volume?: number | null;
  limit?: number | null;
  window?: string | null;
  label?: string | null;
  throttle_status?: string | null;
  estimated_recovery_minutes?: number | null;
  missing?: string[];
  present?: string[];
  extra?: string[];
  items?: Array<Record<string, unknown>>;
  actions?: unknown[];
  count?: number;
  detail?: unknown;
  error?: string | null;
};

export type MetaHealth = {
  overall_status: string;
  enabled: boolean;
  mock_mode: boolean;
  app_id?: string | null;
  fetched_at?: string | null;
  time_range?: string | null;
  message?: string | null;
  app: MetaHealthSection;
  api_usage: MetaHealthSection;
  rate_limits: MetaHealthSection;
  webhooks: MetaHealthSection;
  app_review: MetaHealthSection;
  compliance: MetaHealthSection;
  deprecations: MetaHealthSection;
  alerts: Array<{ level?: string; code?: string; message?: string }>;
  manage_enabled?: boolean;
};

export type MetaDiagnostics = {
  status: string;
  checks: Array<{ name: string; status: string; message?: string | null }>;
  summary: { total: number; healthy: number; attention: number };
  health?: MetaHealth | null;
};

export type MetaWebhookInspect = {
  app_id?: string | null;
  fetched_at?: string | null;
  manage_enabled: boolean;
  expected: string[];
  present: string[];
  missing: string[];
  extra: string[];
  subscriptions: unknown[];
  callback_url?: string | null;
  raw_summary?: Record<string, unknown>;
};

export type MetaWebhookRepairPreview = {
  manage_enabled: boolean;
  changes: Array<{ op?: string; field?: string }>;
  missing: string[];
  extra_untouched: string[];
  note: string;
};

export type MetaWebhookTestResult = {
  test_id: string;
  status: string;
  meta_request_accepted: boolean;
  openlivery_received: boolean;
  latency_ms: number | null;
  event_type: string;
  error: string | null;
  steps: Record<string, unknown>;
};

export type MetaWebhookTestHistory = {
  id: string;
  test_id: string;
  event_type: string;
  status: string;
  requested_at: string;
  received_at: string | null;
  latency_ms: number | null;
  error: string | null;
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

export type LinkedInChannel = {
  id: string;
  client_id: string;
  profile_url: string;
  display_name: string;
  voice_notes: string;
  status: "disconnected" | "connected" | "error" | string;
  member_id: string;
  access_token_configured: boolean;
  granted_scopes: string[];
  token_expires_at: string | null;
  last_error: string | null;
  last_connected_at: string | null;
  is_enabled: boolean;
  publishes: boolean;
  connection_mode: string;
  updated_at: string;
};

export type LinkedInDraft = {
  id: string;
  kind: string;
  idea: string;
  body: string;
  hook_id: number | null;
  human_score: number | null;
  verdict: string;
  status: "draft" | "published" | string;
  provider_post_id: string | null;
  published_at: string | null;
  created_at: string;
};

export type LinkedInOAuthOptions = {
  oauth_available: boolean;
  mock_mode: boolean;
  client_id: string | null;
  scopes: string[];
  redirect_path: string;
  api_version: string;
  blocked_reason: string | null;
};

export type LinkedInOAuthSession = {
  state: string;
  dialog_url: string | null;
  mock_mode: boolean;
};

export type LinkedInPublication = {
  draft_id: string;
  status: string;
  provider_post_id: string;
  published_at: string;
  text: string;
};

export type LinkedInHookOption = { id: number; name: string; line: string; why?: string };

export type LinkedInPostResult = {
  hooks: LinkedInHookOption[];
  chosen_hook_id: number;
  draft: string;
  copy_ready: string;
  post_at_hint: string;
  source: string;
  draft_id?: string;
  humanize: {
    stripped: number;
    structures: { name: string; count: number; fix: string }[];
    panel: { human_score: number; verdict: string; checks: Record<string, { score: number; detail: string }> };
  };
};

export type LinkedInProfileResult = {
  headline: string;
  about: string;
  featured?: string[];
  audit?: { total: number; max: number; items: { id: string; points: number; score: number; full_marks: string }[] };
  copy_note?: string;
  humanize?: { panel: { human_score: number; verdict: string } };
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

export type LeadContact = {
  id: string;
  client_id: string;
  name: string;
  company?: string;
  email: string | null;
  phone: string | null;
  channel_identifier: string | null;
  source: string;
};

export type LeadActivity = {
  id: string;
  kind: string;
  message: string;
  created_at: string;
};

export type LeadRecord = {
  id: string;
  client_id: string;
  source: string;
  tags: string[];
  contact: LeadContact;
  conversation_id: string | null;
  pipeline_id: string | null;
  stage_id: string | null;
  stage_name: string | null;
  stage_slug?: string | null;
  assigned_user_id: string | null;
  assignee_name: string | null;
  notes?: string;
  next_action?: string;
  score?: number | null;
  last_activity_at?: string | null;
  created_at: string;
  updated_at: string;
  activities?: LeadActivity[];
};

export type LeadStats = {
  new_count: number;
  qualified_count: number;
  unassigned_count: number;
  stale_count: number;
  total_count: number;
};

export type LeadCaptureSettings = {
  id: string;
  client_id: string;
  enabled: boolean;
  sources: string[];
  default_pipeline_id: string | null;
  default_stage_id: string | null;
  default_assignee_user_id: string | null;
  auto_tags: string[];
  notify_on_new_lead: boolean;
  ingest_token: string;
  last_ingest_at?: string | null;
  last_ingest_status?: string | null;
  leads_created_count?: number;
  automation_config?: { triggers?: string[]; require_commercial_intent?: boolean };
  pipeline: { id: string; name: string; is_default: boolean; stages: { id: string; name: string; slug: string; position: number }[] } | null;
  assignees: { id: string; name: string; email: string }[];
};

export type LeadCaptureEvent = {
  id: string;
  client_id: string;
  source: string;
  status: string;
  error_message: string | null;
  lead_id: string | null;
  contact_id: string | null;
  conversation_id: string | null;
  attempt_count: number;
  created_at: string;
  updated_at: string;
};

export type LeadNotification = {
  id: string;
  client_id: string;
  lead_id: string;
  kind: string;
  read_at: string | null;
  created_at: string;
  contact_name: string;
  source: string;
};
