import { apiRequest } from "./httpClient";

export interface DepartmentRecord {
  id: number;
  organization_id: number;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MembershipRecord {
  id: number;
  organization_id: number;
  department_id: number;
  user_id: number;
  is_active: boolean;
  effective_from: string;
  effective_to: string | null;
  created_at: string;
  email: string | null;
  display_name: string | null;
}

export async function listDepartments(): Promise<DepartmentRecord[]> {
  return apiRequest<DepartmentRecord[]>("/departments");
}
export async function createDepartment(payload: { name: string; description?: string }): Promise<DepartmentRecord> {
  return apiRequest<DepartmentRecord>("/departments", { method: "POST", body: JSON.stringify(payload) });
}
export async function updateDepartment(
  id: number,
  payload: Partial<{ name: string; description: string; is_active: boolean }>
): Promise<DepartmentRecord> {
  return apiRequest<DepartmentRecord>(`/departments/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}
export async function listDepartmentMembers(id: number): Promise<MembershipRecord[]> {
  return apiRequest<MembershipRecord[]>(`/departments/${id}/members`);
}
export async function addDepartmentMember(id: number, user_id: number): Promise<MembershipRecord> {
  return apiRequest<MembershipRecord>(`/departments/${id}/members`, { method: "POST", body: JSON.stringify({ user_id }) });
}
