"use client";

import { useCallback, useEffect, useState } from "react";
import { Filter, Plus, RadioTower, Search, Wrench } from "lucide-react";

import {
  InstallationFormDrawer,
  type InstallationFormValues,
} from "@/components/installations/InstallationFormDrawer";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/contexts/ToastContext";
import { ApiError } from "@/lib/api";
import { fetchCustomers, type Customer } from "@/lib/customers";
import {
  createInstallation,
  fetchInstallations,
  formatLastSeen,
  INSTALLATION_STATUS_LABELS,
  INSTALLATION_TYPE_LABELS,
  installationStatusBadgeClass,
  installationTypeBadgeClass,
  mapInstallationError,
  type Installation,
  type InstallationListResponse,
  type InstallationStatus,
  type InstallationType,
} from "@/lib/installations";
import { fetchTrackers, type Tracker } from "@/lib/trackers";
import { fetchVehicles, type Vehicle } from "@/lib/vehicles";

type Filters = {
  status: InstallationStatus | "";
  installation_type: InstallationType | "";
};

const defaultFilters: Filters = {
  status: "",
  installation_type: "",
};

export function InstallationsManager() {
  const { accessToken, user } = useAuth();
  const { showToast } = useToast();

  const [data, setData] = useState<InstallationListResponse | null>(null);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [trackers, setTrackers] = useState<Tracker[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchInput, setSearchInput] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [page, setPage] = useState(1);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearch(searchInput.trim());
      setPage(1);
    }, 300);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  const loadReferenceData = useCallback(async () => {
    if (!accessToken) return;
    try {
      const [customersResponse, vehiclesResponse, trackersResponse] = await Promise.all([
        fetchCustomers(accessToken, { page: 1, page_size: 100, status: "ACTIVE" }),
        fetchVehicles(accessToken, { page: 1, page_size: 100 }),
        fetchTrackers(accessToken, { page: 1, page_size: 100 }),
      ]);
      setCustomers(customersResponse.items);
      setVehicles(vehiclesResponse.items);
      setTrackers(trackersResponse.items);
    } catch {
      showToast("Erro ao carregar dados de referência", "error");
    }
  }, [accessToken, showToast]);

  const loadInstallations = useCallback(async () => {
    if (!accessToken) return;
    setLoading(true);
    try {
      const response = await fetchInstallations(accessToken, {
        search: debouncedSearch || undefined,
        status: filters.status || undefined,
        installation_type: filters.installation_type || undefined,
        page,
        page_size: 20,
        sort_by: "installed_at",
        sort_order: "desc",
      });
      setData(response);
    } catch (err) {
      showToast(
        err instanceof ApiError ? mapInstallationError(err.message) : "Erro ao carregar instalações",
        "error",
      );
    } finally {
      setLoading(false);
    }
  }, [accessToken, debouncedSearch, filters, page, showToast]);

  useEffect(() => {
    void loadReferenceData();
  }, [loadReferenceData]);

  useEffect(() => {
    void loadInstallations();
  }, [loadInstallations]);

  async function handleSave(values: InstallationFormValues) {
    if (!accessToken) return;
    try {
      await createInstallation(accessToken, values);
      showToast("Instalação registrada com sucesso");
      await loadInstallations();
      await loadReferenceData();
    } catch (err) {
      const message =
        err instanceof ApiError ? mapInstallationError(err.message) : "Falha ao salvar instalação";
      throw new Error(message);
    }
  }

  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Instalações</h1>
          <p className="text-surface-muted">Gerencie o processo operacional de instalação</p>
        </div>
        <button
          type="button"
          onClick={() => setDrawerOpen(true)}
          className="hidden items-center justify-center gap-2 rounded-lg bg-brand px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-hover lg:inline-flex"
        >
          <Plus className="h-4 w-4" />
          Nova Instalação
        </button>
      </div>

      <div className="rounded-xl border border-surface-border bg-surface-card p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-surface-muted" />
            <input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Buscar por veículo, cliente, IMEI ou modelo..."
              className="w-full rounded-lg border border-surface-border bg-surface py-2.5 pl-10 pr-3 text-sm outline-none ring-brand focus:ring-2"
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <FilterSelect
              label="Status"
              value={filters.status}
              onChange={(value) => {
                setFilters((current) => ({ ...current, status: value as InstallationStatus | "" }));
                setPage(1);
              }}
              options={[
                { value: "", label: "Todos" },
                ...Object.entries(INSTALLATION_STATUS_LABELS).map(([value, label]) => ({
                  value,
                  label,
                })),
              ]}
            />
            <FilterSelect
              label="Tipo"
              value={filters.installation_type}
              onChange={(value) => {
                setFilters((current) => ({
                  ...current,
                  installation_type: value as InstallationType | "",
                }));
                setPage(1);
              }}
              options={[
                { value: "", label: "Todos" },
                ...Object.entries(INSTALLATION_TYPE_LABELS).map(([value, label]) => ({
                  value,
                  label,
                })),
              ]}
            />
          </div>
        </div>
      </div>

      {loading ? (
        <InstallationListSkeleton />
      ) : items.length === 0 ? (
        <EmptyState onCreate={() => setDrawerOpen(true)} />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map((installation) => (
            <InstallationCard key={installation.id} installation={installation} />
          ))}
        </div>
      )}

      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-surface-muted">
            Página {data.page} de {data.total_pages} — {data.total} instalações
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
        onClick={() => setDrawerOpen(true)}
        className="fixed bottom-6 right-6 z-40 inline-flex h-14 w-14 items-center justify-center rounded-full bg-brand text-white shadow-2xl hover:bg-brand-hover lg:hidden"
        aria-label="Nova instalação"
      >
        <Plus className="h-6 w-6" />
      </button>

      {user && (
        <InstallationFormDrawer
          open={drawerOpen}
          customers={customers}
          vehicles={vehicles}
          trackers={trackers}
          technicianId={user.id}
          technicianName={user.full_name}
          onClose={() => setDrawerOpen(false)}
          onSubmit={handleSave}
        />
      )}
    </div>
  );
}

function InstallationCard({ installation }: { installation: Installation }) {
  return (
    <article className="rounded-xl border border-surface-border bg-surface-card p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold">
            {installation.vehicle.plate}
            {installation.vehicle.nickname ? ` — ${installation.vehicle.nickname}` : ""}
          </h3>
          <p className="mt-1 text-sm text-surface-muted">{installation.customer.full_name}</p>
        </div>
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-medium ${installationStatusBadgeClass(installation.status)}`}
        >
          {INSTALLATION_STATUS_LABELS[installation.status]}
        </span>
      </div>

      <dl className="mt-4 space-y-2 text-sm">
        <div className="flex items-center justify-between gap-3">
          <dt className="text-surface-muted">Rastreador</dt>
          <dd className="text-right font-mono text-xs">{installation.tracker.imei}</dd>
        </div>
        <div className="flex items-center justify-between gap-3">
          <dt className="text-surface-muted">Modelo</dt>
          <dd>{installation.tracker.model || "—"}</dd>
        </div>
        <div className="flex items-center justify-between gap-3">
          <dt className="text-surface-muted">Tipo</dt>
          <dd>
            <span
              className={`rounded-full px-2.5 py-1 text-xs font-medium ${installationTypeBadgeClass(installation.installation_type)}`}
            >
              {INSTALLATION_TYPE_LABELS[installation.installation_type]}
            </span>
          </dd>
        </div>
        <div className="flex items-center justify-between gap-3">
          <dt className="text-surface-muted">Técnico</dt>
          <dd>{installation.technician?.full_name ?? "—"}</dd>
        </div>
        <div className="flex items-center justify-between gap-3">
          <dt className="text-surface-muted">Data</dt>
          <dd>{new Date(installation.installed_at).toLocaleString("pt-BR")}</dd>
        </div>
        <div className="flex items-center justify-between gap-3">
          <dt className="text-surface-muted">Última comunicação</dt>
          <dd className="text-right text-xs">{formatLastSeen(installation.tracker.last_seen_at)}</dd>
        </div>
      </dl>
    </article>
  );
}

function InstallationListSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 6 }).map((_, index) => (
        <div
          key={index}
          className="animate-pulse rounded-xl border border-surface-border bg-surface-card p-5"
        >
          <div className="h-4 w-1/2 rounded bg-slate-700/50" />
          <div className="mt-3 h-3 w-2/3 rounded bg-slate-700/40" />
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
        <Wrench className="h-7 w-7" />
      </div>
      <h3 className="mt-4 text-lg font-semibold">Nenhuma instalação encontrada</h3>
      <p className="mt-2 text-sm text-surface-muted">
        Registre a primeira instalação ou ajuste os filtros de busca.
      </p>
      <button
        type="button"
        onClick={onCreate}
        className="mt-6 inline-flex items-center gap-2 rounded-lg bg-brand px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-hover"
      >
        <Plus className="h-4 w-4" />
        Nova Instalação
      </button>
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
      <Filter className="h-4 w-4 lg:hidden" />
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
