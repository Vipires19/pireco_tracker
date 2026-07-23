import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useMonitoringVehicles, monitoringVehiclesQueryKey } from "@/hooks/useMonitoringVehicles";
import { MONITORING_POLL_INTERVAL_MS } from "@/lib/monitoring";

const fetchMonitoringVehicles = vi.fn();

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({ token: "test-token" }),
}));

vi.mock("@/lib/monitoring", async () => {
  const actual = await vi.importActual<typeof import("@/lib/monitoring")>("@/lib/monitoring");
  return {
    ...actual,
    fetchMonitoringVehicles: (...args: unknown[]) => fetchMonitoringVehicles(...args),
  };
});


describe("useMonitoringVehicles polling", () => {
  beforeEach(() => {
    fetchMonitoringVehicles.mockReset();
    fetchMonitoringVehicles.mockResolvedValue([]);
  });

  it("configura polling de 15 segundos", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useMonitoringVehicles(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMonitoringVehicles).toHaveBeenCalledWith("test-token");

    const cached = client.getQueryCache().find({ queryKey: monitoringVehiclesQueryKey });
    expect(cached?.options.refetchInterval).toBe(MONITORING_POLL_INTERVAL_MS);
  });
});
