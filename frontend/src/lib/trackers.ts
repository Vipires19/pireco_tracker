import { apiRequest } from "./api";

export type TrackerStatus =
  | "NEW"
  | "IN_STOCK"
  | "PENDING_INSTALLATION"
  | "INSTALLED"
  | "MAINTENANCE"
  | "BLOCKED"
  | "LOST"
  | "DAMAGED"
  | "DISPOSED";

export type HealthStatus =
  | "UNKNOWN"
  | "ONLINE"
  | "UNSTABLE"
  | "OFFLINE"
  | "HEALTHY"
  | "WARNING"
  | "ERROR"
  | "CRITICAL";

export type TrackerOrigin = "MANUAL" | "AUTO_DISCOVERY" | "IMPORT";

export type Tracker = {
  id: number;
  imei: string;
  model: string | null;
  manufacturer: string | null;
  firmware: string | null;
  tracker_phone_number: string | null;
  sim_iccid: string | null;
  sim_imei: string | null;
  carrier: string | null;
  apn: string | null;
  serial_number: string | null;
  notes: string | null;
  status: TrackerStatus;
  health_status: HealthStatus;
  origin: TrackerOrigin;
  last_seen_at: string | null;
  last_ip: string | null;
  protocol: string | null;
  last_latitude: number | null;
  last_longitude: number | null;
  last_speed: number | null;
  last_course: number | null;
  last_gps_time: string | null;
  created_at: string;
  updated_at: string;
};

export type TrackerStats = {
  total: number;
  in_stock: number;
  installed: number;
  maintenance: number;
  blocked: number;
};

export type TrackerListResponse = {
  items: Tracker[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  stats: TrackerStats;
};

export type TrackerPayload = {
  imei: string;
  model?: string | null;
  manufacturer?: string | null;
  firmware?: string | null;
  tracker_phone_number?: string | null;
  sim_iccid?: string | null;
  sim_imei?: string | null;
  carrier?: string | null;
  apn?: string | null;
  serial_number?: string | null;
  notes?: string | null;
  origin: TrackerOrigin;
  status?: TrackerStatus | null;
};

export type TrackerSortField = "imei" | "model" | "status" | "created_at" | "last_seen_at";

export type TrackerQuery = {
  search?: string;
  status?: TrackerStatus;
  origin?: TrackerOrigin;
  health?: HealthStatus;
  carrier?: string;
  page?: number;
  page_size?: number;
  sort_by?: TrackerSortField;
  sort_order?: "asc" | "desc";
};

function buildQuery(params: TrackerQuery): string {
  const query = new URLSearchParams();
  if (params.search) query.set("search", params.search);
  if (params.status) query.set("status", params.status);
  if (params.origin) query.set("origin", params.origin);
  if (params.health) query.set("health", params.health);
  if (params.carrier) query.set("carrier", params.carrier);
  if (params.page) query.set("page", String(params.page));
  if (params.page_size) query.set("page_size", String(params.page_size));
  if (params.sort_by) query.set("sort_by", params.sort_by);
  if (params.sort_order) query.set("sort_order", params.sort_order);
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

export async function fetchTrackers(
  token: string,
  params: TrackerQuery = {},
): Promise<TrackerListResponse> {
  return apiRequest<TrackerListResponse>(`/trackers${buildQuery(params)}`, { token });
}

export async function fetchTracker(token: string, id: number): Promise<Tracker> {
  return apiRequest<Tracker>(`/trackers/${id}`, { token });
}

export async function createTracker(token: string, payload: TrackerPayload): Promise<Tracker> {
  return apiRequest<Tracker>("/trackers", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function updateTracker(
  token: string,
  id: number,
  payload: TrackerPayload,
): Promise<Tracker> {
  return apiRequest<Tracker>(`/trackers/${id}`, {
    method: "PUT",
    token,
    body: JSON.stringify(payload),
  });
}

export async function updateTrackerStatus(
  token: string,
  id: number,
  status: TrackerStatus,
): Promise<Tracker> {
  return apiRequest<Tracker>(`/trackers/${id}/status`, {
    method: "PATCH",
    token,
    body: JSON.stringify({ status }),
  });
}

export async function deleteTracker(token: string, id: number): Promise<void> {
  await apiRequest<void>(`/trackers/${id}`, { method: "DELETE", token });
}

export const TRACKER_STATUS_LABELS: Record<TrackerStatus, string> = {
  NEW: "Novo",
  IN_STOCK: "Em estoque",
  PENDING_INSTALLATION: "Aguardando instalação",
  INSTALLED: "Instalado",
  MAINTENANCE: "Manutenção",
  BLOCKED: "Bloqueado",
  LOST: "Perdido",
  DAMAGED: "Danificado",
  DISPOSED: "Descartado",
};

export const HEALTH_STATUS_LABELS: Record<HealthStatus, string> = {
  UNKNOWN: "Desconhecido",
  ONLINE: "Online",
  UNSTABLE: "Instável",
  OFFLINE: "Offline",
  HEALTHY: "Saudável",
  WARNING: "Atenção",
  ERROR: "Erro",
  CRITICAL: "Crítico",
};

export function formatRelativeCommunication(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";

  const diffMs = Date.now() - date.getTime();
  if (diffMs < 0) return "agora";

  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 60) return seconds <= 1 ? "Há 1 segundo" : `Há ${seconds} segundos`;

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return minutes === 1 ? "Há 1 minuto" : `Há ${minutes} minutos`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return hours === 1 ? "Há 1 hora" : `Há ${hours} horas`;

  const days = Math.floor(hours / 24);
  return days === 1 ? "Há 1 dia" : `Há ${days} dias`;
}

export function formatProtocol(value: string | null): string {
  if (!value) return "Desconhecido";
  return value.replace(/_/g, " ").toUpperCase();
}

export function displayOrUnknown(value: string | null | undefined): string {
  const trimmed = value?.trim();
  return trimmed ? trimmed : "Desconhecido";
}

export const TRACKER_ORIGIN_LABELS: Record<TrackerOrigin, string> = {
  MANUAL: "Manual",
  AUTO_DISCOVERY: "Detectado Automaticamente",
  IMPORT: "Importação",
};

export function trackerDisplayName(tracker: Tracker): string {
  return tracker.model || tracker.manufacturer || `Rastreador ${tracker.imei}`;
}

export function mapTrackerError(detail: string): string {
  const messages: Record<string, string> = {
    imei_already_exists: "Já existe um rastreador com este IMEI",
    tracker_not_found: "Rastreador não encontrado",
    tracker_has_active_assignment: "Rastreador possui vínculo ativo e não pode ser excluído",
    tracker_status_install_forbidden:
      "Status Instalado é definido automaticamente pela instalação",
    invalid_imei: "IMEI inválido (15 dígitos)",
    invalid_iccid: "ICCID inválido",
    invalid_sim_imei: "IMEI do chip inválido",
    invalid_tracker_phone: "Número do chip inválido",
    invalid_firmware: "Firmware inválido",
    invalid_model: "Modelo inválido",
    invalid_manufacturer: "Fabricante inválido",
    invalid_serial_number: "Número de série inválido",
  };
  return messages[detail] ?? detail;
}
