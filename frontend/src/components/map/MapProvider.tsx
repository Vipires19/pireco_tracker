"use client";

import {
  AdvancedMarker,
  APIProvider,
  InfoWindow,
  Map,
  useAdvancedMarkerRef,
  useMap,
} from "@vis.gl/react-google-maps";
import { useCallback, useEffect, useMemo, useState } from "react";

import { HEALTH_MARKER_COLORS, HEALTH_STATUS_LABELS } from "@/lib/health";
import { formatRelativeCommunication } from "@/lib/trackers";

import type { FleetMapProps, MapPosition, MapProviderProps } from "./types";

const DEFAULT_CENTER: MapPosition = { lat: -21.177, lng: -47.810 };
const DEFAULT_ZOOM = 6;

export function MapProvider({ apiKey, children }: MapProviderProps) {
  if (!apiKey) {
    return (
      <div className="flex h-full items-center justify-center rounded-xl border border-dashed border-surface-border bg-surface-card p-6 text-center text-sm text-surface-muted">
        Configure <code className="mx-1">NEXT_PUBLIC_GOOGLE_MAPS_API_KEY</code> para exibir o mapa.
      </div>
    );
  }

  return <APIProvider apiKey={apiKey}>{children}</APIProvider>;
}

function MapCenterController({
  selectedVehicleId,
  markers,
}: {
  selectedVehicleId: number | null;
  markers: FleetMapProps["markers"];
}) {
  const map = useMap();

  useEffect(() => {
    if (!map || selectedVehicleId == null) return;
    const marker = markers.find((item) => item.id === selectedVehicleId);
    if (!marker) return;
    map.panTo(marker.position);
    map.setZoom(15);
  }, [map, markers, selectedVehicleId]);

  return null;
}

function VehicleMarker({
  marker,
  isSelected,
  onSelect,
}: {
  marker: FleetMapProps["markers"][number];
  isSelected: boolean;
  onSelect: (vehicleId: number) => void;
}) {
  const [markerRef, advancedMarker] = useAdvancedMarkerRef();
  const [infoOpen, setInfoOpen] = useState(false);

  const handleClick = useCallback(() => {
    onSelect(marker.id);
    setInfoOpen(true);
  }, [marker.id, onSelect]);

  const handleClose = useCallback(() => setInfoOpen(false), []);

  const color = HEALTH_MARKER_COLORS[marker.health];

  return (
    <>
      <AdvancedMarker
        ref={markerRef}
        position={marker.position}
        onClick={handleClick}
        zIndex={isSelected ? 2 : 1}
      >
        <div
          className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-white shadow-lg"
          style={{ backgroundColor: color }}
          title={marker.plate}
        />
      </AdvancedMarker>

      {infoOpen && advancedMarker && (
        <InfoWindow anchor={advancedMarker} onClose={handleClose}>
          <div className="min-w-[200px] space-y-1 text-sm text-slate-800">
            <p className="font-semibold">{marker.plate}</p>
            <p>{marker.customerName}</p>
            <p>IMEI: {marker.imei}</p>
            <p>Velocidade: {marker.speed != null ? `${Math.round(marker.speed)} km/h` : "—"}</p>
            <p>Última comunicação: {formatRelativeCommunication(marker.lastSeenAt)}</p>
            <p>Health: {HEALTH_STATUS_LABELS[marker.health]}</p>
          </div>
        </InfoWindow>
      )}
    </>
  );
}

export function FleetMap({
  markers,
  selectedVehicleId,
  onSelectVehicle,
  defaultCenter = DEFAULT_CENTER,
  defaultZoom = DEFAULT_ZOOM,
}: FleetMapProps) {
  const mapCenter = useMemo(() => {
    if (markers.length === 0) return defaultCenter;
    const lat = markers.reduce((sum, item) => sum + item.position.lat, 0) / markers.length;
    const lng = markers.reduce((sum, item) => sum + item.position.lng, 0) / markers.length;
    return { lat, lng };
  }, [defaultCenter, markers]);

  return (
    <Map
      defaultCenter={mapCenter}
      defaultZoom={defaultZoom}
      mapId={process.env.NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID}
      gestureHandling="greedy"
      disableDefaultUI={false}
      className="h-full w-full rounded-xl"
    >
      <MapCenterController selectedVehicleId={selectedVehicleId} markers={markers} />
      {markers.map((marker) => (
        <VehicleMarker
          key={marker.id}
          marker={marker}
          isSelected={marker.id === selectedVehicleId}
          onSelect={onSelectVehicle}
        />
      ))}
    </Map>
  );
}
