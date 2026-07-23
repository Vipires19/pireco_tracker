"use client";

import clsx from "clsx";
import { Search } from "lucide-react";
import { useMemo, useState } from "react";

import { FleetMap, MapProvider } from "@/components/map";
import { useAuth } from "@/contexts/AuthContext";
import { toMapMarkers, useMonitoringVehicles } from "@/hooks/useMonitoringVehicles";
import {
  HEALTH_BADGE_STYLES,
  HEALTH_STATUS_LABELS,
  healthStatusIcon,
} from "@/lib/health";
import { filterMonitoringVehicles } from "@/lib/monitoring";
import { formatRelativeCommunication } from "@/lib/trackers";

const mapsApiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY ?? "";

export function MonitoringCenter() {
  const { token } = useAuth();
  const { data: vehicles = [], isLoading, isError, error, dataUpdatedAt } = useMonitoringVehicles();
  const [search, setSearch] = useState("");
  const [selectedVehicleId, setSelectedVehicleId] = useState<number | null>(null);

  const filteredVehicles = useMemo(
    () => filterMonitoringVehicles(vehicles, search),
    [vehicles, search],
  );

  const mapMarkers = useMemo(() => toMapMarkers(filteredVehicles), [filteredVehicles]);

  if (!token) return null;

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Monitoramento</h1>
          <p className="text-sm text-surface-muted">
            Centro de operações — frota em tempo real via polling de 15 segundos.
          </p>
        </div>
        <p className="text-xs text-surface-muted">
          Última atualização:{" "}
          {dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString("pt-BR") : "—"}
        </p>
      </div>

      <div className="grid h-[calc(100vh-11rem)] min-h-[560px] grid-cols-1 gap-4 lg:grid-cols-[360px_minmax(0,1fr)]">
        <section className="flex min-h-0 flex-col rounded-xl border border-surface-border bg-surface-card">
          <div className="border-b border-surface-border p-4">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-surface-muted" />
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Buscar por cliente, placa ou IMEI"
                className="w-full rounded-lg border border-surface-border bg-surface py-2 pl-9 pr-3 text-sm outline-none ring-brand/40 focus:ring-2"
              />
            </div>
            <p className="mt-2 text-xs text-surface-muted">
              {filteredVehicles.length} veículo(s) • {mapMarkers.length} no mapa
            </p>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto p-2">
            {isLoading && (
              <div className="space-y-2 p-2">
                {Array.from({ length: 6 }).map((_, index) => (
                  <div
                    key={index}
                    className="h-20 animate-pulse rounded-lg bg-slate-700/30"
                  />
                ))}
              </div>
            )}

            {isError && (
              <div className="p-4 text-sm text-red-300">
                Falha ao carregar veículos: {(error as Error).message}
              </div>
            )}

            {!isLoading && !isError && filteredVehicles.length === 0 && (
              <div className="p-4 text-sm text-surface-muted">
                Nenhum veículo instalado encontrado para o filtro atual.
              </div>
            )}

            {!isLoading &&
              filteredVehicles.map((vehicle) => (
                <button
                  key={vehicle.vehicle_id}
                  type="button"
                  onClick={() => setSelectedVehicleId(vehicle.vehicle_id)}
                  className={clsx(
                    "mb-2 w-full rounded-lg border p-3 text-left transition-colors",
                    selectedVehicleId === vehicle.vehicle_id
                      ? "border-brand bg-brand/10"
                      : "border-transparent bg-slate-800/30 hover:bg-slate-700/40",
                  )}
                >
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <span className="font-medium">{vehicle.plate}</span>
                    <HealthBadge health={vehicle.health} />
                  </div>
                  <p className="text-sm text-slate-300">{vehicle.customer_name}</p>
                  <p className="text-xs text-surface-muted">{vehicle.model ?? "Modelo não informado"}</p>
                  <div className="mt-2 flex items-center justify-between text-xs text-surface-muted">
                    <span>
                      {vehicle.speed != null ? `${Math.round(vehicle.speed)} km/h` : "Sem velocidade"}
                    </span>
                    <span>{formatRelativeCommunication(vehicle.last_seen_at)}</span>
                  </div>
                </button>
              ))}
          </div>
        </section>

        <section className="min-h-[320px] overflow-hidden rounded-xl border border-surface-border bg-surface-card">
          <MapProvider apiKey={mapsApiKey}>
            <div className="h-full w-full">
              <FleetMap
                markers={mapMarkers}
                selectedVehicleId={selectedVehicleId}
                onSelectVehicle={setSelectedVehicleId}
              />
            </div>
          </MapProvider>
        </section>
      </div>
    </div>
  );
}

function HealthBadge({ health }: { health: Parameters<typeof healthStatusIcon>[0] }) {
  const icon = healthStatusIcon(health);
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
        HEALTH_BADGE_STYLES[health],
      )}
    >
      {icon && <span aria-hidden>{icon}</span>}
      {HEALTH_STATUS_LABELS[health]}
    </span>
  );
}
