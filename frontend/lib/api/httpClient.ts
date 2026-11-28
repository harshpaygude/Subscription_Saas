export const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api";

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

function getAuthToken(): string | null {
  return typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
}

export async function apiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  const headers = new Headers(options.headers);
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  if (!isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const url = `${API_URL}${endpoint}`;
  let response: Response;

  try {
    response = await fetch(url, {
      ...options,
      cache: options.cache ?? "no-store",
      credentials: "include",
      headers,
    });
  } catch (error) {
    const thrown = describeThrownValue(error);
    console.error(
      "API connection failed",
      JSON.stringify({
        phase: "before-http-response",
        method: options.method || "GET",
        url: redactUrl(url),
        errorName: thrown.name,
        errorMessage: thrown.message,
        thrownType: thrown.type,
      })
    );
    throw new ApiNetworkError(options.method || "GET", url);
  }

  if (!response.ok) {
    let errorMessage = "API request failed";
    let responseDetail = "";
    try {
      const error = await response.json();
      responseDetail = sanitizeDiagnosticValue(error.detail || error.message || "");
      errorMessage = responseDetail || errorMessage;
    } catch {
      // Non-JSON error response
    }

    console.error(
      "API request returned an error",
      JSON.stringify({
        phase: "http-response",
        method: options.method || "GET",
        url: redactUrl(url),
        status: response.status,
        statusText: response.statusText,
        responseDetail: responseDetail || "<non-json-or-empty>",
      })
    );

    if (
      response.status === 401 &&
      typeof window !== "undefined" &&
      !endpoint.startsWith("/auth/login") &&
      !endpoint.startsWith("/auth/register")
    ) {
      localStorage.removeItem("access_token");
      if (!window.location.pathname.startsWith("/login")) {
        window.location.replace("/login?reason=session-expired");
      }
    }

    throw new ApiError(errorMessage, response.status, endpoint);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json();
}

export async function apiMultipartRequest<T>(endpoint: string, file: File): Promise<T> {
  const formData = new FormData();
  formData.append("file", file);
  return apiRequest<T>(endpoint, { method: "POST", body: formData });
}
