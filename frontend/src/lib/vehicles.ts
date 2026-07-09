import { apiRequest } from "./api";

export type VehicleStatus =
  | "ACTIVE"
  | "INACTIVE"
  | "PENDING_INSTALLATION"
  | "IN_STOCK"
  | "DECOMMISSIONED";

export type VehicleCategory =
  | "CAR"
  | "MOTORCYCLE"
  | "TRUCK"
  | "TRAILER"
  | "IMPLEMENT"
  | "OTHER";

export type VehicleFuel =
  | "GASOLINE"
  | "ETHANOL"
  | "FLEX"
  | "DIESEL"
  | "ELECTRIC"
  | "HYBRID"
  | "GNV"
  | "OTHER";

export type Vehicle = {
  id: number;
  customer_id: number;
  plate: string;
  nickname: string | null;
  brand: string | null;
  model: string | null;
  version: string | null;
  year_model: number | null;
  year_manufacture: number | null;
  color: string | null;
  fuel: VehicleFuel | null;
  renavam: string | null;
  chassis: string | null;
  category: VehicleCategory | null;
  cover_image: string | null;
  odometer: number | null;
  notes: string | null;
  status: VehicleStatus;
  created_at: string;
  updated_at: string;
};

export type VehicleStats = {
  total: number;
  active: number;
  inactive: number;
  pending_installation: number;
  in_stock: number;
};

export type VehicleListResponse = {
  items: Vehicle[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  stats: VehicleStats;
};

export type VehiclePayload = {
  customer_id: number;
  plate: string;
  nickname?: string | null;
  brand?: string | null;
  model?: string | null;
  version?: string | null;
  year_model?: number | null;
  year_manufacture?: number | null;
  color?: string | null;
  fuel?: VehicleFuel | null;
  renavam?: string | null;
  chassis?: string | null;
  category?: VehicleCategory | null;
  cover_image?: string | null;
  odometer?: number | null;
  notes?: string | null;
};

export type VehicleQuery = {
  search?: string;
  status?: VehicleStatus;
  customer_id?: number;
  category?: VehicleCategory;
  page?: number;
  page_size?: number;
  sort_by?: "plate" | "nickname" | "brand" | "model" | "created_at" | "updated_at";
  sort_order?: "asc" | "desc";
};

function buildQuery(params: VehicleQuery): string {
  const query = new URLSearchParams();
  if (params.search) query.set("search", params.search);
  if (params.status) query.set("status", params.status);
  if (params.customer_id) query.set("customer_id", String(params.customer_id));
  if (params.category) query.set("category", params.category);
  if (params.page) query.set("page", String(params.page));
  if (params.page_size) query.set("page_size", String(params.page_size));
  if (params.sort_by) query.set("sort_by", params.sort_by);
  if (params.sort_order) query.set("sort_order", params.sort_order);
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

export async function fetchVehicles(
  token: string,
  params: VehicleQuery = {},
): Promise<VehicleListResponse> {
  return apiRequest<VehicleListResponse>(`/vehicles${buildQuery(params)}`, { token });
}

export async function fetchVehicle(token: string, id: number): Promise<Vehicle> {
  return apiRequest<Vehicle>(`/vehicles/${id}`, { token });
}

export async function createVehicle(token: string, payload: VehiclePayload): Promise<Vehicle> {
  return apiRequest<Vehicle>("/vehicles", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function updateVehicle(
  token: string,
  id: number,
  payload: VehiclePayload,
): Promise<Vehicle> {
  return apiRequest<Vehicle>(`/vehicles/${id}`, {
    method: "PUT",
    token,
    body: JSON.stringify(payload),
  });
}

export async function updateVehicleStatus(
  token: string,
  id: number,
  status: VehicleStatus,
): Promise<Vehicle> {
  return apiRequest<Vehicle>(`/vehicles/${id}/status`, {
    method: "PATCH",
    token,
    body: JSON.stringify({ status }),
  });
}

export async function deleteVehicle(token: string, id: number): Promise<void> {
  await apiRequest<void>(`/vehicles/${id}`, { method: "DELETE", token });
}

export const VEHICLE_STATUS_LABELS: Record<VehicleStatus, string> = {
  ACTIVE: "Ativo",
  INACTIVE: "Inativo",
  PENDING_INSTALLATION: "Aguardando instalação",
  IN_STOCK: "Em estoque",
  DECOMMISSIONED: "Baixado",
};

export const VEHICLE_CATEGORY_LABELS: Record<VehicleCategory, string> = {
  CAR: "Carro",
  MOTORCYCLE: "Moto",
  TRUCK: "Caminhão",
  TRAILER: "Carreta",
  IMPLEMENT: "Implemento",
  OTHER: "Outro",
};

export function vehicleDisplayName(vehicle: Vehicle): string {
  if (vehicle.nickname) return vehicle.nickname;
  const brandModel = [vehicle.brand, vehicle.model].filter(Boolean).join(" ");
  return brandModel || vehicle.plate;
}

export function vehicleSubtitle(vehicle: Vehicle): string {
  const brandModel = [vehicle.brand, vehicle.model, vehicle.version].filter(Boolean).join(" ");
  return brandModel || "Veículo sem marca/modelo";
}

export function mapVehicleError(detail: string): string {
  const messages: Record<string, string> = {
    plate_already_exists: "Já existe um veículo com esta placa",
    chassis_already_exists: "Já existe um veículo com este chassi",
    customer_not_found: "Cliente não encontrado",
    vehicle_not_found: "Veículo não encontrado",
    invalid_plate: "Placa inválida",
    invalid_renavam: "RENAVAM inválido",
    invalid_chassis: "Chassi inválido",
    invalid_cover_image: "URL da imagem inválida",
  };
  return messages[detail] ?? detail;
}
