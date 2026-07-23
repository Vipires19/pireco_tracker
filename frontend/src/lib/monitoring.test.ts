import { describe, expect, it } from "vitest";

import { filterMonitoringVehicles } from "@/lib/monitoring";
import type { MonitoringVehicle } from "@/lib/monitoring";

const sampleVehicles: MonitoringVehicle[] = [
  {
    vehicle_id: 1,
    plate: "ABC1D23",
    model: "Onix",
    customer_name: "João Silva",
    tracker_id: 10,
    tracker_imei: "867123456789012",
    health: "ONLINE",
    latitude: -21.1,
    longitude: -47.8,
    speed: 40,
    course: 90,
    last_seen_at: "2026-07-16T12:00:00Z",
    gps_time: "2026-07-16T12:00:00Z",
  },
  {
    vehicle_id: 2,
    plate: "XYZ9Z99",
    model: "HB20",
    customer_name: "Maria Souza",
    tracker_id: 11,
    tracker_imei: "867987654321098",
    health: "OFFLINE",
    latitude: -22.0,
    longitude: -48.0,
    speed: 0,
    course: 0,
    last_seen_at: "2026-07-16T10:00:00Z",
    gps_time: "2026-07-16T10:00:00Z",
  },
];

describe("filterMonitoringVehicles", () => {
  it("filtra por placa", () => {
    const result = filterMonitoringVehicles(sampleVehicles, "abc1");
    expect(result).toHaveLength(1);
    expect(result[0].vehicle_id).toBe(1);
  });

  it("filtra por cliente", () => {
    const result = filterMonitoringVehicles(sampleVehicles, "maria");
    expect(result).toHaveLength(1);
    expect(result[0].vehicle_id).toBe(2);
  });

  it("filtra por IMEI", () => {
    const result = filterMonitoringVehicles(sampleVehicles, "867987654");
    expect(result).toHaveLength(1);
    expect(result[0].tracker_imei).toBe("867987654321098");
  });
});
