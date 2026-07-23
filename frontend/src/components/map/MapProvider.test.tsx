import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { FleetMap } from "@/components/map/MapProvider";

vi.mock("@vis.gl/react-google-maps", () => ({
  APIProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Map: ({ children }: { children: React.ReactNode }) => <div data-testid="map-root">{children}</div>,
  AdvancedMarker: ({ children, onClick }: { children: React.ReactNode; onClick?: () => void }) => (
    <button type="button" data-testid="vehicle-marker" onClick={onClick}>
      {children}
    </button>
  ),
  InfoWindow: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  useAdvancedMarkerRef: () => [vi.fn(), null],
  useMap: () => null,
}));

describe("FleetMap markers", () => {
  it("renderiza um marcador por veículo com posição", () => {
    render(
      <FleetMap
        markers={[
          {
            id: 1,
            position: { lat: -21.1, lng: -47.8 },
            plate: "ABC1D23",
            customerName: "Cliente A",
            imei: "867111111111111",
            speed: 40,
            lastSeenAt: null,
            health: "ONLINE",
          },
          {
            id: 2,
            position: { lat: -22.0, lng: -48.0 },
            plate: "XYZ9Z99",
            customerName: "Cliente B",
            imei: "867222222222222",
            speed: 0,
            lastSeenAt: null,
            health: "OFFLINE",
          },
        ]}
        selectedVehicleId={null}
        onSelectVehicle={() => undefined}
      />,
    );

    expect(screen.getByTestId("map-root")).toBeInTheDocument();
    expect(screen.getAllByTestId("vehicle-marker")).toHaveLength(2);
  });
});
