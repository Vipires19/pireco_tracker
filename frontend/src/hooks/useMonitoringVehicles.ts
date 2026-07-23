"use client";

import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/contexts/AuthContext";
import {
  fetchMonitoringVehicles,
  MONITORING_POLL_INTERVAL_MS,
  type MonitoringVehicle,
} from "@/lib/monitoring";

export const monitoringVehiclesQueryKey = ["monitoring", "vehicles"] as const;

export function useMonitoringVehicles() {
  const { token } = useAuth();

  return useQuery({
    queryKey: monitoringVehiclesQueryKey,
    queryFn: () => fetchMonitoringVehicles(token!),
    enabled: Boolean(token),
    refetchInterval: MONITORING_POLL_INTERVAL_MS,
    refetchIntervalInBackground: true,
  });
}

export function toMapMarkers(vehicles: MonitoringVehicle[]) {
  return vehicles
    .filter(
      (vehicle) =>
        vehicle.latitude != null &&
        vehicle.longitude != null &&
        Number.isFinite(vehicle.latitude) &&
        Number.isFinite(vehicle.longitude),
    )
    .map((vehicle) => ({
      id: vehicle.vehicle_id,
      position: { lat: vehicle.latitude!, lng: vehicle.longitude! },
      plate: vehicle.plate,
      customerName: vehicle.customer_name,
      imei: vehicle.tracker_imei,
      speed: vehicle.speed,
      lastSeenAt: vehicle.last_seen_at,
      health: vehicle.health,
    }));
}
