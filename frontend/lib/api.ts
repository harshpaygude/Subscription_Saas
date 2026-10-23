const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "/api";

export class ApiError extends Error {
  readonly status: number;
  readonly endpoint: string;

  constructor(message: string, status: number, endpoint: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.endpoint = endpoint;
  }
}

export class ApiNetworkError extends Error {
  readonly method: string;
  readonly url: string;

  constructor(method: string, url: string) {
    super(`Network request failed: ${method} ${redactUrl(url)}`);
    this.name = "ApiNetworkError";
    this.method = method;
    this.url = redactUrl(url);
  }
}

function redactUrl(value: string): string {
  try {
    const relative = value.startsWith("/");
    const url = new URL(value, relative ? "http://same-origin.invalid" : undefined);
    const origin = relative ? "<same-origin>" : url.origin;
    return `${origin}${url.pathname}${url.search ? "?<redacted>" : ""}`;
  } catch {
    return "<invalid-url>";
  }
}

function sanitizeDiagnosticValue(value: unknown): string {
  const text = typeof value === "string" ? value : String(value ?? "");
  return text
    .replace(/(authorization|cookie|token|secret|api[_ -]?key|password)\s*[:=]\s*[^,;\s]+/gi, "$1=[redacted]")
    .slice(0, 300);
}

function describeThrownValue(value: unknown): { name: string; message: string; type: string } {
  if (value instanceof Error) {
    return {
      name: value.name || "Error",
      message: sanitizeDiagnosticValue(value.message),
      type: "Error",
    };
  }
  return {
    name: "NonErrorThrownValue",
    message: sanitizeDiagnosticValue(value),
    type: typeof value,
  };
}


/* ========================= */
/* TYPES */
/* ========================= */

export interface User {
  id: number;
  email: string;
  organization_id: number;
  role: string;
  display_name: string | null;
  created_at: string;
}


export interface Organization {
  id: number;
  name: string;
  created_at: string;
}


export interface TokenResponse {
  access_token: string;
  token_type: string;
}


/* ========================= */
/* API REQUEST */
/* ========================= */

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {

  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("access_token")
      : null;


  const headers = new Headers(
    options.headers
  );


  headers.set(
    "Content-Type",
    "application/json"
  );


  if (token) {
    headers.set(
      "Authorization",
      `Bearer ${token}`
    );
  }


  const url =
    `${API_URL}${endpoint}`;


  let response: Response;


  try {

    response = await fetch(
      url,
      {
        ...options,
        credentials: "include",
        headers,
      }
    );

  } catch (error) {
    // Keep diagnostics useful without emitting auth headers, cookies, tokens,
    // provider credentials, or query-string values into the console.
    const thrown = describeThrownValue(error);
    const diagnostic = {
      phase: "before-http-response",
      method: options.method || "GET",
      url: redactUrl(url),
      errorName: thrown.name,
      errorMessage: thrown.message,
      thrownType: thrown.type,
    };
    console.error("API connection failed", JSON.stringify(diagnostic));
    throw new ApiNetworkError(options.method || "GET", url);
  }


  if (!response.ok) {

    let errorMessage =
      "API request failed";

    let responseDetail = "";

    try {

      const error =
        await response.json();

      responseDetail = sanitizeDiagnosticValue(error.detail || error.message || "");
      errorMessage =
        responseDetail ||
        errorMessage;

    } catch {
      // Response was not JSON.
    }

    console.error("API request returned an error", JSON.stringify({
      phase: "http-response",
      method: options.method || "GET",
      url: redactUrl(url),
      status: response.status,
      statusText: response.statusText,
      responseDetail: responseDetail || "<non-json-or-empty>",
    }));

    // Stop every dashboard request from retrying a session that the backend
    // no longer accepts (for example after JWT expiry or a secret rotation).
    // Keep login/register failures on their forms so their error is visible.
    if (response.status === 401 && typeof window !== "undefined" && !endpoint.startsWith("/auth/login") && !endpoint.startsWith("/auth/register")) {
      localStorage.removeItem("access_token");
      if (!window.location.pathname.startsWith("/login")) {
        window.location.replace("/login?reason=session-expired");
      }
    }

    throw new ApiError(errorMessage, response.status, endpoint);
  }

  return response.json();
}


/* ========================= */
/* REGISTER */
/* ========================= */

export async function register(
  email: string,
  password: string,
  organizationName: string
): Promise<User> {

  return apiRequest<User>(
    "/auth/register",
    {
      method: "POST",

      body: JSON.stringify({
        email,
        password,
        organization_name:
          organizationName,
      }),
    }
  );
}


/* ========================= */
/* LOGIN */
/* ========================= */

export async function login(
  email: string,
  password: string
): Promise<TokenResponse> {

  return apiRequest<TokenResponse>(
    "/auth/login",
    {
      method: "POST",

      body: JSON.stringify({
        email,
        password,
      }),
    }
  );
}


/* ========================= */
/* CURRENT USER */
/* ========================= */

export async function getCurrentUser():
  Promise<User> {

  return apiRequest<User>(
    "/auth/me"
  );
}

export async function updateProfile(data: { display_name: string }): Promise<User> {
  return apiRequest<User>("/auth/me", { method: "PATCH", body: JSON.stringify(data) });
}

export async function changePassword(data: { current_password: string; new_password: string; confirm_password: string }): Promise<{ message: string }> {
  return apiRequest<{ message: string }>("/auth/change-password", { method: "POST", body: JSON.stringify(data) });
}


/* ========================= */
/* ORGANIZATION */
/* ========================= */

export async function getOrganization(
  organizationId: number
): Promise<Organization> {

  return apiRequest<Organization>(
    `/organizations/${organizationId}`
  );
}



/* ========================= */
/* AWS INTEGRATION */
/* ========================= */

export interface AWSConnection {
  id: number;
  provider: string;
  account_id: string | null;
  status: string;
  region: string;
  created_at: string;
  updated_at: string;
}

export interface AWSConnectResponse {
  connection: AWSConnection;
  identity_arn: string;
  cost_access: boolean;
  message: string;
}

export interface AWSVerificationResponse {
  account_id: string;
  identity_arn: string;
  region: string;
  cost_access: boolean;
  status: string;
  message: string;
}

export interface AWSCostResponse {
  account_id: string;
  currency: string;
  amount: string;
  period_start: string;
  period_end_exclusive: string;
  granularity: string;
}

export async function listAWSConnections(): Promise<AWSConnection[]> {
  return apiRequest<AWSConnection[]>("/integrations/aws/connections");
}

export async function connectAWS(credentials: {
  access_key_id: string;
  secret_access_key: string;
  session_token?: string;
  region: string;
}): Promise<AWSConnectResponse> {
  return apiRequest<AWSConnectResponse>("/integrations/aws/connections", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

export async function verifyAWS(credentials: {
  access_key_id: string;
  secret_access_key: string;
  session_token?: string;
  region: string;
}): Promise<AWSVerificationResponse> {
  return apiRequest<AWSVerificationResponse>("/integrations/aws/verify", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

export async function disconnectAWS(connectionId: number): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(`/integrations/aws/connections/${connectionId}`, {
    method: "DELETE",
  });
}

export async function getAWSCosts(connectionId: number): Promise<AWSCostResponse> {
  return apiRequest<AWSCostResponse>(`/integrations/aws/connections/${connectionId}/costs`);
}

/* ========================= */
/* LOGOUT */
/* ========================= */

export function logout() {
  localStorage.removeItem("access_token");
  window.location.replace("/login");
}


export interface AWSAccountPlanResponse {
  account_id: string;
  plan_type: string;
  plan_status: string;
  credits_remaining: number | null;
  currency: string;
  expiration_date: string | null;
  days_remaining: number | null;
  original_amount: number | null;
  retrieved_at: string;
  data_status: "AVAILABLE" | "UNAVAILABLE" | "STALE";
}

export async function getAWSAccountPlan(connectionId: number): Promise<AWSAccountPlanResponse> {
  return apiRequest<AWSAccountPlanResponse>(`/integrations/aws/connections/${connectionId}/account-plan`);
}

/* OPENAI INTEGRATION */

export interface OpenAIConnection {
  id: number;
  provider: string;
  status: string;
  created_at: string;
  updated_at: string;
  last_verified_at: string | null;
}

export interface OpenAIConnectResponse {
  connection: OpenAIConnection;
  model_count: number;
  message: string;
}

export interface OpenAITestResponse {
  connection_id: number;
  status: string;
  model_count: number;
  last_verified_at: string;
  message: string;
}

export async function listOpenAIConnections(): Promise<OpenAIConnection[]> {
  return apiRequest<OpenAIConnection[]>("/integrations/openai/connections");
}

export async function connectOpenAI(apiKey: string): Promise<OpenAIConnectResponse> {
  return apiRequest<OpenAIConnectResponse>("/integrations/openai/connections", {
    method: "POST",
    body: JSON.stringify({ api_key: apiKey }),
  });
}

export async function testOpenAIConnection(connectionId: number): Promise<OpenAITestResponse> {
  return apiRequest<OpenAITestResponse>(`/integrations/openai/connections/${connectionId}/test`, {
    method: "POST",
  });
}

export async function disconnectOpenAI(connectionId: number): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(`/integrations/openai/connections/${connectionId}`, {
    method: "DELETE",
  });
}

export interface OpenAIUsageDay {
  start_time: number;
  end_time: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  requests: number | null;
}

export interface OpenAIModelUsage {
  model: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  requests: number | null;
}

export interface OpenAIUsageResponse {
  start_time: number;
  end_time: number;
  daily: OpenAIUsageDay[];
  by_model: OpenAIModelUsage[];
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  requests: number | null;
  synced_at: string;
}

export interface OpenAICostDay {
  start_time: number;
  end_time: number;
  amount: number;
  currency: string;
}

export interface OpenAIProjectCost {
  project_id: string;
  amount: number;
  currency: string;
}

export interface OpenAICostResponse {
  start_time: number;
  end_time: number;
  daily: OpenAICostDay[];
  by_project: OpenAIProjectCost[];
  total: number;
  currency: string;
  synced_at: string;
}

export interface OpenAISummaryResponse {
  usage: OpenAIUsageResponse;
  costs: OpenAICostResponse | null;
  costs_error: string | null;
}

export async function getOpenAISummary(startDate: string, endDate: string): Promise<OpenAISummaryResponse> {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
  return apiRequest<OpenAISummaryResponse>(`/integrations/openai/summary?${params.toString()}`);
}

export interface GeminiConnection { id: number; provider: string; status: string; created_at: string; updated_at: string; last_verified_at: string | null; }
export interface GeminiConnectResponse { connection: GeminiConnection; model_count: number; message: string; }
export interface GeminiTestResponse { connection_id: number; status: string; model_count: number; last_verified_at: string; message: string; }
export async function listGeminiConnections(): Promise<GeminiConnection[]> { return apiRequest<GeminiConnection[]>("/integrations/gemini/connections"); }
export async function connectGemini(apiKey: string): Promise<GeminiConnectResponse> { return apiRequest<GeminiConnectResponse>("/integrations/gemini/connections", { method: "POST", body: JSON.stringify({ api_key: apiKey }) }); }
export async function testGeminiConnection(connectionId: number): Promise<GeminiTestResponse> { return apiRequest<GeminiTestResponse>(`/integrations/gemini/connections/${connectionId}/test`, { method: "POST" }); }
export async function disconnectGemini(connectionId: number): Promise<{ message: string }> { return apiRequest<{ message: string }>(`/integrations/gemini/connections/${connectionId}`, { method: "DELETE" }); }
export interface GeminiUsageResponse { start_date: string; end_date: string; requests: number; input_tokens: number; output_tokens: number; total_tokens: number; by_model: Array<{ model: string; requests: number; input_tokens: number; output_tokens: number; total_tokens: number }>; daily: Array<{ date: string; requests: number; input_tokens: number; output_tokens: number; total_tokens: number }>; }
export async function getGeminiUsage(startDate: string, endDate: string): Promise<GeminiUsageResponse> { const params = new URLSearchParams({ start_date: startDate, end_date: endDate }); return apiRequest<GeminiUsageResponse>(`/integrations/gemini/usage?${params.toString()}`); }
export async function generateGemini(model: string, prompt: string): Promise<{ candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }>; usageMetadata?: { totalTokenCount?: number } }> { return apiRequest(`/integrations/gemini/generate`, { method: "POST", body: JSON.stringify({ model, contents: [{ role: "user", parts: [{ text: prompt }] }] }) }); }

export interface AzureConnection { id: number; provider: string; connected: boolean; status: string; created_at: string | null; updated_at: string | null; last_successful_refresh?: string | null; }
export async function getAzureConnection(): Promise<AzureConnection> { return apiRequest<AzureConnection>("/integrations/azure/connection"); }
export async function connectAzureServicePrincipal(credentials: { tenant_id: string; client_id: string; client_secret: string; subscription_id?: string }): Promise<AzureConnection> { return apiRequest<AzureConnection>("/integrations/azure/connection/service-principal", { method: "POST", body: JSON.stringify(credentials) }); }
export async function discoverAzureSubscriptions(): Promise<{ status: string; subscriptions: Array<{ id: string; display_name: string; state?: string; tenant_id?: string; selected?: boolean }> }> { return apiRequest("/integrations/azure/subscriptions/discover", { method: "POST" }); }
export async function selectAzureSubscriptions(subscription_ids: string[]): Promise<{ status: string }> { return apiRequest("/integrations/azure/subscriptions", { method: "POST", body: JSON.stringify({ subscription_ids }) }); }
export async function getAzureCost(subscriptionId: string, start: string, end: string): Promise<unknown> { return apiRequest(`/integrations/azure/subscriptions/${encodeURIComponent(subscriptionId)}/cost?start=${start}&end=${end}`); }
export async function disconnectAzure(): Promise<{ status: string }> { return apiRequest("/integrations/azure/connection", { method: "DELETE" }); }
export async function startAzureOAuth(): Promise<{ authorization_url: string }> { return apiRequest<{ authorization_url: string }>("/integrations/azure/oauth/start"); }
export async function testAzureConnection(): Promise<{ status: string; last_successful_refresh: string; message: string }> { return apiRequest("/integrations/azure/connection/test", { method: "POST" }); }

export interface AnthropicConnection {
  id: number;
  provider: string;
  status: string;
  model: string;
  connection_name: string | null;
  created_at: string;
  updated_at: string;
  last_verified_at: string | null;
}
export interface AnthropicConnectResponse { connection: AnthropicConnection; message: string; }
export interface AnthropicTestResponse { connection_id: number; status: string; model: string; last_verified_at: string; message: string; }
export async function listAnthropicConnections(): Promise<AnthropicConnection[]> { return apiRequest<AnthropicConnection[]>("/integrations/anthropic/connections"); }
export async function connectAnthropic(apiKey: string, model: string, connectionName?: string): Promise<AnthropicConnectResponse> {
  return apiRequest<AnthropicConnectResponse>("/integrations/anthropic/connections", { method: "POST", body: JSON.stringify({ api_key: apiKey, model, ...(connectionName?.trim() ? { connection_name: connectionName.trim() } : {}) }) });
}
export async function testAnthropicConnection(connectionId: number): Promise<AnthropicTestResponse> { return apiRequest<AnthropicTestResponse>(`/integrations/anthropic/connections/${connectionId}/test`, { method: "POST" }); }
export async function disconnectAnthropic(connectionId: number): Promise<{ message: string }> { return apiRequest<{ message: string }>(`/integrations/anthropic/connections/${connectionId}`, { method: "DELETE" }); }

export interface SubscriptionRecord { id: number; organization_id: number; provider: string; name: string; plan: string | null; amount: string | null; currency: string; billing_interval: string; start_date: string | null; next_renewal_date: string | null; status: string; cancellation_date: string | null; source: string; note: string | null; created_at: string; updated_at: string; }
export interface SpendRow { service: string; name: string; monthly_spend: string; currency: string; billing_source: string; billing_period: string; last_updated: string; status: string; }
export interface MonthlySpendResponse { totals_by_currency: Record<string, string>; services: SpendRow[]; }
export async function listSubscriptions(params: { provider?: string; status?: string } = {}): Promise<SubscriptionRecord[]> { const query = new URLSearchParams(); Object.entries(params).forEach(([key, value]) => value && query.set(key, value)); return apiRequest<SubscriptionRecord[]>(`/subscriptions${query.size ? `?${query.toString()}` : ""}`); }
export async function createSubscription(payload: Omit<SubscriptionRecord, "id" | "organization_id" | "status" | "cancellation_date" | "source" | "created_at" | "updated_at"> & { status?: string }): Promise<SubscriptionRecord> { return apiRequest<SubscriptionRecord>("/subscriptions", { method: "POST", body: JSON.stringify(payload) }); }
export async function cancelSubscription(id: number): Promise<SubscriptionRecord> { return apiRequest<SubscriptionRecord>(`/subscriptions/${id}/cancel`, { method: "POST" }); }
export async function deleteSubscription(id: number): Promise<void> { await apiRequest<unknown>(`/subscriptions/${id}`, { method: "DELETE" }); }
export async function getMonthlySpend(): Promise<MonthlySpendResponse> { return apiRequest<MonthlySpendResponse>("/subscriptions/spend"); }
export async function createManualSpend(payload: { provider: string; amount: string; currency: string; billing_interval: string; period_start: string; period_end?: string; note?: string }): Promise<SpendRow> { return apiRequest<SpendRow>("/subscriptions/manual-spend", { method: "POST", body: JSON.stringify(payload) }); }
export interface AnalyticsSummary { active_subscriptions: number; cancelled_subscriptions: number; upcoming_renewals: number; totals_by_currency: Record<string, string>; by_provider: Record<string, { currency: string; monthly_spend: string; data_status: string }>; historical: Array<{ month: string; totals_by_currency: Record<string, string> }>; historical_note: string; }
export async function getAnalyticsSummary(): Promise<AnalyticsSummary> { return apiRequest<AnalyticsSummary>("/analytics/summary"); }
export interface AlertRecord { id: number; organization_id: number; provider: string | null; subscription_id: number | null; category: string; severity: string; title: string; description: string; is_read: boolean; is_resolved: boolean; created_at: string; updated_at: string; }
export async function listAlerts(params: { read?: boolean; resolved?: boolean } = {}): Promise<AlertRecord[]> { const query = new URLSearchParams(); if (params.read !== undefined) query.set("read", String(params.read)); if (params.resolved !== undefined) query.set("resolved", String(params.resolved)); return apiRequest<AlertRecord[]>(`/alerts${query.size ? `?${query.toString()}` : ""}`); }
export async function markAlertRead(id: number): Promise<AlertRecord> { return apiRequest<AlertRecord>(`/alerts/${id}/read`, { method: "POST" }); }
export async function resolveAlert(id: number): Promise<AlertRecord> { return apiRequest<AlertRecord>(`/alerts/${id}/resolve`, { method: "POST" }); }
