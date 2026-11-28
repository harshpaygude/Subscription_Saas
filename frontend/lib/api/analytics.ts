import { apiRequest } from "./httpClient";

export interface AnalyticsSummary {
  active_subscriptions: number;
  cancelled_subscriptions: number;
  upcoming_renewals: number;
  totals_by_currency: Record<string, string>;
  by_provider: Record<string, { currency: string; monthly_spend: string; data_status: string }>;
  departments?: number;
  assets?: { total: number; assigned: number; available: number };
  license_utilization?: number;
  historical: Array<{ month: string; totals_by_currency: Record<string, string> }>;
  historical_note: string;
}

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

export async function getAnalyticsSummary(): Promise<AnalyticsSummary> {
  return apiRequest<AnalyticsSummary>("/analytics/summary");
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
