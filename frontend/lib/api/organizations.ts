import { apiMultipartRequest, apiRequest } from "./httpClient";

export interface Organization {
  id: number;
  name: string;
  created_at: string;
  legal_name?: string | null;
  display_name?: string | null;
  industry?: string | null;
  company_size?: string | null;
  website?: string | null;
  company_email?: string | null;
  company_phone?: string | null;
  country?: string | null;
  state?: string | null;
  city?: string | null;
  address?: string | null;
  postal_code?: string | null;
  tax_registration_number?: string | null;
  onboarding_completed?: boolean;
  onboarding_completed_at?: string | null;
}

export interface OnboardingStatus {
  onboarding_completed: boolean;
  onboarding_completed_at: string | null;
}

export interface DepartmentInput {
  name: string;
  description?: string;
}

export interface CompanyProfile {
  legal_name?: string;
  display_name?: string;
  industry?: string;
  company_size?: string;
  website?: string;
  company_email?: string;
  company_phone?: string;
  country?: string;
  state?: string;
  city?: string;
  address?: string;
  postal_code?: string;
  tax_registration_number?: string;
}

export interface ExcelAssetItem {
  asset_tag: string;
  name: string;
  asset_type?: string;
  manufacturer?: string | null;
  model?: string | null;
  serial_number?: string | null;
  purchase_cost?: string | null;
  currency?: string;
  location?: string | null;
  assigned_to?: string | null;
}

export interface ExcelEmployeeItem {
  employee_id: string;
  full_name: string;
  email: string;
  phone_number?: string | null;
  department_name?: string | null;
  joining_date?: string | null;
}

export interface OnboardingPayload {
  company: CompanyProfile;
  departments: DepartmentInput[];
  employees?: ExcelEmployeeItem[];
  assets?: ExcelAssetItem[];
}

export interface ExcelImportResult {
  valid: boolean;
  company: {
    company_name?: string | null;
    legal_name?: string | null;
    industry?: string | null;
    company_size?: string | null;
    website?: string | null;
    company_email?: string | null;
    company_phone?: string | null;
    country?: string | null;
    state?: string | null;
    city?: string | null;
    address?: string | null;
    postal_code?: string | null;
    tax_registration_number?: string | null;
  } | null;
  departments: DepartmentInput[];
  employees: ExcelEmployeeItem[];
  assets: ExcelAssetItem[];
  errors: string[];
  warnings: string[];
  department_count: number;
  employee_count: number;
  asset_count: number;
}

export async function getOrganization(organizationId: number): Promise<Organization> {
  return apiRequest<Organization>(`/organizations/${organizationId}`);
}

export async function getOnboardingStatus(): Promise<OnboardingStatus> {
  return apiRequest<OnboardingStatus>("/organizations/me/onboarding-status");
}

export async function updateOrganizationProfile(payload: CompanyProfile): Promise<Organization> {
  return apiRequest<Organization>("/organizations/me/profile", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function submitOnboarding(payload: OnboardingPayload): Promise<Organization> {
  return apiRequest<Organization>("/organizations/me/onboarding", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function parseOnboardingExcel(file: File): Promise<ExcelImportResult> {
  return apiMultipartRequest<ExcelImportResult>("/organizations/me/onboarding/parse-excel", file);
}
