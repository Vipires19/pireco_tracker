import { describe, expect, it } from "vitest";

import { toMapMarkers } from "@/hooks/useMonitoringVehicles";
import type { MonitoringVehicle } from "@/lib/monitoring";

describe("toMapMarkers", () => {
  it("renderiza apenas veículos com coordenadas válidas", () => {
    const vehicles: MonitoringVehicle[] = [
      {
        vehicle_id: 1,
        plate: "AAA1A11",
        model: "Onix",
        customer_name: "Cliente A",
        tracker_id: 1,
        tracker_imei: "867111111111111",
        health: "ONLINE",
        latitude: -21.1,
        longitude: -47.8,
        speed: 30,
        course: 10,
        last_seen_at: null,
        gps_time: null,
      },
      {
        vehicle_id: 2,
        plate: "BBB2B22",
        model: "HB20",
        customer_name: "Cliente B",
        tracker_id: 2,
        tracker_imei: "867222222222222",
        health: "UNKNOWN",
        latitude: null,
        longitude: null,
        speed: null,
        course: null,
        last_seen_at: null,
        gps_time: null,
      },
    ];

    const markers = toMapMarkers(vehicles);
    expect(markers).toHaveLength(1);
    expect(markers[0]).toMatchObject({
      id: 1,
      plate: "AAA1A11",
      position: { lat: -21.1, lng: -47.8 },
      health: "ONLINE",
    });
  });
});
