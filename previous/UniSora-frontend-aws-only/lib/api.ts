
const API_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

/* ========================= */
/* TYPES */
/* ========================= */

export interface User {
  id: number;
  email: string;
  organization_id: number;
  role: string;
}

export interface Organization {
  id: number;
  name: string;
  created_at: string;
}

export interface ProviderMetadata {
  provider_id: string;
  display_name: string;
  description: string;
  capabilities: string[];
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface AWSConnection {
  id: number;
  provider: string;
  account_id: string | null;
  status: string;
  region: string;
  created_at: string;
  updated_at: string;
}

export interface AWSConnectionSetupResponse {
  connection_id: number;
  account_id: string;
  external_id: string;
  trusted_principal_arn: string;
  trust_policy: Record<string, unknown>;
  next_step: string;
}

export interface AWSConnectResponse {
  connection: AWSConnection;
  identity_arn: string;
  cost_access: boolean;
  message: string;
}

export interface AWSConnectionVerifyResponse {
  connection: AWSConnection;
  identity_arn: string;
  cost_access: boolean;
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

  const headers = new Headers(options.headers);

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;

  try {
    response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    });
  } catch (error) {
    console.error("API connection failed:", error);
    throw new Error(`Cannot connect to backend at ${API_URL}`);
  }

  if (!response.ok) {
    let errorMessage = `API request failed (${response.status})`;

    try {
      const error = await response.json();
      errorMessage =
        error.detail || error.message || errorMessage;
    } catch {
      // The response was not JSON.
    }

    throw new Error(errorMessage);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

/* ========================= */
/* AUTHENTICATION */
/* ========================= */

export async function register(
  email: string,
  password: string,
  organizationName: string
): Promise<User> {
  return apiRequest<User>("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      email,
      password,
      organization_name: organizationName,
    }),
  });
}

export async function login(
  email: string,
  password: string
): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function getCurrentUser(): Promise<User> {
  return apiRequest<User>("/auth/me");
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

export async function listProviders(): Promise<ProviderMetadata[]> {
  return apiRequest<ProviderMetadata[]>("/integrations/providers");
}

/* ========================= */
/* AWS INTEGRATION */
/* ========================= */

export async function listAWSConnections(): Promise<AWSConnection[]> {
  return apiRequest<AWSConnection[]>("/integrations/aws/connections");
}

/**
 * Stage 1: Create a pending AWS connection and retrieve
 * its external ID and trust policy.
 */
export async function setupAWSConnection(
  accountId: string
): Promise<AWSConnectionSetupResponse> {
  return apiRequest<AWSConnectionSetupResponse>(
    "/integrations/aws/connections/setup",
    {
      method: "POST",
      body: JSON.stringify({ account_id: accountId }),
    }
  );
}

/**
 * Stage 2: Verify the role created in the target AWS account.
 */
export async function verifyAWSConnection(
  connectionId: number,
  roleArn: string
): Promise<AWSConnectionVerifyResponse> {
  return apiRequest<AWSConnectionVerifyResponse>(
    `/integrations/aws/connections/${connectionId}/verify`,
    {
      method: "POST",
      body: JSON.stringify({ role_arn: roleArn }),
    }
  );
}

export async function disconnectAWS(
  connectionId: number
): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(
    `/integrations/aws/connections/${connectionId}`,
    { method: "DELETE" }
  );
}

export async function getAWSCosts(
  connectionId: number
): Promise<AWSCostResponse> {
  return apiRequest<AWSCostResponse>(
    `/integrations/aws/connections/${connectionId}/costs`
  );
}

export async function getAWSAccountPlan(
  connectionId: number
): Promise<AWSAccountPlanResponse> {
  return apiRequest<AWSAccountPlanResponse>(
    `/integrations/aws/connections/${connectionId}/account-plan`
  );
}

/* ========================= */
/* LOGOUT */
/* ========================= */

export function logout(): void {
  localStorage.removeItem("access_token");
  window.location.href = "/login";
}

