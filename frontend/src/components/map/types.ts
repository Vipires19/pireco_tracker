import type { ReactNode } from "react";

import type { HealthStatus } from "@/lib/trackers";

export type MapPosition = {
  lat: number;
  lng: number;
};

export type MapVehicleMarker = {
  id: number;
  position: MapPosition;
  plate: string;
  customerName: string;
  imei: string;
  speed: number | null;
  lastSeenAt: string | null;
  health: HealthStatus;
};

export type MapProviderProps = {
  apiKey: string;
  children: ReactNode;
};

export type FleetMapProps = {
  markers: MapVehicleMarker[];
  selectedVehicleId: number | null;
  onSelectVehicle: (vehicleId: number) => void;
  defaultCenter?: MapPosition;
  defaultZoom?: number;
};
