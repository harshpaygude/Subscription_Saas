import { apiMultipartRequest, apiRequest } from "./httpClient";

export interface EmployeeRecord {
  id: number;
  email: string;
  display_name: string | null;
  employee_id: string | null;
  phone_number: string | null;
  role: string;
  department_ids: number[];
  active_subscription_assignments: number;
  active_asset_assignments: number;
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

export async function listEmployees(): Promise<EmployeeRecord[]> {
  return apiRequest<EmployeeRecord[]>("/employees");
}

export async function createEmployee(payload: {
  employee_id: string;
  name: string;
  email: string;
  phone_number?: string;
  department_id: number;
  joined_at: string;
  asset_ids: number[];
}): Promise<EmployeeRecord> {
  return apiRequest<EmployeeRecord>("/employees", { method: "POST", body: JSON.stringify(payload) });
}

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
  return apiRequest<EmployeeRecord>(`/employees/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export async function importEmployeesCSV(file: File): Promise<BulkImportResult> {
  return apiMultipartRequest<BulkImportResult>("/employees/import-csv", file);
}
