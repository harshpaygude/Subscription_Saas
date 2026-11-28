import { apiRequest } from "./httpClient";

export interface LifecycleTaskRecord {
  id: number;
  lifecycle_id: number;
  task_type: string;
  title: string;
  status: string;
  action_status: string;
  required: boolean;
  assignee_id: number | null;
  related_subscription_id: number | null;
  related_subscription_assignment_id: number | null;
  related_asset_id: number | null;
  related_asset_assignment_id: number | null;
  due_at: string | null;
  completed_at: string | null;
  completed_by: number | null;
  completion_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface LifecycleResourceRecord {
  id: number;
  resource_id: number;
  status: string;
  assigned_at: string;
  released_at: string | null;
  resource_name?: string | null;
  resource_provider?: string | null;
}

export interface LifecycleEmployeeRecord {
  id: number;
  user_id: number;
  email: string;
  display_name: string | null;
  employee_id: string | null;
  phone_number: string | null;
  role: string;
  status: string;
  joined_at: string;
  last_working_date: string | null;
  department_ids: number[];
  department_names: string[];
  subscription_assignments: LifecycleResourceRecord[];
  asset_assignments: LifecycleResourceRecord[];
  tasks: LifecycleTaskRecord[];
  open_task_count: number;
  completed_task_count: number;
}

export interface LifecycleDashboardRecord {
  new_joiners: LifecycleEmployeeRecord[];
  working: LifecycleEmployeeRecord[];
  offboarding: LifecycleEmployeeRecord[];
  completed: LifecycleEmployeeRecord[];
  pending_tasks: LifecycleTaskRecord[];
}

export async function getLifecycleDashboard(): Promise<LifecycleDashboardRecord> {
  return apiRequest<LifecycleDashboardRecord>("/employee-lifecycle/dashboard");
}

export async function getEmployeeLifecycle(userId: number): Promise<LifecycleEmployeeRecord> {
  return apiRequest<LifecycleEmployeeRecord>(`/employees/${userId}/lifecycle`);
}

export async function startEmployeeOnboarding(
  userId: number,
  payload: {
    department_id: number;
    joined_at: string;
    tasks?: Array<{ task_type: string; title: string; subscription_id?: number; asset_id?: number; due_at?: string; required?: boolean }>;
  }
): Promise<LifecycleEmployeeRecord> {
  return apiRequest<LifecycleEmployeeRecord>(`/employees/${userId}/onboarding`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function startEmployeeOffboarding(userId: number, last_working_date: string): Promise<LifecycleEmployeeRecord> {
  return apiRequest<LifecycleEmployeeRecord>(`/employees/${userId}/offboarding`, {
    method: "POST",
    body: JSON.stringify({ last_working_date }),
  });
}

export async function completeLifecycleTask(taskId: number, completion_note?: string): Promise<LifecycleTaskRecord> {
  return apiRequest<LifecycleTaskRecord>(`/lifecycle-tasks/${taskId}/complete`, {
    method: "POST",
    body: JSON.stringify({ completion_note }),
  });
}
