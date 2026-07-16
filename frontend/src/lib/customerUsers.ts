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
  created_at: string;
  updated_at: string;
};

export type CustomerUserListResponse = {
  items: CustomerUser[];
  total: number;
};

export type CustomerUserCreatePayload = {
  full_name: string;
  email: string;
  password: string;
  role: CustomerUserRole;
  status: CustomerUserStatus;
};

export type CustomerUserUpdatePayload = {
  full_name?: string;
  password?: string;
  role?: CustomerUserRole;
  status?: CustomerUserStatus;
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
  customerId: number,
): Promise<CustomerUserListResponse> {
  return apiRequest<CustomerUserListResponse>(`/customers/${customerId}/users`, { token });
}

export async function createCustomerUser(
  token: string,
  customerId: number,
  payload: CustomerUserCreatePayload,
): Promise<CustomerUser> {
  return apiRequest<CustomerUser>(`/customers/${customerId}/users`, {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function updateCustomerUser(
  token: string,
  customerId: number,
  userId: number,
  payload: CustomerUserUpdatePayload,
): Promise<CustomerUser> {
  return apiRequest<CustomerUser>(`/customers/${customerId}/users/${userId}`, {
    method: "PUT",
    token,
    body: JSON.stringify(payload),
  });
}

export async function deleteCustomerUser(
  token: string,
  customerId: number,
  userId: number,
): Promise<void> {
  await apiRequest<void>(`/customers/${customerId}/users/${userId}`, {
    method: "DELETE",
    token,
  });
}

export function mapCustomerUserError(detail: string): string {
  const messages: Record<string, string> = {
    customer_not_found: "Cliente não encontrado",
    customer_user_not_found: "Usuário não encontrado",
    customer_user_email_exists: "Já existe um usuário com este e-mail",
  };
  return messages[detail] ?? detail;
}
