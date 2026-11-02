const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { credentials: "include", ...init });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail ?? `Request failed (${response.status})`);
  return body as T;
}

export type Subscription = { id: string; display_name: string; state?: string; tenant_id?: string; selected?: boolean };
export type Connection = { connected: boolean; status: string; last_successful_refresh?: string };

export const api = {
  connection: () => request<Connection>("/api/azure/connection"),
  devSession: (user_id: string) => request<{ status: string }>("/api/dev/session", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ user_id }) }),
  manualToken: (access_token: string) => request<{ status: string }>("/api/azure/dev/manual-token", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ access_token }) }),
  clearManualToken: () => request<{ status: string }>("/api/azure/dev/manual-token", { method: "DELETE" }),
  discover: () => request<{ status: string; mode?: string; subscriptions: Subscription[] }>("/api/azure/subscriptions/discover", { method: "POST" }),
  select: (subscription_ids: string[]) => request<{ status: string }>("/api/azure/subscriptions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ subscription_ids }) }),
  resources: (subscription_id: string) => request<{ resources: Record<string, unknown>[] }>(`/api/azure/subscriptions/${encodeURIComponent(subscription_id)}/resources`),
};

export function beginOAuth(): void { window.location.href = `${API_BASE}/api/azure/oauth/start`; }
