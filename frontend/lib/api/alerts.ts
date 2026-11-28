import { apiRequest } from "./httpClient";

export interface AlertRecord {
  id: number;
  organization_id: number;
  provider: string | null;
  subscription_id: number | null;
  category: string;
  severity: string;
  title: string;
  description: string;
  is_read: boolean;
  is_resolved: boolean;
  created_at: string;
  updated_at: string;
}

export async function listAlerts(params: { read?: boolean; resolved?: boolean } = {}): Promise<AlertRecord[]> {
  const query = new URLSearchParams();
  if (params.read !== undefined) query.set("read", String(params.read));
  if (params.resolved !== undefined) query.set("resolved", String(params.resolved));
  return apiRequest<AlertRecord[]>(`/alerts${query.size ? `?${query.toString()}` : ""}`);
}

export async function markAlertRead(id: number): Promise<AlertRecord> {
  return apiRequest<AlertRecord>(`/alerts/${id}/read`, { method: "POST" });
}

export async function resolveAlert(id: number): Promise<AlertRecord> {
  return apiRequest<AlertRecord>(`/alerts/${id}/resolve`, { method: "POST" });
}
