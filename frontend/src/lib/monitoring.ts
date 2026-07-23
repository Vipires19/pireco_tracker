import { apiRequest } from "./api";
import type { HealthStatus } from "./trackers";

export type MonitoringVehicle = {
  vehicle_id: number;
  plate: string;
  model: string | null;
  customer_name: string;
  tracker_id: number;
  tracker_imei: string;
  health: HealthStatus;
  latitude: number | null;
  longitude: number | null;
  speed: number | null;
  course: number | null;
  last_seen_at: string | null;
  gps_time: string | null;
};

export type MonitoringVehicleDetail = {
  customer: { id: number; full_name: string };
  vehicle: {
    id: number;
    plate: string;
    model: string | null;
    brand: string | null;
    nickname: string | null;
  };
  tracker: {
    id: number;
    imei: string;
    model: string | null;
    last_seen_at: string | null;
    last_latitude: number | null;
    last_longitude: number | null;
    last_speed: number | null;
    last_course: number | null;
    last_gps_time: string | null;
  };
  health: HealthStatus;
  last_seen_at: string | null;
  latitude: number | null;
  longitude: number | null;
  speed: number | null;
  course: number | null;
  gps_time: string | null;
};

export async function fetchMonitoringVehicles(token: string): Promise<MonitoringVehicle[]> {
  return apiRequest<MonitoringVehicle[]>("/monitoring/vehicles", { token });
}

export async function fetchMonitoringVehicle(
  token: string,
  vehicleId: number,
): Promise<MonitoringVehicleDetail> {
  return apiRequest<MonitoringVehicleDetail>(`/monitoring/vehicles/${vehicleId}`, { token });
}

export const MONITORING_POLL_INTERVAL_MS = 15_000;

export function filterMonitoringVehicles(
  vehicles: MonitoringVehicle[],
  search: string,
): MonitoringVehicle[] {
  const term = search.trim().toLowerCase();
  if (!term) return vehicles;
  return vehicles.filter((vehicle) => {
    const digits = term.replace(/\D/g, "");
    return (
      vehicle.customer_name.toLowerCase().includes(term) ||
      vehicle.plate.toLowerCase().includes(term) ||
      vehicle.tracker_imei.toLowerCase().includes(term) ||
      (digits.length > 0 && vehicle.tracker_imei.includes(digits))
    );
  });
}
