export interface HealthResponse {
  status: string;
  version: string;
  db: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface ChatStartResponse {
  session_id: string;
  message: string;
  quick_replies: string[];
}

export interface SourceReference {
  document_title: string;
  chunk_text: string;
  score: number;
}

export interface HandoffInfo {
  should_handoff: boolean;
  reason: string | null;
  message: string;
  contact_phone: string | null;
  contact_instagram: string | null;
}

export interface ChatMessageResponse {
  message_id: string;
  conversation_id: string;
  content: string;
  intent: string | null;
  sources: SourceReference[];
  handoff: HandoffInfo;
  lead_capture_suggested: boolean;
  suggested_replies: string[];
}

export interface StreamChunk {
  content: string;
}

export interface StreamDone {
  message_id: string;
  conversation_id: string;
  content: string;
  intent: string | null;
  sources: SourceReference[];
  suggested_replies: string[];
  handoff: HandoffInfo;
  lead_capture_suggested: boolean;
}

export interface LeadCreateRequest {
  name: string;
  email: string;
  phone?: string;
  preferred_language?: "en" | "hi" | "gu";
  service_interest?: string;
  budget_range?: string;
  placement?: string;
  style_preference?: string;
  notes?: string;
  source?: string;
  consent: true;
}

export interface LeadResponse {
  id: string;
  name: string | null;
  email: string | null;
  phone: string | null;
  preferred_language: string | null;
  service_interest: string | null;
  status: string | null;
  source: string | null;
}

export interface AdminLeadResponse {
  id: string;
  name: string | null;
  email: string | null;
  phone: string | null;
  preferred_language: string | null;
  service_interest: string | null;
  budget_range: string | null;
  placement: string | null;
  style_preference: string | null;
  notes: string | null;
  conversation_context: string | null;
  status: string;
  source: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminLeadUpdateRequest {
  status?: string;
  notes?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ConversationListItem {
  id: string;
  session_id: string;
  language: string | null;
  status: string;
  summary: string | null;
  lead_id: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface MessageInConversation {
  id: string;
  role: string;
  content: string;
  intent: string | null;
  confidence: number | null;
  created_at: string;
}

export interface ConversationDetail {
  id: string;
  session_id: string;
  language: string | null;
  status: string;
  summary: string | null;
  lead_id: string | null;
  created_at: string;
  updated_at: string;
  messages: MessageInConversation[];
}

export interface KnowledgeDocument {
  id: string;
  title: string;
  source_type: string;
  source_url: string | null;
  language: string | null;
  content: string;
  status: string;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeDocumentCreate {
  title: string;
  source_type: string;
  language?: string;
  content: string;
  status?: string;
  source_url?: string;
  metadata_json?: Record<string, unknown>;
}

export interface KnowledgeDocumentUpdate {
  title?: string;
  source_type?: string;
  language?: string;
  content?: string;
  status?: string;
  source_url?: string;
  metadata_json?: Record<string, unknown>;
}

export interface ReindexResponse {
  message: string;
  document_id: string;
  chunk_count: number;
}

export interface KnowledgeChunkResponse {
  id: string;
  document_id: string;
  chunk_text: string;
  chunk_index: number;
  service_type: string;
  language: string | null;
  created_at: string;
}

export interface ServiceCount {
  service: string;
  count: number;
}

export interface LanguageCount {
  language: string;
  count: number;
}

export interface AnalyticsOverview {
  period: { start_date: string; end_date: string };
  total_conversations: number;
  total_messages: number;
  total_leads: number;
  lead_conversion_rate: number;
  handoff_rate: number;
  average_feedback_rating: number;
  popular_services: ServiceCount[];
  language_distribution: LanguageCount[];
}

export interface IntentStat {
  intent: string;
  count: number;
  percentage: number;
}

export interface PopularIntentsResponse {
  period: { start_date: string; end_date: string };
  intents: IntentStat[];
}

export interface FailedQueryItem {
  id: string;
  conversation_id: string | null;
  user_message: string;
  intent: string | null;
  confidence: number | null;
  handoff_triggered: boolean;
  handoff_reason: string | null;
  created_at: string;
}

export interface StudioHours {
  mon_sat: string;
  sun: string;
}

export interface StudioSettings {
  studio_name: string;
  studio_phone: string;
  studio_instagram: string;
  studio_address: string;
  studio_hours: StudioHours;
  default_language: string;
  supported_languages: string[];
  handoff_message_template: string;
  rag_similarity_threshold: number;
  rag_top_k: number;
  max_message_length: number;
  updated_at: string | null;
}

export interface StudioSettingsUpdate {
  studio_phone?: string;
  handoff_message_template?: string;
  rag_similarity_threshold?: number;
  rag_top_k?: number;
  max_message_length?: number;
}

export interface ListParams {
  page?: number;
  page_size?: number;
  status?: string;
  language?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}
