import { apiRequest } from "./api";

export type CustomerUserRole = "CLIENT_ADMIN" | "OPERATOR" | "VIEWER";
export type CustomerUserStatus = "ACTIVE" | "INACTIVE";

export type CustomerUser = {
  id: number;
  customer_id: number;
  full_name: string;
  email: string;
  role: CustomerUserRole;
  status: CustomerUserStatus;
  must_change_password: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CustomerUserListResponse = {
  items: CustomerUser[];
  total: number;
};

export type CustomerUserCreatePayload = {
  customer_id: number;
  full_name: string;
  email: string;
  password: string;
  password_confirm: string;
  role: CustomerUserRole;
  status?: CustomerUserStatus;
  must_change_password: boolean;
};

export type CustomerUserUpdatePayload = {
  full_name?: string;
  email?: string;
  role?: CustomerUserRole;
  must_change_password?: boolean;
};

export type CustomerUserResetPasswordPayload = {
  password: string;
  password_confirm: string;
  must_change_password: boolean;
};

export const CUSTOMER_USER_ROLE_LABELS: Record<CustomerUserRole, string> = {
  CLIENT_ADMIN: "Administrador do Cliente",
  OPERATOR: "Operador",
  VIEWER: "Somente Leitura",
};

export const CUSTOMER_USER_STATUS_LABELS: Record<CustomerUserStatus, string> = {
  ACTIVE: "Ativo",
  INACTIVE: "Inativo",
};

export async function fetchCustomerUsers(
  token: string,
  customerId?: number,
): Promise<CustomerUserListResponse> {
  const qs = customerId ? `?customer_id=${customerId}` : "";
  return apiRequest<CustomerUserListResponse>(`/customer-users${qs}`, { token });
}

export async function createCustomerUser(
  token: string,
  payload: CustomerUserCreatePayload,
): Promise<CustomerUser> {
  return apiRequest<CustomerUser>("/customer-users", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function updateCustomerUser(
  token: string,
  userId: number,
  payload: CustomerUserUpdatePayload,
): Promise<CustomerUser> {
  return apiRequest<CustomerUser>(`/customer-users/${userId}`, {
    method: "PUT",
    token,
    body: JSON.stringify(payload),
  });
}

export async function updateCustomerUserStatus(
  token: string,
  userId: number,
  status: CustomerUserStatus,
): Promise<CustomerUser> {
  return apiRequest<CustomerUser>(`/customer-users/${userId}/status`, {
    method: "PATCH",
    token,
    body: JSON.stringify({ status }),
  });
}

export async function resetCustomerUserPassword(
  token: string,
  userId: number,
  payload: CustomerUserResetPasswordPayload,
): Promise<CustomerUser> {
  return apiRequest<CustomerUser>(`/customer-users/${userId}/reset-password`, {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function deleteCustomerUser(token: string, userId: number): Promise<void> {
  await apiRequest<void>(`/customer-users/${userId}`, {
    method: "DELETE",
    token,
  });
}

export function mapCustomerUserError(detail: string): string {
  const messages: Record<string, string> = {
    customer_not_found: "Cliente não encontrado",
    customer_user_not_found: "Usuário não encontrado",
    customer_user_email_exists: "Já existe um usuário com este e-mail",
    passwords_do_not_match: "As senhas não coincidem",
  };
  return messages[detail] ?? detail;
}

export function formatLastLogin(value: string | null): string {
  if (!value) return "Nunca acessou";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Nunca acessou";
  return date.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
