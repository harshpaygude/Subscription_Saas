import { apiRequest } from "./httpClient";

export interface User {
  id: number;
  email: string;
  organization_id: number;
  role: string;
  display_name: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export async function register(email: string, password: string, organizationName: string): Promise<User> {
  return apiRequest<User>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, organization_name: organizationName }),
  });
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function getCurrentUser(): Promise<User> {
  return apiRequest<User>("/auth/me");
}

export async function updateProfile(data: { display_name: string }): Promise<User> {
  return apiRequest<User>("/auth/me", { method: "PATCH", body: JSON.stringify(data) });
}

export async function changePassword(data: {
  current_password: string;
  new_password: string;
  confirm_password: string;
}): Promise<{ message: string }> {
  return apiRequest<{ message: string }>("/auth/change-password", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function logout() {
  localStorage.removeItem("access_token");
  window.location.replace("/login");
}
