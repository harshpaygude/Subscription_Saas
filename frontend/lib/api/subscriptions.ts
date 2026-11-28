import { apiMultipartRequest, apiRequest } from "./httpClient";

export interface SubscriptionRecord {
  id: number;
  organization_id: number;
  provider: string;
  name: string;
  plan: string | null;
  amount: string | null;
  currency: string;
  billing_interval: string;
  renewal_type: string | null;
  start_date: string | null;
  next_renewal_date: string | null;
  status: string;
  cancellation_date: string | null;
  source: string;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface SpendRow {
  service: string;
  name: string;
  monthly_spend: string;
  currency: string;
  billing_source: string;
  billing_period: string;
  last_updated: string;
  status: string;
}

export interface MonthlySpendResponse {
  totals_by_currency: Record<string, string>;
  services: SpendRow[];
}

export interface SubscriptionLicenseRecord {
  id: number;
  organization_id: number;
  subscription_id: number;
  reference: string | null;
  capacity: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface SubscriptionAssignmentRecord {
  id: number;
  organization_id: number;
  subscription_id: number;
  license_id: number | null;
  user_id: number;
  assigned_by: number;
  assigned_at: string;
  released_at: string | null;
  status: string;
  notes: string | null;
}

export async function listSubscriptions(params: { provider?: string; status?: string } = {}): Promise<SubscriptionRecord[]> {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => value && query.set(key, value));
  return apiRequest<SubscriptionRecord[]>(`/subscriptions${query.size ? `?${query.toString()}` : ""}`);
}

export async function createSubscription(
  payload: Omit<SubscriptionRecord, "id" | "organization_id" | "status" | "cancellation_date" | "source" | "created_at" | "updated_at" | "renewal_type"> & {
    status?: string;
    renewal_type?: string | null;
  }
): Promise<SubscriptionRecord> {
  return apiRequest<SubscriptionRecord>("/subscriptions", { method: "POST", body: JSON.stringify(payload) });
}

export async function importSubscriptionsCSV(
  file: File
): Promise<{ success: boolean; imported: number; updated: number; total_processed: number; errors: string[] }> {
  return apiMultipartRequest("/subscriptions/import-csv", file);
}

export async function seedDemoSubscriptions(): Promise<{
  message: string;
  imported: number;
  updated: number;
  total_processed: number;
  errors: string[];
}> {
  return apiRequest("/subscriptions/seed-demo", { method: "POST" });
}

export async function createSubscriptionLicense(
  subscriptionId: number,
  payload: { reference?: string; capacity: number }
): Promise<SubscriptionLicenseRecord> {
  return apiRequest<SubscriptionLicenseRecord>(`/subscriptions/${subscriptionId}/licenses`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listSubscriptionLicenses(subscriptionId: number): Promise<SubscriptionLicenseRecord[]> {
  return apiRequest<SubscriptionLicenseRecord[]>(`/subscriptions/${subscriptionId}/licenses`);
}

export async function listSubscriptionAssignments(
  params: { subscription_id?: number; user_id?: number } = {}
): Promise<SubscriptionAssignmentRecord[]> {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => value !== undefined && query.set(key, String(value)));
  return apiRequest<SubscriptionAssignmentRecord[]>(`/subscription-assignments${query.size ? `?${query.toString()}` : ""}`);
}

export async function assignSubscription(payload: {
  subscription_id: number;
  license_id: number;
  user_id: number;
  notes?: string;
}): Promise<SubscriptionAssignmentRecord> {
  return apiRequest<SubscriptionAssignmentRecord>("/subscription-assignments", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function releaseSubscriptionAssignment(id: number): Promise<SubscriptionAssignmentRecord> {
  return apiRequest<SubscriptionAssignmentRecord>(`/subscription-assignments/${id}/release`, { method: "POST" });
}

export async function cancelSubscription(id: number): Promise<SubscriptionRecord> {
  return apiRequest<SubscriptionRecord>(`/subscriptions/${id}/cancel`, { method: "POST" });
}

export async function deleteSubscription(id: number): Promise<void> {
  await apiRequest<unknown>(`/subscriptions/${id}`, { method: "DELETE" });
}

export async function getMonthlySpend(): Promise<MonthlySpendResponse> {
  return apiRequest<MonthlySpendResponse>("/subscriptions/spend");
}

export async function createManualSpend(payload: {
  provider: string;
  amount: string;
  currency: string;
  billing_interval: string;
  period_start: string;
  period_end?: string;
  note?: string;
}): Promise<SpendRow> {
  return apiRequest<SpendRow>("/subscriptions/manual-spend", { method: "POST", body: JSON.stringify(payload) });
}
