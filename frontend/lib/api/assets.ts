import { apiMultipartRequest, apiRequest } from "./httpClient";

export interface AssetRecord {
  id: number;
  organization_id: number;
  asset_tag: string;
  asset_type: string;
  name: string;
  manufacturer: string | null;
  model: string | null;
  serial_number: string | null;
  purchase_date: string | null;
  purchase_cost: string | null;
  currency: string;
  warranty_expiry: string | null;
  location: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface AssetAssignmentRecord {
  id: number;
  organization_id: number;
  asset_id: number;
  user_id: number;
  assigned_by: number;
  assigned_at: string;
  expected_return_at: string | null;
  returned_at: string | null;
  returned_by: number | null;
  condition_at_issue: string | null;
  condition_at_return: string | null;
  handover_notes: string | null;
  status: string;
  user_name?: string | null;
  user_email?: string | null;
  user_employee_id?: string | null;
}

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
  return apiMultipartRequest<AssetBulkImportResult>("/assets/import-csv", file);
}

export async function listAssets(params: { status?: string; asset_type?: string } = {}): Promise<AssetRecord[]> {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => value && query.set(key, value));
  return apiRequest<AssetRecord[]>(`/assets${query.size ? `?${query.toString()}` : ""}`);
}

export async function createAsset(payload: {
  asset_tag: string;
  asset_type: string;
  name: string;
  manufacturer?: string;
  model?: string;
  serial_number?: string;
  purchase_date?: string;
  purchase_cost?: string;
  currency?: string;
  warranty_expiry?: string;
  location?: string;
}): Promise<AssetRecord> {
  return apiRequest<AssetRecord>("/assets", { method: "POST", body: JSON.stringify(payload) });
}

export async function assignAsset(
  id: number,
  payload: { user_id: number; expected_return_at?: string; condition_at_issue?: string; handover_notes?: string }
): Promise<AssetAssignmentRecord> {
  return apiRequest<AssetAssignmentRecord>(`/assets/${id}/assignments`, { method: "POST", body: JSON.stringify(payload) });
}

export async function listAssetAssignments(id: number): Promise<AssetAssignmentRecord[]> {
  return apiRequest<AssetAssignmentRecord[]>(`/assets/${id}/assignments`);
}

export async function returnAsset(
  id: number,
  payload: { condition_at_return?: string; handover_notes?: string } = {}
): Promise<AssetAssignmentRecord> {
  return apiRequest<AssetAssignmentRecord>(`/assets/assignments/${id}/return`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
