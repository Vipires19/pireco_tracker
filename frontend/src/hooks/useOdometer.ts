import { useCallback, useState } from "react";

/**
 * Hook preparatório para odômetro automático (próxima sprint).
 * Por enquanto expõe apenas estado local e um placeholder de recálculo.
 */
export function useOdometer(vehicleId: number | null) {
  const [odometerKm, setOdometerKm] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const recalculate = useCallback(async () => {
    if (vehicleId == null) return;
    setLoading(true);
    setError(null);
    try {
      // Endpoint de recálculo será exposto na próxima sprint.
      setError("Recálculo automático de odômetro ainda não disponível");
    } finally {
      setLoading(false);
    }
  }, [vehicleId]);

  return { odometerKm, setOdometerKm, loading, error, recalculate };
}
