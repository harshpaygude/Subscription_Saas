import { apiRequest } from "./httpClient";

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
  return apiRequest<{ message: string }>(`/integrations/aws/connections/${connectionId}`, { method: "DELETE" });
}

export async function getAWSCosts(connectionId: number): Promise<AWSCostResponse> {
  return apiRequest<AWSCostResponse>(`/integrations/aws/connections/${connectionId}/costs`);
}

export async function getAWSAccountPlan(connectionId: number): Promise<AWSAccountPlanResponse> {
  return apiRequest<AWSAccountPlanResponse>(`/integrations/aws/connections/${connectionId}/account-plan`);
}

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
  return apiRequest<OpenAITestResponse>(`/integrations/openai/connections/${connectionId}/test`, { method: "POST" });
}

export async function disconnectOpenAI(connectionId: number): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(`/integrations/openai/connections/${connectionId}`, { method: "DELETE" });
}

export async function getOpenAISummary(startDate: string, endDate: string): Promise<OpenAISummaryResponse> {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
  return apiRequest<OpenAISummaryResponse>(`/integrations/openai/summary?${params.toString()}`);
}

export interface GeminiConnection {
  id: number;
  provider: string;
  status: string;
  created_at: string;
  updated_at: string;
  last_verified_at: string | null;
}
export interface GeminiConnectResponse {
  connection: GeminiConnection;
  model_count: number;
  message: string;
}
export interface GeminiTestResponse {
  connection_id: number;
  status: string;
  model_count: number;
  last_verified_at: string;
  message: string;
}
export interface GeminiUsageResponse {
  start_date: string;
  end_date: string;
  requests: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  by_model: Array<{ model: string; requests: number; input_tokens: number; output_tokens: number; total_tokens: number }>;
  daily: Array<{ date: string; requests: number; input_tokens: number; output_tokens: number; total_tokens: number }>;
}

export async function listGeminiConnections(): Promise<GeminiConnection[]> {
  return apiRequest<GeminiConnection[]>("/integrations/gemini/connections");
}
export async function connectGemini(apiKey: string): Promise<GeminiConnectResponse> {
  return apiRequest<GeminiConnectResponse>("/integrations/gemini/connections", {
    method: "POST",
    body: JSON.stringify({ api_key: apiKey }),
  });
}
export async function testGeminiConnection(connectionId: number): Promise<GeminiTestResponse> {
  return apiRequest<GeminiTestResponse>(`/integrations/gemini/connections/${connectionId}/test`, { method: "POST" });
}
export async function disconnectGemini(connectionId: number): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(`/integrations/gemini/connections/${connectionId}`, { method: "DELETE" });
}
export async function getGeminiUsage(startDate: string, endDate: string): Promise<GeminiUsageResponse> {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
  return apiRequest<GeminiUsageResponse>(`/integrations/gemini/usage?${params.toString()}`);
}
export async function generateGemini(
  model: string,
  prompt: string
): Promise<{ candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }>; usageMetadata?: { totalTokenCount?: number } }> {
  return apiRequest(`/integrations/gemini/generate`, {
    method: "POST",
    body: JSON.stringify({ model, contents: [{ role: "user", parts: [{ text: prompt }] }] }),
  });
}

export interface AzureConnection {
  id: number;
  provider: string;
  connected: boolean;
  status: string;
  created_at: string | null;
  updated_at: string | null;
  last_successful_refresh?: string | null;
}

export async function getAzureConnection(): Promise<AzureConnection> {
  return apiRequest<AzureConnection>("/integrations/azure/connection");
}
export async function connectAzureServicePrincipal(credentials: {
  tenant_id: string;
  client_id: string;
  client_secret: string;
  subscription_id?: string;
}): Promise<AzureConnection> {
  return apiRequest<AzureConnection>("/integrations/azure/connection/service-principal", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}
export async function discoverAzureSubscriptions(): Promise<{
  status: string;
  subscriptions: Array<{ id: string; display_name: string; state?: string; tenant_id?: string; selected?: boolean }>;
}> {
  return apiRequest("/integrations/azure/subscriptions/discover", { method: "POST" });
}
export async function selectAzureSubscriptions(subscription_ids: string[]): Promise<{ status: string }> {
  return apiRequest("/integrations/azure/subscriptions", {
    method: "POST",
    body: JSON.stringify({ subscription_ids }),
  });
}
export async function getAzureCost(subscriptionId: string, start: string, end: string): Promise<unknown> {
  return apiRequest(`/integrations/azure/subscriptions/${encodeURIComponent(subscriptionId)}/cost?start=${start}&end=${end}`);
}
export async function disconnectAzure(): Promise<{ status: string }> {
  return apiRequest("/integrations/azure/connection", { method: "DELETE" });
}
export async function startAzureOAuth(): Promise<{ authorization_url: string }> {
  return apiRequest<{ authorization_url: string }>("/integrations/azure/oauth/start");
}
export async function testAzureConnection(): Promise<{ status: string; last_successful_refresh: string; message: string }> {
  return apiRequest("/integrations/azure/connection/test", { method: "POST" });
}

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
export interface AnthropicConnectResponse {
  connection: AnthropicConnection;
  message: string;
}
export interface AnthropicTestResponse {
  connection_id: number;
  status: string;
  model: string;
  last_verified_at: string;
  message: string;
}
export interface AnthropicReportResponse {
  connection_id: number;
  admin_access_status: string;
  usage_status: string;
  cost_status: string;
  start_date: string;
  end_date: string;
  usage: {
    totals: Record<string, number>;
    by_model: Array<Record<string, string | number>>;
    rows: Array<Record<string, string | number | null>>;
    data_refreshed_at: string | null;
  } | null;
  cost: {
    total: string;
    list_total: string;
    currency: string;
    by_cost_type: Array<{ cost_type: string; amount: string; currency: string }>;
    rows: Array<Record<string, string | number | null>>;
    data_refreshed_at: string | null;
  } | null;
  data_refreshed_at: string | null;
  last_synced_at: string | null;
  balance: {
    status: "UNSUPPORTED" | "MANUAL" | "ACTIVE" | string;
    amount: string | null;
    currency: string | null;
    entered_at: string | null;
    source: string;
    console_url: string;
    message: string;
  };
}
export interface AnthropicAdminCredentialResponse {
  connection_id: number;
  admin_access_status: string;
  admin_verified_at: string;
  message: string;
}

export async function listAnthropicConnections(): Promise<AnthropicConnection[]> {
  return apiRequest<AnthropicConnection[]>("/integrations/anthropic/connections");
}
export async function connectAnthropic(
  apiKey: string,
  model: string,
  connectionName?: string,
  tier?: string
): Promise<AnthropicConnectResponse> {
  return apiRequest<AnthropicConnectResponse>("/integrations/anthropic/connections", {
    method: "POST",
    body: JSON.stringify({
      api_key: apiKey,
      model,
      ...(connectionName?.trim() ? { connection_name: connectionName.trim() } : {}),
      ...(tier ? { tier } : {}),
    }),
  });
}
export async function updateAnthropicConnection(
  connectionId: number,
  data: { api_key?: string; model?: string; connection_name?: string; tier?: string }
): Promise<AnthropicConnectResponse> {
  return apiRequest<AnthropicConnectResponse>(`/integrations/anthropic/connections/${connectionId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}
export async function testAnthropicConnection(connectionId: number): Promise<AnthropicTestResponse> {
  return apiRequest<AnthropicTestResponse>(`/integrations/anthropic/connections/${connectionId}/test`, { method: "POST" });
}
export async function disconnectAnthropic(connectionId: number): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(`/integrations/anthropic/connections/${connectionId}`, { method: "DELETE" });
}
export async function configureAnthropicAdminCredential(
  connectionId: number,
  adminApiKey: string
): Promise<AnthropicAdminCredentialResponse> {
  return apiRequest<AnthropicAdminCredentialResponse>(`/integrations/anthropic/connections/${connectionId}/admin-credential`, {
    method: "POST",
    body: JSON.stringify({ admin_api_key: adminApiKey }),
  });
}
export async function removeAnthropicAdminCredential(connectionId: number): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(`/integrations/anthropic/connections/${connectionId}/admin-credential`, {
    method: "DELETE",
  });
}
export async function getAnthropicReports(
  connectionId: number,
  startDate: string,
  endDate: string,
  forceRefresh = false
): Promise<AnthropicReportResponse> {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate, force_refresh: String(forceRefresh) });
  return apiRequest<AnthropicReportResponse>(`/integrations/anthropic/connections/${connectionId}/reports?${params.toString()}`);
}
export async function saveAnthropicManualBalance(
  connectionId: number,
  amount: string,
  currency: string
): Promise<{ connection_id: number; balance: AnthropicReportResponse["balance"] }> {
  return apiRequest(`/integrations/anthropic/connections/${connectionId}/balance`, {
    method: "POST",
    body: JSON.stringify({ amount, currency }),
  });
}
export async function removeAnthropicManualBalance(connectionId: number): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(`/integrations/anthropic/connections/${connectionId}/balance`, {
    method: "DELETE",
  });
}

export interface GenericProviderConnection {
  id: number;
  provider: string;
  provider_tenant_id?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  last_verified_at?: string | null;
  profile_data?: Record<string, any>;
}
export interface GenericProviderConnectResponse {
  connection: GenericProviderConnection;
  profile_data: Record<string, any>;
  message: string;
}
export interface GenericProviderDetailsResponse {
  connection_id: number;
  provider: string;
  provider_tenant_id?: string | null;
  status: string;
  created_at: string;
  last_verified_at?: string | null;
  profile_data: Record<string, any>;
}

export async function connectProvider(
  providerId: string,
  credentials: Record<string, any>
): Promise<GenericProviderConnectResponse> {
  return apiRequest<GenericProviderConnectResponse>(`/integrations/${providerId}/connections`, {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}
export async function listProviderConnections(providerId: string): Promise<GenericProviderConnection[]> {
  return apiRequest<GenericProviderConnection[]>(`/integrations/${providerId}/connections`);
}
export async function getProviderConnectionDetails(
  providerId: string,
  connectionId: number
): Promise<GenericProviderDetailsResponse> {
  return apiRequest<GenericProviderDetailsResponse>(`/integrations/${providerId}/connections/${connectionId}/details`);
}
export async function testProviderConnection(
  providerId: string,
  connectionId: number
): Promise<{ connection_id: number; status: string; message: string; last_verified_at: string; profile_data?: Record<string, any> }> {
  return apiRequest(`/integrations/${providerId}/connections/${connectionId}/test`, { method: "POST" });
}
export async function disconnectProviderConnection(providerId: string, connectionId: number): Promise<void> {
  return apiRequest<void>(`/integrations/${providerId}/connections/${connectionId}`, { method: "DELETE" });
}
export async function listAllActiveConnections(): Promise<GenericProviderConnection[]> {
  return apiRequest<GenericProviderConnection[]>("/integrations/all-active");
}
