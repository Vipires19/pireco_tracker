import { apiRequest } from "./api";

export type InstallationType = "PRIMARY" | "BAIT" | "AUXILIARY";

export type InstallationStatus =
  | "PENDING"
  | "IN_PROGRESS"
  | "INSTALLED"
  | "REMOVED"
  | "CANCELLED";

export type InstallationChecklist = {
  power_connected: boolean;
  gps_ok: boolean;
  gsm_ok: boolean;
  ignition_ok: boolean;
  blocking_ok: boolean;
  test_drive_completed: boolean;
  customer_present: boolean;
};

export type TrackerSummary = {
  id: number;
  imei: string;
  model: string | null;
  last_seen_at: string | null;
};

export type VehicleSummary = {
  id: number;
  plate: string;
  nickname: string | null;
};

export type CustomerSummary = {
  id: number;
  full_name: string;
};

export type TechnicianSummary = {
  id: number;
  full_name: string;
};

export type Installation = {
  id: number;
  tracker_id: number;
  vehicle_id: number;
  installation_type: InstallationType;
  status: InstallationStatus;
  installed_at: string;
  installed_by: number | null;
  installation_notes: string | null;
  power_connected: boolean;
  gps_ok: boolean;
  gsm_ok: boolean;
  ignition_ok: boolean;
  blocking_ok: boolean;
  test_drive_completed: boolean;
  customer_present: boolean;
  removed_at: string | null;
  removed_by: number | null;
  removal_reason: string | null;
  created_at: string;
  updated_at: string;
  tracker: TrackerSummary;
  vehicle: VehicleSummary;
  customer: CustomerSummary;
  technician: TechnicianSummary | null;
};

export type InstallationListResponse = {
  items: Installation[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type InstallationPayload = {
  tracker_id: number;
  vehicle_id: number;
  installation_type: InstallationType;
  installed_by?: number | null;
  installation_notes?: string | null;
  checklist: InstallationChecklist;
  complete?: boolean;
};

export type InstallationQuery = {
  search?: string;
  status?: InstallationStatus;
  installation_type?: InstallationType;
  vehicle_id?: number;
  tracker_id?: number;
  customer_id?: number;
  active_only?: boolean;
  page?: number;
  page_size?: number;
  sort_by?: "installed_at" | "created_at" | "status" | "installation_type";
  sort_order?: "asc" | "desc";
};

function buildQuery(params: InstallationQuery): string {
  const query = new URLSearchParams();
  if (params.search) query.set("search", params.search);
  if (params.status) query.set("status", params.status);
  if (params.installation_type) query.set("installation_type", params.installation_type);
  if (params.vehicle_id) query.set("vehicle_id", String(params.vehicle_id));
  if (params.tracker_id) query.set("tracker_id", String(params.tracker_id));
  if (params.customer_id) query.set("customer_id", String(params.customer_id));
  if (params.active_only) query.set("active_only", "true");
  if (params.page) query.set("page", String(params.page));
  if (params.page_size) query.set("page_size", String(params.page_size));
  if (params.sort_by) query.set("sort_by", params.sort_by);
  if (params.sort_order) query.set("sort_order", params.sort_order);
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

export async function fetchInstallations(
  token: string,
  params: InstallationQuery = {},
): Promise<InstallationListResponse> {
  return apiRequest<InstallationListResponse>(`/installations${buildQuery(params)}`, { token });
}

export async function fetchInstallation(token: string, id: number): Promise<Installation> {
  return apiRequest<Installation>(`/installations/${id}`, { token });
}

export async function createInstallation(
  token: string,
  payload: InstallationPayload,
): Promise<Installation> {
  return apiRequest<Installation>("/installations", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function updateInstallation(
  token: string,
  id: number,
  payload: Partial<InstallationPayload> & {
    status?: InstallationStatus;
    removal_reason?: string | null;
  },
): Promise<Installation> {
  return apiRequest<Installation>(`/installations/${id}`, {
    method: "PUT",
    token,
    body: JSON.stringify(payload),
  });
}

export async function finishInstallation(
  token: string,
  id: number,
  installation_notes?: string | null,
): Promise<Installation> {
  return apiRequest<Installation>(`/installations/${id}/finish`, {
    method: "PATCH",
    token,
    body: JSON.stringify({ installation_notes: installation_notes ?? null }),
  });
}

export const INSTALLATION_TYPE_LABELS: Record<InstallationType, string> = {
  PRIMARY: "Principal",
  BAIT: "Isca",
  AUXILIARY: "Auxiliar",
};

export const INSTALLATION_STATUS_LABELS: Record<InstallationStatus, string> = {
  PENDING: "Pendente",
  IN_PROGRESS: "Em andamento",
  INSTALLED: "Instalado",
  REMOVED: "Removido",
  CANCELLED: "Cancelado",
};

export const CHECKLIST_LABELS: Record<keyof InstallationChecklist, string> = {
  power_connected: "Alimentação conectada",
  gps_ok: "GPS OK",
  gsm_ok: "GSM OK",
  ignition_ok: "Ignição OK",
  blocking_ok: "Bloqueio OK",
  test_drive_completed: "Teste de rodagem",
  customer_present: "Cliente presente",
};

export function installationTypeBadgeClass(type: InstallationType): string {
  const styles: Record<InstallationType, string> = {
    PRIMARY: "bg-emerald-500/15 text-emerald-300",
    BAIT: "bg-amber-500/15 text-amber-300",
    AUXILIARY: "bg-blue-500/15 text-blue-300",
  };
  return styles[type];
}

export function installationStatusBadgeClass(status: InstallationStatus): string {
  const styles: Record<InstallationStatus, string> = {
    PENDING: "bg-slate-500/20 text-slate-300",
    IN_PROGRESS: "bg-sky-500/15 text-sky-300",
    INSTALLED: "bg-emerald-500/15 text-emerald-300",
    REMOVED: "bg-orange-500/15 text-orange-300",
    CANCELLED: "bg-red-500/15 text-red-300",
  };
  return styles[status];
}

export function mapInstallationError(detail: string): string {
  const messages: Record<string, string> = {
    installation_not_found: "Instalação não encontrada",
    tracker_not_found: "Rastreador não encontrado",
    vehicle_not_found: "Veículo não encontrado",
    technician_not_found: "Técnico não encontrado",
    tracker_already_assigned: "Rastreador já possui instalação ativa em outro veículo",
    vehicle_primary_exists: "Este veículo já possui um rastreador principal ativo",
    tracker_not_installable: "Equipamento não pode ser instalado (perdido, danificado ou descartado)",
    installation_not_editable: "Instalação finalizada não pode ser editada",
    installation_cannot_finish: "Instalação não pode ser concluída neste status",
  };
  return messages[detail] ?? detail;
}

export function formatLastSeen(value: string | null): string {
  if (!value) return "Aguardando primeira conexão.";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Aguardando primeira conexão.";
  return date.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
