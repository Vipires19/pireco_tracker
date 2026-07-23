import type { HealthStatus } from "@/lib/trackers";
import { HEALTH_STATUS_LABELS } from "@/lib/trackers";

export const HEALTH_MARKER_COLORS: Record<HealthStatus, string> = {
  ONLINE: "#22c55e",
  UNSTABLE: "#eab308",
  OFFLINE: "#ef4444",
  UNKNOWN: "#64748b",
  HEALTHY: "#22c55e",
  WARNING: "#eab308",
  ERROR: "#f97316",
  CRITICAL: "#ef4444",
};

export const HEALTH_BADGE_STYLES: Record<HealthStatus, string> = {
  UNKNOWN: "bg-slate-500/20 text-slate-300",
  ONLINE: "bg-emerald-500/15 text-emerald-300",
  UNSTABLE: "bg-amber-500/15 text-amber-300",
  OFFLINE: "bg-red-500/15 text-red-300",
  HEALTHY: "bg-emerald-500/15 text-emerald-300",
  WARNING: "bg-amber-500/15 text-amber-300",
  ERROR: "bg-orange-500/15 text-orange-300",
  CRITICAL: "bg-red-500/15 text-red-300",
};

export function healthStatusIcon(health: HealthStatus): string | null {
  if (health === "ONLINE") return "🟢";
  if (health === "UNSTABLE") return "🟡";
  if (health === "OFFLINE") return "🔴";
  if (health === "UNKNOWN") return "⚫";
  return null;
}

export { HEALTH_STATUS_LABELS };
