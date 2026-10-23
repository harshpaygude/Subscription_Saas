const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";


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
        headers,
      }
    );

  } catch (error) {

    console.error(
      "API connection failed:",
      error
    );

    throw new Error(
      `Cannot connect to backend at ${API_URL}`
    );
  }


  if (!response.ok) {

    let errorMessage =
      "API request failed";


    try {

      const error =
        await response.json();

      errorMessage =
        error.detail ||
        error.message ||
        errorMessage;

    } catch {
      // Response was not JSON.
    }


    throw new Error(
      errorMessage
    );
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

export async function connectAWS(): Promise<AWSConnectResponse> {
  return apiRequest<AWSConnectResponse>("/integrations/aws/connections", {
    method: "POST",
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

  localStorage.removeItem(
    "access_token"
  );

  window.location.href =
    "/login";
}
