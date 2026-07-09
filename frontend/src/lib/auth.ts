import { apiRequest } from "./api";

export type Role = {
  id: number;
  name: string;
  slug: string;
};

export type User = {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  roles: Role[];
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
};

export type DashboardOverview = {
  clients: number;
  vehicles: number;
  online: number;
  offline: number;
};

const ACCESS_TOKEN_KEY = "vt_access_token";
const AUTH_COOKIE = "vt_auth";

export function getStoredAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setStoredAccessToken(token: string): void {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, token);
  document.cookie = `${AUTH_COOKIE}=1; path=/; SameSite=Lax; max-age=${7 * 24 * 60 * 60}`;
}

export function clearStoredAccessToken(): void {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  document.cookie = `${AUTH_COOKIE}=; path=/; max-age=0`;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const data = await apiRequest<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setStoredAccessToken(data.access_token);
  return data;
}

export async function refreshAccessToken(): Promise<string> {
  const data = await apiRequest<TokenResponse>("/auth/refresh", { method: "POST" });
  setStoredAccessToken(data.access_token);
  return data.access_token;
}

export async function logout(token: string | null): Promise<void> {
  try {
    await apiRequest<void>("/auth/logout", {
      method: "POST",
      token,
    });
  } finally {
    clearStoredAccessToken();
  }
}

export async function fetchMe(token: string): Promise<User> {
  return apiRequest<User>("/auth/me", { token });
}

export async function fetchDashboardOverview(token: string): Promise<DashboardOverview> {
  return apiRequest<DashboardOverview>("/dashboard/overview", { token });
}
