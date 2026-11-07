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
  legal_name?: string | null;
  display_name?: string | null;
  industry?: string | null;
  company_size?: string | null;
  website?: string | null;
  company_email?: string | null;
  company_phone?: string | null;
  country?: string | null;
  state?: string | null;
  city?: string | null;
  address?: string | null;
  postal_code?: string | null;
  tax_registration_number?: string | null;
  onboarding_completed?: boolean;
  onboarding_completed_at?: string | null;
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
        cache: options.cache ?? "no-store",
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
  admin_access_status: "NOT_CONFIGURED" | "CONFIGURED" | "VERIFIED";
  admin_verified_at: string | null;
  last_reporting_sync_at: string | null;
  manual_balance_amount: string | null;
  manual_balance_currency: string | null;
  manual_balance_entered_at: string | null;
}
export interface AnthropicConnectResponse { connection: AnthropicConnection; message: string; }
export interface AnthropicTestResponse { connection_id: number; status: string; model: string; last_verified_at: string; message: string; }
export interface AnthropicReportResponse {
  connection_id: number;
  admin_access_status: string;
  usage_status: string;
  cost_status: string;
  start_date: string;
  end_date: string;
  usage: { totals: Record<string, number>; by_model: Array<Record<string, string | number>>; rows: Array<Record<string, string | number | null>>; data_refreshed_at: string | null } | null;
  cost: { total: string; list_total: string; currency: string; by_cost_type: Array<{ cost_type: string; amount: string; currency: string }>; rows: Array<Record<string, string | number | null>>; data_refreshed_at: string | null } | null;
  data_refreshed_at: string | null;
  last_synced_at: string | null;
  balance: { status: "UNSUPPORTED" | "MANUAL"; amount: string | null; currency: string | null; entered_at: string | null; source: string; console_url: string; message: string };
}
export interface AnthropicAdminCredentialResponse { connection_id: number; admin_access_status: string; admin_verified_at: string; message: string; }
export async function listAnthropicConnections(): Promise<AnthropicConnection[]> { return apiRequest<AnthropicConnection[]>("/integrations/anthropic/connections"); }
export async function connectAnthropic(apiKey: string, model: string, connectionName?: string): Promise<AnthropicConnectResponse> {
  return apiRequest<AnthropicConnectResponse>("/integrations/anthropic/connections", { method: "POST", body: JSON.stringify({ api_key: apiKey, model, ...(connectionName?.trim() ? { connection_name: connectionName.trim() } : {}) }) });
}
export async function testAnthropicConnection(connectionId: number): Promise<AnthropicTestResponse> { return apiRequest<AnthropicTestResponse>(`/integrations/anthropic/connections/${connectionId}/test`, { method: "POST" }); }
export async function disconnectAnthropic(connectionId: number): Promise<{ message: string }> { return apiRequest<{ message: string }>(`/integrations/anthropic/connections/${connectionId}`, { method: "DELETE" }); }
export async function configureAnthropicAdminCredential(connectionId: number, adminApiKey: string): Promise<AnthropicAdminCredentialResponse> { return apiRequest<AnthropicAdminCredentialResponse>(`/integrations/anthropic/connections/${connectionId}/admin-credential`, { method: "POST", body: JSON.stringify({ admin_api_key: adminApiKey }) }); }
export async function removeAnthropicAdminCredential(connectionId: number): Promise<{ message: string }> { return apiRequest<{ message: string }>(`/integrations/anthropic/connections/${connectionId}/admin-credential`, { method: "DELETE" }); }
export async function getAnthropicReports(connectionId: number, startDate: string, endDate: string, forceRefresh = false): Promise<AnthropicReportResponse> { const params = new URLSearchParams({ start_date: startDate, end_date: endDate, force_refresh: String(forceRefresh) }); return apiRequest<AnthropicReportResponse>(`/integrations/anthropic/connections/${connectionId}/reports?${params.toString()}`); }
export async function saveAnthropicManualBalance(connectionId: number, amount: string, currency: string): Promise<{ connection_id: number; balance: AnthropicReportResponse["balance"] }> { return apiRequest(`/integrations/anthropic/connections/${connectionId}/balance`, { method: "POST", body: JSON.stringify({ amount, currency }) }); }
export async function removeAnthropicManualBalance(connectionId: number): Promise<{ message: string }> { return apiRequest<{ message: string }>(`/integrations/anthropic/connections/${connectionId}/balance`, { method: "DELETE" }); }

export interface SubscriptionRecord { id: number; organization_id: number; provider: string; name: string; plan: string | null; amount: string | null; currency: string; billing_interval: string; renewal_type: string | null; start_date: string | null; next_renewal_date: string | null; status: string; cancellation_date: string | null; source: string; note: string | null; created_at: string; updated_at: string; }
export interface SpendRow { service: string; name: string; monthly_spend: string; currency: string; billing_source: string; billing_period: string; last_updated: string; status: string; }
export interface MonthlySpendResponse { totals_by_currency: Record<string, string>; services: SpendRow[]; }
export async function listSubscriptions(params: { provider?: string; status?: string } = {}): Promise<SubscriptionRecord[]> { const query = new URLSearchParams(); Object.entries(params).forEach(([key, value]) => value && query.set(key, value)); return apiRequest<SubscriptionRecord[]>(`/subscriptions${query.size ? `?${query.toString()}` : ""}`); }
export async function createSubscription(payload: Omit<SubscriptionRecord, "id" | "organization_id" | "status" | "cancellation_date" | "source" | "created_at" | "updated_at" | "renewal_type"> & { status?: string; renewal_type?: string | null }): Promise<SubscriptionRecord> { return apiRequest<SubscriptionRecord>("/subscriptions", { method: "POST", body: JSON.stringify(payload) }); }
export async function importSubscriptionsCSV(file: File): Promise<{ success: boolean; imported: number; updated: number; total_processed: number; errors: string[] }> {
  const formData = new FormData();
  formData.append("file", file);
  return apiRequest("/subscriptions/import-csv", { method: "POST", body: formData });
}
export async function seedDemoSubscriptions(): Promise<{ message: string; imported: number; updated: number; total_processed: number; errors: string[] }> {
  return apiRequest("/subscriptions/seed-demo", { method: "POST" });
}
export interface SubscriptionLicenseRecord { id: number; organization_id: number; subscription_id: number; reference: string | null; capacity: number; status: string; created_at: string; updated_at: string; }
export interface SubscriptionAssignmentRecord { id: number; organization_id: number; subscription_id: number; license_id: number | null; user_id: number; assigned_by: number; assigned_at: string; released_at: string | null; status: string; notes: string | null; }
export async function createSubscriptionLicense(subscriptionId: number, payload: { reference?: string; capacity: number }): Promise<SubscriptionLicenseRecord> { return apiRequest<SubscriptionLicenseRecord>(`/subscriptions/${subscriptionId}/licenses`, { method: "POST", body: JSON.stringify(payload) }); }
export async function listSubscriptionLicenses(subscriptionId: number): Promise<SubscriptionLicenseRecord[]> { return apiRequest<SubscriptionLicenseRecord[]>(`/subscriptions/${subscriptionId}/licenses`); }
export async function listSubscriptionAssignments(params: { subscription_id?: number; user_id?: number } = {}): Promise<SubscriptionAssignmentRecord[]> { const query = new URLSearchParams(); Object.entries(params).forEach(([key, value]) => value !== undefined && query.set(key, String(value))); return apiRequest<SubscriptionAssignmentRecord[]>(`/subscription-assignments${query.size ? `?${query.toString()}` : ""}`); }
export async function assignSubscription(payload: { subscription_id: number; license_id: number; user_id: number; notes?: string }): Promise<SubscriptionAssignmentRecord> { return apiRequest<SubscriptionAssignmentRecord>("/subscription-assignments", { method: "POST", body: JSON.stringify(payload) }); }
export async function releaseSubscriptionAssignment(id: number): Promise<SubscriptionAssignmentRecord> { return apiRequest<SubscriptionAssignmentRecord>(`/subscription-assignments/${id}/release`, { method: "POST" }); }
export async function cancelSubscription(id: number): Promise<SubscriptionRecord> { return apiRequest<SubscriptionRecord>(`/subscriptions/${id}/cancel`, { method: "POST" }); }
export async function deleteSubscription(id: number): Promise<void> { await apiRequest<unknown>(`/subscriptions/${id}`, { method: "DELETE" }); }
export async function getMonthlySpend(): Promise<MonthlySpendResponse> { return apiRequest<MonthlySpendResponse>("/subscriptions/spend"); }
export async function createManualSpend(payload: { provider: string; amount: string; currency: string; billing_interval: string; period_start: string; period_end?: string; note?: string }): Promise<SpendRow> { return apiRequest<SpendRow>("/subscriptions/manual-spend", { method: "POST", body: JSON.stringify(payload) }); }
export interface AnalyticsSummary { active_subscriptions: number; cancelled_subscriptions: number; upcoming_renewals: number; totals_by_currency: Record<string, string>; by_provider: Record<string, { currency: string; monthly_spend: string; data_status: string }>; departments?: number; assets?: { total: number; assigned: number; available: number }; license_utilization?: number; historical: Array<{ month: string; totals_by_currency: Record<string, string> }>; historical_note: string; }
export async function getAnalyticsSummary(): Promise<AnalyticsSummary> { return apiRequest<AnalyticsSummary>("/analytics/summary"); }

export interface AuditLogItem {
  id: number;
  created_at: string;
  actor_email?: string;
  action: string;
  entity_type: string;
  entity_id: number;
  details?: string | Record<string, unknown> | null;
}

export interface AuditExportResponse {
  organization_id?: number;
  organization_name?: string;
  generated_at: string;
  range_type: string;
  start_date: string;
  end_date: string;
  summary: {
    active_subscriptions: number;
    cancelled_subscriptions: number;
    upcoming_renewals: number;
    totals_by_currency: Record<string, string>;
  };
  by_provider: Record<string, { currency: string; monthly_spend: string; data_status: string }>;
  subscriptions?: Array<{
    id: number;
    provider: string;
    currency: string;
    amount: string;
    billing_interval: string;
    status: string;
    renewal_date?: string | null;
  }>;
  audit_logs: AuditLogItem[];
}

export async function getAuditExport(params: {
  range_type: "1year" | "6months" | "monthly" | "custom";
  start_date?: string;
  end_date?: string;
}): Promise<AuditExportResponse> {
  const query = new URLSearchParams();
  query.set("range_type", params.range_type);
  if (params.start_date) query.set("start_date", params.start_date);
  if (params.end_date) query.set("end_date", params.end_date);
  return apiRequest<AuditExportResponse>(`/analytics/audit-export?${query.toString()}`);
}
export interface DepartmentRecord { id: number; organization_id: number; name: string; description: string | null; is_active: boolean; created_at: string; updated_at: string; }
export interface MembershipRecord { id: number; organization_id: number; department_id: number; user_id: number; is_active: boolean; effective_from: string; effective_to: string | null; created_at: string; email: string | null; display_name: string | null; }
export interface EmployeeRecord { id: number; email: string; display_name: string | null; employee_id: string | null; phone_number: string | null; role: string; department_ids: number[]; active_subscription_assignments: number; active_asset_assignments: number; }
export async function listEmployees(): Promise<EmployeeRecord[]> { return apiRequest<EmployeeRecord[]>("/employees"); }
export async function createEmployee(payload: { employee_id: string; name: string; email: string; phone_number?: string; department_id: number; joined_at: string; asset_ids: number[] }): Promise<EmployeeRecord> { return apiRequest<EmployeeRecord>("/employees", { method: "POST", body: JSON.stringify(payload) }); }
export async function updateEmployee(
  id: number,
  payload: {
    name?: string;
    email?: string;
    employee_id?: string;
    phone_number?: string;
    role?: string;
    department_id?: number;
    subscription_ids?: number[];
    asset_ids?: number[];
  }
): Promise<EmployeeRecord> {
  return apiRequest<EmployeeRecord>(`/employees/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}


export interface BulkImportResult {
  success: boolean;
  message: string;
  created_employees: number;
  updated_employees: number;
  created_assets: number;
  assigned_assets: number;
  assigned_subscriptions: number;
  total_processed: number;
}

export async function importEmployeesCSV(file: File): Promise<BulkImportResult> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const formData = new FormData();
  formData.append("file", file);

  const url = `${API_URL}/employees/import-csv`;
  const headers = new Headers();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(url, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail || `Import failed with status ${response.status}`);
  }

  return response.json();
}
export async function listDepartments(): Promise<DepartmentRecord[]> { return apiRequest<DepartmentRecord[]>("/departments"); }
export async function createDepartment(payload: { name: string; description?: string }): Promise<DepartmentRecord> { return apiRequest<DepartmentRecord>("/departments", { method: "POST", body: JSON.stringify(payload) }); }
export async function updateDepartment(id: number, payload: Partial<{ name: string; description: string; is_active: boolean }>): Promise<DepartmentRecord> { return apiRequest<DepartmentRecord>(`/departments/${id}`, { method: "PATCH", body: JSON.stringify(payload) }); }
export async function listDepartmentMembers(id: number): Promise<MembershipRecord[]> { return apiRequest<MembershipRecord[]>(`/departments/${id}/members`); }
export async function addDepartmentMember(id: number, user_id: number): Promise<MembershipRecord> { return apiRequest<MembershipRecord>(`/departments/${id}/members`, { method: "POST", body: JSON.stringify({ user_id }) }); }
export interface AssetRecord { id: number; organization_id: number; asset_tag: string; asset_type: string; name: string; manufacturer: string | null; model: string | null; serial_number: string | null; purchase_date: string | null; purchase_cost: string | null; currency: string; warranty_expiry: string | null; location: string | null; status: string; created_at: string; updated_at: string; }
export interface AssetAssignmentRecord { id: number; organization_id: number; asset_id: number; user_id: number; assigned_by: number; assigned_at: string; expected_return_at: string | null; returned_at: string | null; returned_by: number | null; condition_at_issue: string | null; condition_at_return: string | null; handover_notes: string | null; status: string; user_name?: string | null; user_email?: string | null; user_employee_id?: string | null; }
export interface AssetBulkImportResult {
  success: boolean;
  message: string;
  created_assets: number;
  updated_assets: number;
  assigned_assets: number;
  employees_matched: number;
  total_processed: number;
  warnings?: string[];
}

export async function importAssetsCSV(file: File): Promise<AssetBulkImportResult> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const formData = new FormData();
  formData.append("file", file);

  const url = `${API_URL}/assets/import-csv`;
  const headers = new Headers();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(url, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail || `Import failed with status ${response.status}`);
  }

  return response.json();
}

export async function listAssets(params: { status?: string; asset_type?: string } = {}): Promise<AssetRecord[]> { const query = new URLSearchParams(); Object.entries(params).forEach(([key, value]) => value && query.set(key, value)); return apiRequest<AssetRecord[]>(`/assets${query.size ? `?${query}` : ""}`); }
export async function createAsset(payload: { asset_tag: string; asset_type: string; name: string; manufacturer?: string; model?: string; serial_number?: string; purchase_date?: string; purchase_cost?: string; currency?: string; warranty_expiry?: string; location?: string }): Promise<AssetRecord> { return apiRequest<AssetRecord>("/assets", { method: "POST", body: JSON.stringify(payload) }); }
export async function assignAsset(id: number, payload: { user_id: number; expected_return_at?: string; condition_at_issue?: string; handover_notes?: string }): Promise<AssetAssignmentRecord> { return apiRequest<AssetAssignmentRecord>(`/assets/${id}/assignments`, { method: "POST", body: JSON.stringify(payload) }); }
export async function listAssetAssignments(id: number): Promise<AssetAssignmentRecord[]> { return apiRequest<AssetAssignmentRecord[]>(`/assets/${id}/assignments`); }
export async function returnAsset(id: number, payload: { condition_at_return?: string; handover_notes?: string } = {}): Promise<AssetAssignmentRecord> { return apiRequest<AssetAssignmentRecord>(`/assets/assignments/${id}/return`, { method: "POST", body: JSON.stringify(payload) }); }
export interface LifecycleTaskRecord { id: number; lifecycle_id: number; task_type: string; title: string; status: string; action_status: string; required: boolean; assignee_id: number | null; related_subscription_id: number | null; related_subscription_assignment_id: number | null; related_asset_id: number | null; related_asset_assignment_id: number | null; due_at: string | null; completed_at: string | null; completed_by: number | null; completion_note: string | null; created_at: string; updated_at: string; }
export interface LifecycleResourceRecord { id: number; resource_id: number; status: string; assigned_at: string; released_at: string | null; resource_name?: string | null; resource_provider?: string | null; }
export interface LifecycleEmployeeRecord { id: number; user_id: number; email: string; display_name: string | null; employee_id: string | null; phone_number: string | null; role: string; status: string; joined_at: string; last_working_date: string | null; department_ids: number[]; department_names: string[]; subscription_assignments: LifecycleResourceRecord[]; asset_assignments: LifecycleResourceRecord[]; tasks: LifecycleTaskRecord[]; open_task_count: number; completed_task_count: number; }
export interface LifecycleDashboardRecord { new_joiners: LifecycleEmployeeRecord[]; working: LifecycleEmployeeRecord[]; offboarding: LifecycleEmployeeRecord[]; completed: LifecycleEmployeeRecord[]; pending_tasks: LifecycleTaskRecord[]; }
export async function getLifecycleDashboard(): Promise<LifecycleDashboardRecord> { return apiRequest<LifecycleDashboardRecord>("/employee-lifecycle/dashboard"); }
export async function getEmployeeLifecycle(userId: number): Promise<LifecycleEmployeeRecord> { return apiRequest<LifecycleEmployeeRecord>(`/employees/${userId}/lifecycle`); }
export async function startEmployeeOnboarding(userId: number, payload: { department_id: number; joined_at: string; tasks?: Array<{ task_type: string; title: string; subscription_id?: number; asset_id?: number; due_at?: string; required?: boolean }> }): Promise<LifecycleEmployeeRecord> { return apiRequest<LifecycleEmployeeRecord>(`/employees/${userId}/onboarding`, { method: "POST", body: JSON.stringify(payload) }); }
export async function startEmployeeOffboarding(userId: number, last_working_date: string): Promise<LifecycleEmployeeRecord> { return apiRequest<LifecycleEmployeeRecord>(`/employees/${userId}/offboarding`, { method: "POST", body: JSON.stringify({ last_working_date }) }); }
export async function completeLifecycleTask(taskId: number, completion_note?: string): Promise<LifecycleTaskRecord> { return apiRequest<LifecycleTaskRecord>(`/lifecycle-tasks/${taskId}/complete`, { method: "POST", body: JSON.stringify({ completion_note }) }); }
export interface AlertRecord { id: number; organization_id: number; provider: string | null; subscription_id: number | null; category: string; severity: string; title: string; description: string; is_read: boolean; is_resolved: boolean; created_at: string; updated_at: string; }
export async function listAlerts(params: { read?: boolean; resolved?: boolean } = {}): Promise<AlertRecord[]> { const query = new URLSearchParams(); if (params.read !== undefined) query.set("read", String(params.read)); if (params.resolved !== undefined) query.set("resolved", String(params.resolved)); return apiRequest<AlertRecord[]>(`/alerts${query.size ? `?${query.toString()}` : ""}`); }
export async function markAlertRead(id: number): Promise<AlertRecord> { return apiRequest<AlertRecord>(`/alerts/${id}/read`, { method: "POST" }); }
export async function resolveAlert(id: number): Promise<AlertRecord> { return apiRequest<AlertRecord>(`/alerts/${id}/resolve`, { method: "POST" }); }

/* ========================= */
/* ONBOARDING & COMPANY PROFILE */
/* ========================= */

export interface OnboardingStatus {
  onboarding_completed: boolean;
  onboarding_completed_at: string | null;
}

export interface DepartmentInput {
  name: string;
  description?: string;
}

export interface CompanyProfile {
  legal_name?: string;
  display_name?: string;
  industry?: string;
  company_size?: string;
  website?: string;
  company_email?: string;
  company_phone?: string;
  country?: string;
  state?: string;
  city?: string;
  address?: string;
  postal_code?: string;
  tax_registration_number?: string;
}

export interface ExcelAssetItem {
  asset_tag: string;
  name: string;
  asset_type?: string;
  manufacturer?: string | null;
  model?: string | null;
  serial_number?: string | null;
  purchase_cost?: string | null;
  currency?: string;
  location?: string | null;
  assigned_to?: string | null;
}

export interface ExcelEmployeeItem {
  employee_id: string;
  full_name: string;
  email: string;
  phone_number?: string | null;
  department_name?: string | null;
  joining_date?: string | null;
}

export interface OnboardingPayload {
  company: CompanyProfile;
  departments: DepartmentInput[];
  employees?: ExcelEmployeeItem[];
  assets?: ExcelAssetItem[];
}

export interface ExcelImportResult {
  valid: boolean;
  company: {
    company_name?: string | null;
    legal_name?: string | null;
    industry?: string | null;
    company_size?: string | null;
    website?: string | null;
    company_email?: string | null;
    company_phone?: string | null;
    country?: string | null;
    state?: string | null;
    city?: string | null;
    address?: string | null;
    postal_code?: string | null;
    tax_registration_number?: string | null;
  } | null;
  departments: DepartmentInput[];
  employees: ExcelEmployeeItem[];
  assets: ExcelAssetItem[];
  errors: string[];
  warnings: string[];
  department_count: number;
  employee_count: number;
  asset_count: number;
}

export async function getOnboardingStatus(): Promise<OnboardingStatus> {
  return apiRequest<OnboardingStatus>("/organizations/me/onboarding-status");
}

export async function updateOrganizationProfile(payload: CompanyProfile): Promise<Organization> {
  return apiRequest<Organization>("/organizations/me/profile", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function submitOnboarding(payload: OnboardingPayload): Promise<Organization> {
  return apiRequest<Organization>("/organizations/me/onboarding", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function parseOnboardingExcel(file: File): Promise<ExcelImportResult> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const formData = new FormData();
  formData.append("file", file);

  const url = `${API_URL}/organizations/me/onboarding/parse-excel`;
  const headers = new Headers();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers,
      body: formData,
      credentials: "include",
    });
  } catch {
    throw new ApiNetworkError("POST", url);
  }

  if (!response.ok) {
    let msg = "Failed to parse Excel file";
    try {
      const err = await response.json();
      if (err.detail) msg = err.detail;
    } catch {}
    throw new ApiError(msg, response.status, "/organizations/me/onboarding/parse-excel");
  }

  return response.json();
}

