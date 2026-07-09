import { apiRequest } from "./api";

export type CustomerStatus = "ACTIVE" | "INACTIVE";
export type DocumentType = "CPF" | "CNPJ";

export type Customer = {
  id: number;
  company_id: number | null;
  full_name: string;
  document: string;
  document_type: DocumentType;
  phone: string;
  secondary_phone: string | null;
  email: string | null;
  zip_code: string | null;
  street: string | null;
  number: string | null;
  complement: string | null;
  district: string | null;
  city: string | null;
  state: string | null;
  notes: string | null;
  status: CustomerStatus;
  created_at: string;
  updated_at: string;
};

export type CustomerStats = {
  total: number;
  active: number;
  inactive: number;
};

export type CustomerListResponse = {
  items: Customer[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  stats: CustomerStats;
};

export type CustomerPayload = {
  full_name: string;
  document: string;
  document_type: DocumentType;
  phone: string;
  secondary_phone?: string | null;
  email?: string | null;
  zip_code?: string | null;
  street?: string | null;
  number?: string | null;
  complement?: string | null;
  district?: string | null;
  city?: string | null;
  state?: string | null;
  notes?: string | null;
};

export type CustomerQuery = {
  search?: string;
  status?: CustomerStatus;
  page?: number;
  page_size?: number;
  sort_by?: "full_name" | "created_at" | "city" | "status";
  sort_order?: "asc" | "desc";
};

function buildQuery(params: CustomerQuery): string {
  const query = new URLSearchParams();
  if (params.search) query.set("search", params.search);
  if (params.status) query.set("status", params.status);
  if (params.page) query.set("page", String(params.page));
  if (params.page_size) query.set("page_size", String(params.page_size));
  if (params.sort_by) query.set("sort_by", params.sort_by);
  if (params.sort_order) query.set("sort_order", params.sort_order);
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

export async function fetchCustomers(
  token: string,
  params: CustomerQuery = {},
): Promise<CustomerListResponse> {
  return apiRequest<CustomerListResponse>(`/customers${buildQuery(params)}`, { token });
}

export async function fetchCustomer(token: string, id: number): Promise<Customer> {
  return apiRequest<Customer>(`/customers/${id}`, { token });
}

export async function createCustomer(token: string, payload: CustomerPayload): Promise<Customer> {
  return apiRequest<Customer>("/customers", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function updateCustomer(
  token: string,
  id: number,
  payload: CustomerPayload,
): Promise<Customer> {
  return apiRequest<Customer>(`/customers/${id}`, {
    method: "PUT",
    token,
    body: JSON.stringify(payload),
  });
}

export async function updateCustomerStatus(
  token: string,
  id: number,
  status: CustomerStatus,
): Promise<Customer> {
  return apiRequest<Customer>(`/customers/${id}/status`, {
    method: "PATCH",
    token,
    body: JSON.stringify({ status }),
  });
}

export async function deleteCustomer(token: string, id: number): Promise<void> {
  await apiRequest<void>(`/customers/${id}`, { method: "DELETE", token });
}
