import {
  getAccessToken,
  getRefreshToken,
  removeTokens,
  setAccessToken,
  setRefreshToken,
} from "@/lib/auth";
import type {
  AdminLeadResponse,
  AdminLeadUpdateRequest,
  AnalyticsOverview,
  ChatMessageResponse,
  ChatStartResponse,
  ConversationDetail,
  ConversationListItem,
  FailedQueryItem,
  KnowledgeDocument,
  KnowledgeDocumentCreate,
  KnowledgeDocumentUpdate,
  LeadCreateRequest,
  LeadResponse,
  ListParams,
  PaginatedResponse,
  PopularIntentsResponse,
  ReindexResponse,
  StreamChunk,
  StreamDone,
  StudioSettings,
  StudioSettingsUpdate,
  TokenResponse,
  UserResponse,
} from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function apiPost<TRequest, TResponse>(
  path: string,
  body: TRequest
): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json() as Promise<TResponse>;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}/api/v1${path}`;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    const token = getAccessToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(url, { ...options, headers });

    if (response.status === 401 && token) {
      const refreshed = await this.tryRefresh();
      if (refreshed) {
        headers["Authorization"] = `Bearer ${getAccessToken()}`;
        const retry = await fetch(url, { ...options, headers });
        if (!retry.ok) {
          throw new ApiError(retry.status, await retry.text());
        }
        return retry.json() as Promise<T>;
      }
      removeTokens();
      if (typeof window !== "undefined") {
        window.location.href = "/admin/login";
      }
      throw new ApiError(401, "Session expired");
    }

    if (!response.ok) {
      throw new ApiError(response.status, await response.text());
    }

    return response.json() as Promise<T>;
  }

  private async tryRefresh(): Promise<boolean> {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return false;

    try {
      const response = await fetch(`${this.baseUrl}/api/v1/admin/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) return false;

      const data: TokenResponse = await response.json();
      setAccessToken(data.access_token);
      setRefreshToken(data.refresh_token);
      return true;
    } catch {
      return false;
    }
  }

  private buildQuery(params?: Record<string, string | number | boolean | undefined>): string {
    if (!params) return "";
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        searchParams.set(key, String(value));
      }
    }
    const str = searchParams.toString();
    return str ? `?${str}` : "";
  }

  async startChat(language: string = "en", channel: string = "web"): Promise<ChatStartResponse> {
    return this.request<ChatStartResponse>("/chat/start", {
      method: "POST",
      body: JSON.stringify({ language, channel }),
    });
  }

  async sendMessage(sessionId: string, message: string, language: string = "en"): Promise<ChatMessageResponse> {
    return this.request<ChatMessageResponse>("/chat/message", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, message, language }),
    });
  }

  async *streamMessage(
    sessionId: string,
    message: string,
    language: string = "en",
    signal?: AbortSignal
  ): AsyncGenerator<{ event: string; data: StreamChunk | StreamDone }> {
    const url = `${this.baseUrl}/api/v1/chat/message/stream`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message, language }),
      signal,
    });

    if (!response.ok) {
      throw new ApiError(response.status, await response.text());
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error("No response body");

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("event: ")) {
          continue;
        }
        if (line.startsWith("data: ")) {
          const raw = line.slice(6);
          try {
            const parsed = JSON.parse(raw);
            if (parsed.content !== undefined && !parsed.message_id) {
              yield { event: "chunk", data: parsed as StreamChunk };
            } else if (parsed.message_id) {
              yield { event: "done", data: parsed as StreamDone };
            }
          } catch {
            // skip malformed lines
          }
        }
      }
    }
  }

  async submitFeedback(messageId: string, rating: number, comment?: string, sessionId?: string): Promise<void> {
    await this.request("/chat/feedback", {
      method: "POST",
      body: JSON.stringify({ message_id: messageId, rating, comment, session_id: sessionId }),
    });
  }

  async submitLead(data: LeadCreateRequest): Promise<LeadResponse> {
    return this.request<LeadResponse>("/leads", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async adminLogin(email: string, password: string): Promise<TokenResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/admin/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) {
      throw new ApiError(response.status, await response.text());
    }
    const data: TokenResponse = await response.json();
    setAccessToken(data.access_token);
    setRefreshToken(data.refresh_token);
    return data;
  }

  async adminRefresh(refreshToken: string): Promise<TokenResponse> {
    return this.request<TokenResponse>("/admin/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  }

  async getMe(): Promise<UserResponse> {
    return this.request<UserResponse>("/admin/me");
  }

  async listKnowledge(params?: ListParams): Promise<KnowledgeDocument[]> {
    return this.request<KnowledgeDocument[]>(`/admin/knowledge${this.buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  }

  async createKnowledge(data: KnowledgeDocumentCreate): Promise<KnowledgeDocument> {
    return this.request<KnowledgeDocument>("/admin/knowledge", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getKnowledge(id: string): Promise<KnowledgeDocument> {
    return this.request<KnowledgeDocument>(`/admin/knowledge/${id}`);
  }

  async updateKnowledge(id: string, data: KnowledgeDocumentUpdate): Promise<KnowledgeDocument> {
    return this.request<KnowledgeDocument>(`/admin/knowledge/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async deleteKnowledge(id: string): Promise<void> {
    await this.request(`/admin/knowledge/${id}`, { method: "DELETE" });
  }

  async reindexKnowledge(id: string): Promise<ReindexResponse> {
    return this.request<ReindexResponse>(`/admin/knowledge/${id}/reindex`, {
      method: "POST",
    });
  }

  async listLeads(params?: ListParams): Promise<PaginatedResponse<AdminLeadResponse>> {
    return this.request<PaginatedResponse<AdminLeadResponse>>(`/admin/leads${this.buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  }

  async getLead(id: string): Promise<AdminLeadResponse> {
    return this.request<AdminLeadResponse>(`/admin/leads/${id}`);
  }

  async updateLead(id: string, data: AdminLeadUpdateRequest): Promise<AdminLeadResponse> {
    return this.request<AdminLeadResponse>(`/admin/leads/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async listChats(params?: ListParams): Promise<PaginatedResponse<ConversationListItem>> {
    return this.request<PaginatedResponse<ConversationListItem>>(`/admin/chats${this.buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  }

  async getChat(id: string): Promise<ConversationDetail> {
    return this.request<ConversationDetail>(`/admin/chats/${id}`);
  }

  async getAnalyticsOverview(startDate?: string, endDate?: string): Promise<AnalyticsOverview> {
    return this.request<AnalyticsOverview>(`/admin/analytics/overview${this.buildQuery({ start_date: startDate, end_date: endDate })}`);
  }

  async getPopularIntents(startDate?: string, endDate?: string, limit?: number): Promise<PopularIntentsResponse> {
    return this.request<PopularIntentsResponse>(`/admin/analytics/popular-intents${this.buildQuery({ start_date: startDate, end_date: endDate, limit })}`);
  }

  async getFailedQueries(
    startDate?: string,
    endDate?: string,
    page?: number,
    pageSize?: number
  ): Promise<PaginatedResponse<FailedQueryItem>> {
    return this.request<PaginatedResponse<FailedQueryItem>>(
      `/admin/analytics/failed-queries${this.buildQuery({ start_date: startDate, end_date: endDate, page, page_size: pageSize })}`
    );
  }

  async getSettings(): Promise<StudioSettings> {
    return this.request<StudioSettings>("/admin/settings");
  }

  async updateSettings(data: StudioSettingsUpdate): Promise<StudioSettings> {
    return this.request<StudioSettings>("/admin/settings", {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }
}

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

export { ApiError };
export const api = new ApiClient(API_BASE_URL);
