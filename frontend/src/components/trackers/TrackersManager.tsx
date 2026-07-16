"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  ArrowDownUp,
  Cpu,
  Filter,
  MoreHorizontal,
  Pencil,
  Plus,
  RadioTower,
  RefreshCw,
  Search,
  Signal,
  Sparkles,
  Trash2,
} from "lucide-react";

import {
  InstallationFormDrawer,
  type InstallationFormValues,
} from "@/components/installations/InstallationFormDrawer";
import {
  TrackerFormDrawer,
  type TrackerFormValues,
} from "@/components/trackers/TrackerFormDrawer";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/contexts/ToastContext";
import { ApiError } from "@/lib/api";
import { fetchCustomers, type Customer } from "@/lib/customers";
import {
  createInstallation,
  mapInstallationError,
} from "@/lib/installations";
import {
  createTracker,
  deleteTracker,
  fetchTrackers,
  formatRelativeCommunication,
  HEALTH_STATUS_LABELS,
  mapTrackerError,
  TRACKER_ORIGIN_LABELS,
  TRACKER_STATUS_LABELS,
  trackerDisplayName,
  updateTracker,
  updateTrackerStatus,
  type HealthStatus,
  type Tracker,
  type TrackerListResponse,
  type TrackerOrigin,
  type TrackerPayload,
  type TrackerStatus,
} from "@/lib/trackers";
import { fetchVehicles, type Vehicle } from "@/lib/vehicles";

type Filters = {
  status: TrackerStatus | "";
  origin: TrackerOrigin | "";
  health: HealthStatus | "";
  carrier: string;
  sort_by: "imei" | "model" | "status" | "created_at" | "last_seen_at";
  sort_order: "asc" | "desc";
};

const defaultFilters: Filters = {
  status: "",
  origin: "",
  health: "",
  carrier: "",
  sort_by: "created_at",
  sort_order: "desc",
};

export function TrackersManager() {
  const { accessToken, user } = useAuth();
  const { showToast } = useToast();

  const [data, setData] = useState<TrackerListResponse | null>(null);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchInput, setSearchInput] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [debouncedCarrier, setDebouncedCarrier] = useState("");
  const [page, setPage] = useState(1);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerMode, setDrawerMode] = useState<"create" | "edit">("create");
  const [selectedTracker, setSelectedTracker] = useState<Tracker | null>(null);
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);
  const [menuOpenId, setMenuOpenId] = useState<number | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Tracker | null>(null);
  const [statusTarget, setStatusTarget] = useState<Tracker | null>(null);
  const [nextStatus, setNextStatus] = useState<TrackerStatus>("IN_STOCK");
  const [installDrawerOpen, setInstallDrawerOpen] = useState(false);
  const [installTracker, setInstallTracker] = useState<Tracker | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearch(searchInput.trim());
      setPage(1);
    }, 300);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedCarrier(filters.carrier.trim());
      setPage(1);
    }, 300);
    return () => window.clearTimeout(timer);
  }, [filters.carrier]);

  const loadReferenceData = useCallback(async () => {
    if (!accessToken) return;
    try {
      const [customersResponse, vehiclesResponse] = await Promise.all([
        fetchCustomers(accessToken, { page: 1, page_size: 100, status: "ACTIVE" }),
        fetchVehicles(accessToken, { page: 1, page_size: 100 }),
      ]);
      setCustomers(customersResponse.items);
      setVehicles(vehiclesResponse.items);
    } catch {
      showToast("Erro ao carregar dados para instalação", "error");
    }
  }, [accessToken, showToast]);

  useEffect(() => {
    void loadReferenceData();
  }, [loadReferenceData]);

  const loadTrackers = useCallback(async () => {
    if (!accessToken) return;
    setLoading(true);
    try {
      const response = await fetchTrackers(accessToken, {
        search: debouncedSearch || undefined,
        status: filters.status || undefined,
        origin: filters.origin || undefined,
        health: filters.health || undefined,
        carrier: debouncedCarrier || undefined,
        page,
        page_size: 20,
        sort_by: filters.sort_by,
        sort_order: filters.sort_order,
      });
      setData(response);
    } catch (err) {
      showToast(
        err instanceof ApiError ? mapTrackerError(err.message) : "Erro ao carregar rastreadores",
        "error",
      );
    } finally {
      setLoading(false);
    }
  }, [
    accessToken,
    debouncedSearch,
    debouncedCarrier,
    filters.status,
    filters.origin,
    filters.health,
    filters.sort_by,
    filters.sort_order,
    page,
    showToast,
  ]);

  useEffect(() => {
    void loadTrackers();
  }, [loadTrackers]);

  function openInstall(tracker: Tracker) {
    setInstallTracker(tracker);
    setInstallDrawerOpen(true);
    setMenuOpenId(null);
  }

  async function handleInstallSave(values: InstallationFormValues) {
    if (!accessToken) return;
    try {
      await createInstallation(accessToken, values);
      showToast("Instalação registrada com sucesso");
      await loadTrackers();
    } catch (err) {
      const message =
        err instanceof ApiError ? mapInstallationError(err.message) : "Falha ao instalar rastreador";
      throw new Error(message);
    }
  }

  function openCreate() {
    setDrawerMode("create");
    setSelectedTracker(null);
    setDrawerOpen(true);
  }

  function openEdit(tracker: Tracker) {
    setDrawerMode("edit");
    setSelectedTracker(tracker);
    setDrawerOpen(true);
    setMenuOpenId(null);
  }

  function buildPayload(values: TrackerFormValues): TrackerPayload {
    return {
      imei: values.imei,
      model: values.model?.trim() || null,
      manufacturer: values.manufacturer?.trim() || null,
      firmware: values.firmware?.trim() || null,
      tracker_phone_number: values.tracker_phone_number?.trim() || null,
      sim_imei: values.sim_imei?.trim() || null,
      sim_iccid: values.sim_iccid?.trim() || null,
      carrier: values.carrier?.trim() || null,
      apn: values.apn?.trim() || null,
      serial_number: values.serial_number?.trim() || null,
      notes: values.notes?.trim() || null,
      origin: values.origin,
      status: values.status ?? null,
    };
  }

  async function handleSave(values: TrackerFormValues) {
    if (!accessToken) return;
    const payload = buildPayload(values);
    try {
      if (drawerMode === "create") {
        await createTracker(accessToken, payload);
        showToast("Rastreador cadastrado com sucesso");
      } else if (selectedTracker) {
        await updateTracker(accessToken, selectedTracker.id, payload);
        if (values.status && values.status !== selectedTracker.status) {
          await updateTrackerStatus(accessToken, selectedTracker.id, values.status);
        }
        showToast("Rastreador atualizado com sucesso");
      }
      await loadTrackers();
    } catch (err) {
      const message =
        err instanceof ApiError ? mapTrackerError(err.message) : "Falha ao salvar rastreador";
      throw new Error(message);
    }
  }

  async function confirmDelete() {
    if (!accessToken || !deleteTarget) return;
    try {
      await deleteTracker(accessToken, deleteTarget.id);
      showToast("Rastreador excluído com sucesso");
      setDeleteTarget(null);
      setMenuOpenId(null);
      await loadTrackers();
    } catch (err) {
      showToast(
        err instanceof ApiError ? mapTrackerError(err.message) : "Erro ao excluir rastreador",
        "error",
      );
    }
  }

  async function confirmStatusChange() {
    if (!accessToken || !statusTarget) return;
    try {
      await updateTrackerStatus(accessToken, statusTarget.id, nextStatus);
      showToast("Status atualizado com sucesso");
      setStatusTarget(null);
      setMenuOpenId(null);
      await loadTrackers();
    } catch (err) {
      showToast(
        err instanceof ApiError ? mapTrackerError(err.message) : "Erro ao alterar status",
        "error",
      );
    }
  }

  function openStatusDialog(tracker: Tracker) {
    setStatusTarget(tracker);
    setNextStatus(tracker.status);
    setMenuOpenId(null);
  }

  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Rastreadores</h1>
          <p className="text-surface-muted">Gerencie o estoque de equipamentos</p>
        </div>
        <button
          type="button"
          onClick={openCreate}
          className="hidden items-center justify-center gap-2 rounded-lg bg-brand px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-hover lg:inline-flex"
        >
          <Plus className="h-4 w-4" />
          Novo Rastreador
        </button>
      </div>

      {data && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          <StatCard title="Total" value={data.stats.total} icon={RadioTower} accent="text-brand" />
          <StatCard title="Em estoque" value={data.stats.in_stock} icon={Cpu} accent="text-blue-300" />
          <StatCard title="Instalados" value={data.stats.installed} icon={Signal} accent="text-emerald-300" />
          <StatCard title="Manutenção" value={data.stats.maintenance} icon={Activity} accent="text-amber-300" />
          <StatCard title="Bloqueados" value={data.stats.blocked} icon={Activity} accent="text-red-300" />
        </div>
      )}

      <div className="rounded-xl border border-surface-border bg-surface-card p-4">
        <div className="flex flex-col gap-3">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-surface-muted" />
            <input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Buscar por IMEI, modelo, fabricante, chip, ICCID, operadora ou firmware..."
              aria-label="Buscar rastreadores"
              className="w-full rounded-lg border border-surface-border bg-surface py-2.5 pl-10 pr-3 text-sm outline-none ring-brand focus:ring-2"
            />
          </div>

          <div className="hidden flex-wrap items-center gap-2 lg:flex">
            <FilterSelect
              label="Status"
              value={filters.status}
              onChange={(value) => {
                setFilters((current) => ({ ...current, status: value as TrackerStatus | "" }));
                setPage(1);
              }}
              options={[
                { value: "", label: "Todos os status" },
                ...Object.entries(TRACKER_STATUS_LABELS).map(([value, label]) => ({ value, label })),
              ]}
            />
            <FilterSelect
              label="Origem"
              value={filters.origin}
              onChange={(value) => {
                setFilters((current) => ({ ...current, origin: value as TrackerOrigin | "" }));
                setPage(1);
              }}
              options={[
                { value: "", label: "Todas as origens" },
                ...Object.entries(TRACKER_ORIGIN_LABELS).map(([value, label]) => ({ value, label })),
              ]}
            />
            <FilterSelect
              label="Health"
              value={filters.health}
              onChange={(value) => {
                setFilters((current) => ({ ...current, health: value as HealthStatus | "" }));
                setPage(1);
              }}
              options={[
                { value: "", label: "Todos os health" },
                ...Object.entries(HEALTH_STATUS_LABELS).map(([value, label]) => ({ value, label })),
              ]}
            />
            <label className="inline-flex items-center gap-2 text-sm text-surface-muted">
              <span>Operadora</span>
              <input
                value={filters.carrier}
                onChange={(e) => setFilters((current) => ({ ...current, carrier: e.target.value }))}
                placeholder="Todas"
                className="w-32 rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm text-slate-100 outline-none ring-brand focus:ring-2"
              />
            </label>
            <FilterSelect
              label="Ordenar por"
              value={filters.sort_by}
              onChange={(value) => {
                setFilters((current) => ({ ...current, sort_by: value as Filters["sort_by"] }));
                setPage(1);
              }}
              options={[
                { value: "created_at", label: "Data de cadastro" },
                { value: "imei", label: "IMEI" },
                { value: "model", label: "Modelo" },
                { value: "status", label: "Status" },
                { value: "last_seen_at", label: "Última comunicação" },
              ]}
            />
            <button
              type="button"
              onClick={() =>
                setFilters((current) => ({
                  ...current,
                  sort_order: current.sort_order === "asc" ? "desc" : "asc",
                }))
              }
              className="inline-flex items-center gap-2 rounded-lg border border-surface-border px-3 py-2 text-sm hover:bg-slate-700/30"
              aria-label="Alternar ordem"
            >
              <ArrowDownUp className="h-4 w-4" />
              {filters.sort_order === "asc" ? "Ascendente" : "Descendente"}
            </button>
          </div>

          <button
            type="button"
            onClick={() => setFilterDrawerOpen(true)}
            className="inline-flex items-center gap-2 rounded-lg border border-surface-border px-4 py-2.5 text-sm hover:bg-slate-700/30 lg:hidden"
          >
            <Filter className="h-4 w-4" />
            Filtros e ordenação
          </button>
        </div>
      </div>

      {loading ? (
        <TrackerListSkeleton />
      ) : items.length === 0 ? (
        <EmptyState onCreate={openCreate} />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map((tracker) => (
            <TrackerCard
              key={tracker.id}
              tracker={tracker}
              menuOpen={menuOpenId === tracker.id}
              onToggleMenu={() =>
                setMenuOpenId((current) => (current === tracker.id ? null : tracker.id))
              }
              onEdit={() => openEdit(tracker)}
              onStatus={() => openStatusDialog(tracker)}
              onDelete={() => {
                setDeleteTarget(tracker);
                setMenuOpenId(null);
              }}
              onInstall={() => openInstall(tracker)}
            />
          ))}
        </div>
      )}

      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-surface-muted">
            Página {data.page} de {data.total_pages} — {data.total} rastreadores
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((current) => current - 1)}
              className="rounded-lg border border-surface-border px-3 py-1.5 text-sm disabled:opacity-50"
            >
              Anterior
            </button>
            <button
              type="button"
              disabled={page >= data.total_pages}
              onClick={() => setPage((current) => current + 1)}
              className="rounded-lg border border-surface-border px-3 py-1.5 text-sm disabled:opacity-50"
            >
              Próxima
            </button>
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={openCreate}
        className="fixed bottom-6 right-6 z-40 inline-flex h-14 w-14 items-center justify-center rounded-full bg-brand text-white shadow-2xl hover:bg-brand-hover lg:hidden"
        aria-label="Novo rastreador"
      >
        <Plus className="h-6 w-6" />
      </button>

      <TrackerFormDrawer
        open={drawerOpen}
        mode={drawerMode}
        tracker={selectedTracker}
        onClose={() => setDrawerOpen(false)}
        onSubmit={handleSave}
      />

      {deleteTarget && (
        <ConfirmDialog
          title="Excluir rastreador"
          description={`Tem certeza que deseja excluir ${trackerDisplayName(deleteTarget)} (IMEI ${deleteTarget.imei})? Esta ação não pode ser desfeita.`}
          confirmLabel="Excluir"
          danger
          onCancel={() => setDeleteTarget(null)}
          onConfirm={() => void confirmDelete()}
        />
      )}

      {statusTarget && (
        <ConfirmDialog
          title="Alterar status"
          description={`Defina o novo status para ${trackerDisplayName(statusTarget)}.`}
          confirmLabel="Salvar status"
          onCancel={() => setStatusTarget(null)}
          onConfirm={() => void confirmStatusChange()}
        >
          <select
            value={nextStatus}
            onChange={(e) => setNextStatus(e.target.value as TrackerStatus)}
            className="mt-4 w-full rounded-lg border border-surface-border bg-surface px-3 py-2.5 text-sm outline-none ring-brand focus:ring-2"
          >
            {Object.entries(TRACKER_STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </ConfirmDialog>
      )}

      {filterDrawerOpen && (
        <MobileFilterDrawer
          filters={filters}
          onChange={setFilters}
          onApply={() => {
            setPage(1);
            setFilterDrawerOpen(false);
          }}
          onClose={() => setFilterDrawerOpen(false)}
        />
      )}

      {user && (
        <InstallationFormDrawer
          open={installDrawerOpen}
          customers={customers}
          vehicles={vehicles}
          trackers={data?.items ?? []}
          initialTrackerId={installTracker?.id}
          technicianId={user.id}
          technicianName={user.full_name}
          onClose={() => {
            setInstallDrawerOpen(false);
            setInstallTracker(null);
          }}
          onSubmit={handleInstallSave}
        />
      )}
    </div>
  );
}

function TrackerCard({
  tracker,
  menuOpen,
  onToggleMenu,
  onEdit,
  onStatus,
  onDelete,
  onInstall,
}: {
  tracker: Tracker;
  menuOpen: boolean;
  onToggleMenu: () => void;
  onEdit: () => void;
  onStatus: () => void;
  onDelete: () => void;
  onInstall: () => void;
}) {
  const canInstall = tracker.status === "IN_STOCK" || tracker.status === "PENDING_INSTALLATION";
  return (
    <article className="relative flex flex-col rounded-xl border border-surface-border bg-surface-card p-5 transition hover:border-brand/30">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand/10 text-brand">
            <RadioTower className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <h3 className="truncate text-base font-semibold">{tracker.model || "Sem modelo"}</h3>
            <p className="mt-0.5 font-mono text-xs text-surface-muted">IMEI {tracker.imei}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={onToggleMenu}
          className="rounded-lg p-2 hover:bg-slate-700/40"
          aria-label="Mais ações"
        >
          <MoreHorizontal className="h-4 w-4" />
        </button>
        {menuOpen && (
          <ActionMenu
            onEdit={onEdit}
            onStatus={onStatus}
            onDelete={onDelete}
            onInstall={onInstall}
            canInstall={canInstall}
          />
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <StatusBadge status={tracker.status} />
        <HealthBadge health={tracker.health_status} />
        <OriginBadge origin={tracker.origin} />
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        <Detail label="Fabricante" value={tracker.manufacturer} />
        <Detail label="Firmware" value={tracker.firmware} />
        <Detail label="Operadora" value={tracker.carrier} />
        <Detail label="Número do chip" value={tracker.tracker_phone_number} />
        <Detail
          label="Última comunicação"
          value={formatRelativeCommunication(tracker.last_seen_at)}
        />
        <Detail label="Protocolo" value={tracker.protocol} />
        <Detail label="Último IP" value={tracker.last_ip} />
        <Detail label="ICCID" value={tracker.sim_iccid} />
        {tracker.last_latitude != null && tracker.last_longitude != null && (
          <>
            <Detail
              label="Última posição"
              value={`${tracker.last_latitude.toFixed(6)}, ${tracker.last_longitude.toFixed(6)}`}
            />
            <Detail
              label="Velocidade"
              value={
                tracker.last_speed != null ? `${tracker.last_speed.toFixed(1)} km/h` : null
              }
            />
          </>
        )}
      </dl>

      <div className="mt-4 flex flex-wrap gap-2 border-t border-surface-border pt-3">
        {canInstall && (
          <button
            type="button"
            onClick={onInstall}
            className="rounded-lg border border-brand/40 bg-brand/10 px-3 py-1.5 text-xs text-brand hover:bg-brand/20"
          >
            Instalar
          </button>
        )}
        <button
          type="button"
          onClick={onEdit}
          className="rounded-lg border border-surface-border px-3 py-1.5 text-xs hover:bg-slate-700/30"
        >
          Editar
        </button>
        <button
          type="button"
          onClick={onStatus}
          className="rounded-lg border border-surface-border px-3 py-1.5 text-xs hover:bg-slate-700/30"
        >
          Alterar Status
        </button>
        <button
          type="button"
          onClick={onDelete}
          className="rounded-lg border border-red-500/30 px-3 py-1.5 text-xs text-red-300 hover:bg-red-500/10"
        >
          Excluir
        </button>
      </div>
    </article>
  );
}

function Detail({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-surface-muted">{label}</dt>
      <dd className="truncate">{value || "—"}</dd>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon: Icon,
  accent,
}: {
  title: string;
  value: number;
  icon: React.ElementType;
  accent: string;
}) {
  return (
    <div className="rounded-xl border border-surface-border bg-surface-card p-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-surface-muted">{title}</span>
        <Icon className={`h-4 w-4 ${accent}`} />
      </div>
      <p className="mt-2 text-2xl font-bold">{value}</p>
    </div>
  );
}

function StatusBadge({ status }: { status: TrackerStatus }) {
  const styles: Record<TrackerStatus, string> = {
    NEW: "bg-sky-500/15 text-sky-300",
    IN_STOCK: "bg-blue-500/15 text-blue-300",
    PENDING_INSTALLATION: "bg-amber-500/15 text-amber-300",
    INSTALLED: "bg-emerald-500/15 text-emerald-300",
    MAINTENANCE: "bg-orange-500/15 text-orange-300",
    BLOCKED: "bg-red-500/15 text-red-300",
    LOST: "bg-slate-500/20 text-slate-300",
    DAMAGED: "bg-rose-500/15 text-rose-300",
    DISPOSED: "bg-slate-500/20 text-slate-300",
  };
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${styles[status]}`}>
      {TRACKER_STATUS_LABELS[status]}
    </span>
  );
}

function HealthBadge({ health }: { health: HealthStatus }) {
  const styles: Record<HealthStatus, string> = {
    UNKNOWN: "bg-slate-500/20 text-slate-300",
    ONLINE: "bg-emerald-500/15 text-emerald-300",
    OFFLINE: "bg-red-500/15 text-red-300",
    HEALTHY: "bg-emerald-500/15 text-emerald-300",
    WARNING: "bg-amber-500/15 text-amber-300",
    ERROR: "bg-orange-500/15 text-orange-300",
    CRITICAL: "bg-red-500/15 text-red-300",
  };
  const icon =
    health === "ONLINE" ? "🟢" : health === "OFFLINE" ? "🔴" : null;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${styles[health]}`}>
      {icon ? <span aria-hidden>{icon}</span> : <Activity className="h-3 w-3" />}
      {HEALTH_STATUS_LABELS[health]}
    </span>
  );
}

function OriginBadge({ origin }: { origin: TrackerOrigin }) {
  const styles: Record<TrackerOrigin, string> = {
    MANUAL: "bg-slate-500/20 text-slate-300",
    AUTO_DISCOVERY: "bg-violet-500/15 text-violet-300",
    IMPORT: "bg-cyan-500/15 text-cyan-300",
  };
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${styles[origin]}`}>
      {origin === "AUTO_DISCOVERY" && <Sparkles className="h-3 w-3" />}
      {TRACKER_ORIGIN_LABELS[origin]}
    </span>
  );
}

function ActionMenu({
  onEdit,
  onStatus,
  onDelete,
  onInstall,
  canInstall,
}: {
  onEdit: () => void;
  onStatus: () => void;
  onDelete: () => void;
  onInstall: () => void;
  canInstall: boolean;
}) {
  return (
    <div className="absolute right-4 top-14 z-10 w-44 rounded-xl border border-surface-border bg-surface-card p-1 shadow-2xl">
      {canInstall && <MenuButton icon={RadioTower} label="Instalar" onClick={onInstall} />}
      <MenuButton icon={Pencil} label="Editar" onClick={onEdit} />
      <MenuButton icon={RefreshCw} label="Alterar Status" onClick={onStatus} />
      <MenuButton icon={Trash2} label="Excluir" onClick={onDelete} danger />
    </div>
  );
}

function MenuButton({
  icon: Icon,
  label,
  onClick,
  danger,
}: {
  icon: React.ElementType;
  label: string;
  onClick: () => void;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-700/40 ${
        danger ? "text-red-400" : ""
      }`}
    >
      <Icon className="h-4 w-4" />
      {label}
    </button>
  );
}

function TrackerListSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 6 }).map((_, index) => (
        <div
          key={index}
          className="animate-pulse rounded-xl border border-surface-border bg-surface-card p-5"
        >
          <div className="flex items-center gap-3">
            <div className="h-11 w-11 rounded-xl bg-slate-700/50" />
            <div className="flex-1 space-y-2">
              <div className="h-4 w-1/2 rounded bg-slate-700/50" />
              <div className="h-3 w-2/3 rounded bg-slate-700/40" />
            </div>
          </div>
          <div className="mt-4 space-y-2">
            <div className="h-3 w-full rounded bg-slate-700/40" />
            <div className="h-3 w-3/4 rounded bg-slate-700/40" />
          </div>
        </div>
      ))}
    </div>
  );
}

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="rounded-xl border border-dashed border-surface-border bg-surface-card px-6 py-14 text-center">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-brand/10 text-brand">
        <RadioTower className="h-7 w-7" />
      </div>
      <h3 className="mt-4 text-lg font-semibold">Nenhum rastreador encontrado</h3>
      <p className="mt-2 text-sm text-surface-muted">
        Cadastre o primeiro equipamento do estoque ou ajuste os filtros de busca.
      </p>
      <button
        type="button"
        onClick={onCreate}
        className="mt-6 inline-flex items-center gap-2 rounded-lg bg-brand px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-hover"
      >
        <Plus className="h-4 w-4" />
        Novo Rastreador
      </button>
    </div>
  );
}

function ConfirmDialog({
  title,
  description,
  confirmLabel,
  danger,
  onCancel,
  onConfirm,
  children,
}: {
  title: string;
  description: string;
  confirmLabel: string;
  danger?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  children?: React.ReactNode;
}) {
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onCancel();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onCancel]);

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onCancel}
        aria-label="Fechar diálogo"
      />
      <div
        role="dialog"
        aria-modal="true"
        className="relative w-full max-w-md rounded-2xl border border-surface-border bg-surface-card p-6 shadow-2xl"
      >
        <h3 className="text-lg font-semibold">{title}</h3>
        <p className="mt-2 text-sm text-surface-muted">{description}</p>
        {children}
        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 rounded-lg border border-surface-border px-4 py-2.5 text-sm hover:bg-slate-700/30"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className={`flex-1 rounded-lg px-4 py-2.5 text-sm font-medium text-white ${
              danger ? "bg-red-600 hover:bg-red-500" : "bg-brand hover:bg-brand-hover"
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
}) {
  return (
    <label className="inline-flex items-center gap-2 text-sm text-surface-muted">
      <span>{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm text-slate-100 outline-none ring-brand focus:ring-2"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function MobileFilterDrawer({
  filters,
  onChange,
  onApply,
  onClose,
}: {
  filters: Filters;
  onChange: (filters: Filters) => void;
  onApply: () => void;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 lg:hidden">
      <button type="button" className="absolute inset-0 bg-black/60" onClick={onClose} />
      <aside className="absolute bottom-0 left-0 right-0 max-h-[85vh] overflow-y-auto rounded-t-2xl border border-surface-border bg-surface-card p-5">
        <h3 className="text-lg font-semibold">Filtros e ordenação</h3>
        <div className="mt-4 space-y-4">
          <label className="block text-sm text-surface-muted">
            Status
            <select
              value={filters.status}
              onChange={(e) => onChange({ ...filters, status: e.target.value as TrackerStatus | "" })}
              className="mt-1 w-full rounded-lg border border-surface-border bg-surface px-3 py-2.5"
            >
              <option value="">Todos</option>
              {Object.entries(TRACKER_STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm text-surface-muted">
            Origem
            <select
              value={filters.origin}
              onChange={(e) => onChange({ ...filters, origin: e.target.value as TrackerOrigin | "" })}
              className="mt-1 w-full rounded-lg border border-surface-border bg-surface px-3 py-2.5"
            >
              <option value="">Todas</option>
              {Object.entries(TRACKER_ORIGIN_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm text-surface-muted">
            Health
            <select
              value={filters.health}
              onChange={(e) => onChange({ ...filters, health: e.target.value as HealthStatus | "" })}
              className="mt-1 w-full rounded-lg border border-surface-border bg-surface px-3 py-2.5"
            >
              <option value="">Todos</option>
              {Object.entries(HEALTH_STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm text-surface-muted">
            Operadora
            <input
              value={filters.carrier}
              onChange={(e) => onChange({ ...filters, carrier: e.target.value })}
              placeholder="Todas"
              className="mt-1 w-full rounded-lg border border-surface-border bg-surface px-3 py-2.5"
            />
          </label>
          <label className="block text-sm text-surface-muted">
            Ordenar por
            <select
              value={filters.sort_by}
              onChange={(e) => onChange({ ...filters, sort_by: e.target.value as Filters["sort_by"] })}
              className="mt-1 w-full rounded-lg border border-surface-border bg-surface px-3 py-2.5"
            >
              <option value="created_at">Data de cadastro</option>
              <option value="imei">IMEI</option>
              <option value="model">Modelo</option>
              <option value="status">Status</option>
              <option value="last_seen_at">Última comunicação</option>
            </select>
          </label>
          <label className="block text-sm text-surface-muted">
            Ordem
            <select
              value={filters.sort_order}
              onChange={(e) => onChange({ ...filters, sort_order: e.target.value as "asc" | "desc" })}
              className="mt-1 w-full rounded-lg border border-surface-border bg-surface px-3 py-2.5"
            >
              <option value="asc">Ascendente</option>
              <option value="desc">Descendente</option>
            </select>
          </label>
        </div>
        <button
          type="button"
          onClick={onApply}
          className="mt-5 w-full rounded-lg bg-brand py-2.5 text-sm font-medium text-white"
        >
          Aplicar filtros
        </button>
      </aside>
    </div>
  );
}

function formatDateTime(value: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
