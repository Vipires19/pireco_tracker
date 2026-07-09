"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowDownUp,
  Car,
  Filter,
  MoreHorizontal,
  Pencil,
  Plus,
  RadioTower,
  RefreshCw,
  Search,
  Trash2,
} from "lucide-react";

import {
  InstallationFormDrawer,
  type InstallationFormValues,
} from "@/components/installations/InstallationFormDrawer";
import {
  VehicleFormDrawer,
  type VehicleFormValues,
} from "@/components/vehicles/VehicleFormDrawer";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/contexts/ToastContext";
import { ApiError } from "@/lib/api";
import { fetchCustomers, type Customer } from "@/lib/customers";
import {
  createInstallation,
  fetchInstallations,
  formatLastSeen,
  INSTALLATION_TYPE_LABELS,
  installationTypeBadgeClass,
  mapInstallationError,
  type Installation,
} from "@/lib/installations";
import { formatPlate } from "@/lib/masks";
import { fetchTrackers, type Tracker } from "@/lib/trackers";
import {
  createVehicle,
  deleteVehicle,
  fetchVehicles,
  mapVehicleError,
  updateVehicle,
  updateVehicleStatus,
  VEHICLE_STATUS_LABELS,
  vehicleDisplayName,
  vehicleSubtitle,
  type Vehicle,
  type VehicleListResponse,
  type VehiclePayload,
  type VehicleStatus,
} from "@/lib/vehicles";

type Filters = {
  status: VehicleStatus | "";
  customer_id: number | "";
  sort_by: "plate" | "nickname" | "brand" | "model" | "created_at" | "updated_at";
  sort_order: "asc" | "desc";
};

const defaultFilters: Filters = {
  status: "",
  customer_id: "",
  sort_by: "plate",
  sort_order: "asc",
};

export function VehiclesManager() {
  const { accessToken, user } = useAuth();
  const { showToast } = useToast();

  const [data, setData] = useState<VehicleListResponse | null>(null);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [trackers, setTrackers] = useState<Tracker[]>([]);
  const [installationsByVehicle, setInstallationsByVehicle] = useState<
    Record<number, Installation[]>
  >({});
  const [loading, setLoading] = useState(true);
  const [searchInput, setSearchInput] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [page, setPage] = useState(1);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerMode, setDrawerMode] = useState<"create" | "edit">("create");
  const [selectedVehicle, setSelectedVehicle] = useState<Vehicle | null>(null);
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);
  const [menuOpenId, setMenuOpenId] = useState<number | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Vehicle | null>(null);
  const [statusTarget, setStatusTarget] = useState<Vehicle | null>(null);
  const [nextStatus, setNextStatus] = useState<VehicleStatus>("ACTIVE");
  const [installDrawerOpen, setInstallDrawerOpen] = useState(false);
  const [installVehicle, setInstallVehicle] = useState<Vehicle | null>(null);

  const customerMap = useMemo(
    () => Object.fromEntries(customers.map((customer) => [customer.id, customer.full_name])),
    [customers],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearch(searchInput.trim());
      setPage(1);
    }, 300);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  const loadCustomers = useCallback(async () => {
    if (!accessToken) return;
    try {
      const response = await fetchCustomers(accessToken, {
        page: 1,
        page_size: 100,
        sort_by: "full_name",
        sort_order: "asc",
        status: "ACTIVE",
      });
      setCustomers(response.items);
    } catch {
      showToast("Erro ao carregar clientes para filtros", "error");
    }
  }, [accessToken, showToast]);

  const loadInstallations = useCallback(async () => {
    if (!accessToken) return;
    try {
      const response = await fetchInstallations(accessToken, {
        active_only: true,
        page_size: 100,
      });
      const grouped: Record<number, Installation[]> = {};
      for (const installation of response.items) {
        grouped[installation.vehicle_id] ??= [];
        grouped[installation.vehicle_id].push(installation);
      }
      setInstallationsByVehicle(grouped);
    } catch {
      showToast("Erro ao carregar instalações dos veículos", "error");
    }
  }, [accessToken, showToast]);

  const loadTrackers = useCallback(async () => {
    if (!accessToken) return;
    try {
      const response = await fetchTrackers(accessToken, { page: 1, page_size: 100 });
      setTrackers(response.items);
    } catch {
      showToast("Erro ao carregar rastreadores", "error");
    }
  }, [accessToken, showToast]);

  const loadVehicles = useCallback(async () => {
    if (!accessToken) return;
    setLoading(true);
    try {
      const response = await fetchVehicles(accessToken, {
        search: debouncedSearch || undefined,
        status: filters.status || undefined,
        customer_id: filters.customer_id || undefined,
        page,
        page_size: 20,
        sort_by: filters.sort_by,
        sort_order: filters.sort_order,
      });
      setData(response);
    } catch (err) {
      showToast(err instanceof ApiError ? mapVehicleError(err.message) : "Erro ao carregar veículos", "error");
    } finally {
      setLoading(false);
    }
  }, [accessToken, debouncedSearch, filters, page, showToast]);

  useEffect(() => {
    void loadCustomers();
    void loadTrackers();
  }, [loadCustomers, loadTrackers]);

  useEffect(() => {
    void loadVehicles();
    void loadInstallations();
  }, [loadVehicles, loadInstallations]);

  function openInstallDrawer(vehicle: Vehicle) {
    setInstallVehicle(vehicle);
    setInstallDrawerOpen(true);
  }

  async function handleInstallSave(values: InstallationFormValues) {
    if (!accessToken) return;
    try {
      await createInstallation(accessToken, values);
      showToast("Rastreador vinculado com sucesso");
      await Promise.all([loadInstallations(), loadTrackers(), loadVehicles()]);
    } catch (err) {
      const message =
        err instanceof ApiError ? mapInstallationError(err.message) : "Falha ao vincular rastreador";
      throw new Error(message);
    }
  }

  function openCreate() {
    setDrawerMode("create");
    setSelectedVehicle(null);
    setDrawerOpen(true);
  }

  function openEdit(vehicle: Vehicle) {
    setDrawerMode("edit");
    setSelectedVehicle(vehicle);
    setDrawerOpen(true);
    setMenuOpenId(null);
  }

  function buildPayload(values: VehicleFormValues): VehiclePayload {
    return {
      customer_id: values.customer_id,
      plate: values.plate,
      nickname: values.nickname?.trim() || null,
      brand: values.brand?.trim() || null,
      model: values.model?.trim() || null,
      version: values.version?.trim() || null,
      year_model: values.year_model ?? null,
      year_manufacture: values.year_manufacture ?? null,
      category: values.category ?? null,
      renavam: values.renavam?.trim() || null,
      chassis: values.chassis?.trim() || null,
      odometer: values.odometer ?? null,
      notes: values.notes?.trim() || null,
      cover_image: values.cover_image?.trim() || null,
    };
  }

  async function handleSave(values: VehicleFormValues) {
    if (!accessToken) return;
    const payload = buildPayload(values);

    try {
      if (drawerMode === "create") {
        await createVehicle(accessToken, payload);
        showToast("Veículo cadastrado com sucesso");
      } else if (selectedVehicle) {
        await updateVehicle(accessToken, selectedVehicle.id, payload);
        if (values.status && values.status !== selectedVehicle.status) {
          await updateVehicleStatus(accessToken, selectedVehicle.id, values.status);
        }
        showToast("Veículo atualizado com sucesso");
      }
      await loadVehicles();
    } catch (err) {
      const message =
        err instanceof ApiError ? mapVehicleError(err.message) : "Falha ao salvar veículo";
      throw new Error(message);
    }
  }

  async function confirmDelete() {
    if (!accessToken || !deleteTarget) return;
    try {
      await deleteVehicle(accessToken, deleteTarget.id);
      showToast("Veículo excluído com sucesso");
      setDeleteTarget(null);
      setMenuOpenId(null);
      await loadVehicles();
    } catch (err) {
      showToast(
        err instanceof ApiError ? mapVehicleError(err.message) : "Erro ao excluir veículo",
        "error",
      );
    }
  }

  async function confirmStatusChange() {
    if (!accessToken || !statusTarget) return;
    try {
      await updateVehicleStatus(accessToken, statusTarget.id, nextStatus);
      showToast("Status atualizado com sucesso");
      setStatusTarget(null);
      setMenuOpenId(null);
      await loadVehicles();
    } catch (err) {
      showToast(
        err instanceof ApiError ? mapVehicleError(err.message) : "Erro ao alterar status",
        "error",
      );
    }
  }

  function openStatusDialog(vehicle: Vehicle) {
    setStatusTarget(vehicle);
    setNextStatus(vehicle.status);
    setMenuOpenId(null);
  }

  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Veículos</h1>
          <p className="text-surface-muted">Gerencie toda a frota da empresa</p>
        </div>
        <button
          type="button"
          onClick={openCreate}
          className="hidden items-center justify-center gap-2 rounded-lg bg-brand px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-hover lg:inline-flex"
        >
          <Plus className="h-4 w-4" />
          Novo Veículo
        </button>
      </div>

      <div className="rounded-xl border border-surface-border bg-surface-card p-4">
        <div className="flex flex-col gap-3">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-surface-muted" />
            <input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Buscar por placa, apelido, marca, modelo ou cliente..."
              aria-label="Buscar veículos"
              className="w-full rounded-lg border border-surface-border bg-surface py-2.5 pl-10 pr-3 text-sm outline-none ring-brand focus:ring-2"
            />
          </div>

          <div className="hidden flex-wrap items-center gap-2 lg:flex">
            <FilterSelect
              label="Status"
              value={filters.status}
              onChange={(value) => {
                setFilters((current) => ({ ...current, status: value as VehicleStatus | "" }));
                setPage(1);
              }}
              options={[
                { value: "", label: "Todos os status" },
                ...Object.entries(VEHICLE_STATUS_LABELS).map(([value, label]) => ({
                  value,
                  label,
                })),
              ]}
            />
            <FilterSelect
              label="Cliente"
              value={filters.customer_id === "" ? "" : String(filters.customer_id)}
              onChange={(value) => {
                setFilters((current) => ({
                  ...current,
                  customer_id: value ? Number(value) : "",
                }));
                setPage(1);
              }}
              options={[
                { value: "", label: "Todos os clientes" },
                ...customers.map((customer) => ({
                  value: String(customer.id),
                  label: customer.full_name,
                })),
              ]}
            />
            <FilterSelect
              label="Ordenar por"
              value={filters.sort_by}
              onChange={(value) => {
                setFilters((current) => ({
                  ...current,
                  sort_by: value as Filters["sort_by"],
                }));
                setPage(1);
              }}
              options={[
                { value: "plate", label: "Placa" },
                { value: "nickname", label: "Apelido" },
                { value: "brand", label: "Marca" },
                { value: "model", label: "Modelo" },
                { value: "created_at", label: "Data de cadastro" },
                { value: "updated_at", label: "Última atualização" },
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

      <div className="hidden space-y-3 lg:block">
        {loading ? (
          <VehicleListSkeleton desktop />
        ) : items.length === 0 ? (
          <EmptyState onCreate={openCreate} />
        ) : (
          items.map((vehicle) => (
            <VehicleRow
              key={vehicle.id}
              vehicle={vehicle}
              customerName={customerMap[vehicle.customer_id] ?? `Cliente #${vehicle.customer_id}`}
              installations={installationsByVehicle[vehicle.id] ?? []}
              menuOpen={menuOpenId === vehicle.id}
              onToggleMenu={() =>
                setMenuOpenId((current) => (current === vehicle.id ? null : vehicle.id))
              }
              onEdit={() => openEdit(vehicle)}
              onStatus={() => openStatusDialog(vehicle)}
              onDelete={() => {
                setDeleteTarget(vehicle);
                setMenuOpenId(null);
              }}
              onLinkTracker={() => openInstallDrawer(vehicle)}
            />
          ))
        )}
      </div>

      <div className="space-y-4 lg:hidden">
        {loading ? (
          <VehicleListSkeleton />
        ) : items.length === 0 ? (
          <EmptyState onCreate={openCreate} />
        ) : (
          items.map((vehicle) => (
            <VehicleMobileCard
              key={vehicle.id}
              vehicle={vehicle}
              customerName={customerMap[vehicle.customer_id] ?? `Cliente #${vehicle.customer_id}`}
              installations={installationsByVehicle[vehicle.id] ?? []}
              onEdit={() => openEdit(vehicle)}
              onStatus={() => openStatusDialog(vehicle)}
              onDelete={() => setDeleteTarget(vehicle)}
              onLinkTracker={() => openInstallDrawer(vehicle)}
            />
          ))
        )}
      </div>

      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-surface-muted">
            Página {data.page} de {data.total_pages} — {data.total} veículos
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
        aria-label="Novo veículo"
      >
        <Plus className="h-6 w-6" />
      </button>

      <VehicleFormDrawer
        open={drawerOpen}
        mode={drawerMode}
        vehicle={selectedVehicle}
        customers={customers}
        onClose={() => setDrawerOpen(false)}
        onSubmit={handleSave}
      />

      {deleteTarget && (
        <ConfirmDialog
          title="Excluir veículo"
          description={`Tem certeza que deseja excluir ${vehicleDisplayName(deleteTarget)}? Esta ação não pode ser desfeita.`}
          confirmLabel="Excluir"
          danger
          onCancel={() => setDeleteTarget(null)}
          onConfirm={() => void confirmDelete()}
        />
      )}

      {statusTarget && (
        <ConfirmDialog
          title="Alterar status"
          description={`Defina o novo status para ${vehicleDisplayName(statusTarget)}.`}
          confirmLabel="Salvar status"
          onCancel={() => setStatusTarget(null)}
          onConfirm={() => void confirmStatusChange()}
        >
          <select
            value={nextStatus}
            onChange={(e) => setNextStatus(e.target.value as VehicleStatus)}
            className="mt-4 w-full rounded-lg border border-surface-border bg-surface px-3 py-2.5 text-sm outline-none ring-brand focus:ring-2"
          >
            {Object.entries(VEHICLE_STATUS_LABELS).map(([value, label]) => (
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
          customers={customers}
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
          vehicles={data?.items ?? []}
          trackers={trackers}
          initialCustomerId={installVehicle?.customer_id}
          initialVehicleId={installVehicle?.id}
          technicianId={user.id}
          technicianName={user.full_name}
          onClose={() => {
            setInstallDrawerOpen(false);
            setInstallVehicle(null);
          }}
          onSubmit={handleInstallSave}
        />
      )}
    </div>
  );
}

function VehicleRow({
  vehicle,
  customerName,
  installations,
  menuOpen,
  onToggleMenu,
  onEdit,
  onStatus,
  onDelete,
  onLinkTracker,
}: {
  vehicle: Vehicle;
  customerName: string;
  installations: Installation[];
  menuOpen: boolean;
  onToggleMenu: () => void;
  onEdit: () => void;
  onStatus: () => void;
  onDelete: () => void;
  onLinkTracker: () => void;
}) {
  return (
    <article className="relative flex items-start gap-4 rounded-xl border border-surface-border bg-surface-card p-4 transition hover:border-brand/30 hover:bg-slate-800/20">
      <VehicleThumbnail vehicle={vehicle} size="md" />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="truncate text-base font-semibold">{vehicleDisplayName(vehicle)}</h3>
          <StatusBadge status={vehicle.status} />
        </div>
        <p className="mt-1 text-sm text-surface-muted">{vehicleSubtitle(vehicle)}</p>
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-surface-muted">
          <span>{formatPlate(vehicle.plate)}</span>
          <span>{customerName}</span>
        </div>
        <TrackerSection installations={installations} onLinkTracker={onLinkTracker} />
      </div>
      <div className="flex items-center gap-2 self-start">
        <button
          type="button"
          onClick={onEdit}
          className="hidden rounded-lg border border-surface-border px-3 py-1.5 text-xs hover:bg-slate-700/30 sm:inline-flex"
        >
          Editar
        </button>
        <button
          type="button"
          onClick={onStatus}
          className="hidden rounded-lg border border-surface-border px-3 py-1.5 text-xs hover:bg-slate-700/30 sm:inline-flex"
        >
          Alterar Status
        </button>
        <button
          type="button"
          onClick={onDelete}
          className="hidden rounded-lg border border-red-500/30 px-3 py-1.5 text-xs text-red-300 hover:bg-red-500/10 sm:inline-flex"
        >
          Excluir
        </button>
        <button
          type="button"
          onClick={onToggleMenu}
          className="rounded-lg p-2 hover:bg-slate-700/40"
          aria-label="Mais ações"
        >
          <MoreHorizontal className="h-4 w-4" />
        </button>
      </div>
      {menuOpen && (
        <ActionMenu onEdit={onEdit} onStatus={onStatus} onDelete={onDelete} />
      )}
    </article>
  );
}

function VehicleMobileCard({
  vehicle,
  customerName,
  installations,
  onEdit,
  onStatus,
  onDelete,
  onLinkTracker,
}: {
  vehicle: Vehicle;
  customerName: string;
  installations: Installation[];
  onEdit: () => void;
  onStatus: () => void;
  onDelete: () => void;
  onLinkTracker: () => void;
}) {
  return (
    <article className="overflow-hidden rounded-xl border border-surface-border bg-surface-card">
      <VehicleThumbnail vehicle={vehicle} size="lg" />
      <div className="space-y-3 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold">{vehicleDisplayName(vehicle)}</h3>
            <p className="mt-1 text-sm text-surface-muted">{customerName}</p>
          </div>
          <StatusBadge status={vehicle.status} />
        </div>
        <p className="text-sm text-surface-muted">{vehicleSubtitle(vehicle)}</p>
        <p className="text-sm font-medium">{formatPlate(vehicle.plate)}</p>
        <TrackerSection installations={installations} onLinkTracker={onLinkTracker} />
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onEdit}
            className="rounded-lg border border-surface-border px-3 py-1.5 text-xs"
          >
            Editar
          </button>
          <button
            type="button"
            onClick={onStatus}
            className="rounded-lg border border-surface-border px-3 py-1.5 text-xs"
          >
            Status
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="rounded-lg border border-red-500/30 px-3 py-1.5 text-xs text-red-300"
          >
            Excluir
          </button>
        </div>
      </div>
    </article>
  );
}

function TrackerSection({
  installations,
  onLinkTracker,
}: {
  installations: Installation[];
  onLinkTracker: () => void;
}) {
  return (
    <div className="mt-3 rounded-lg border border-dashed border-surface-border bg-slate-900/30 p-3">
      <div className="flex items-center gap-2 text-sm font-medium">
        <RadioTower className="h-4 w-4 text-brand" />
        <span>Rastreadores</span>
      </div>
      {installations.length === 0 ? (
        <p className="mt-1.5 text-xs text-surface-muted">Nenhum rastreador instalado.</p>
      ) : (
        <div className="mt-2 space-y-2">
          {installations.map((installation) => (
            <div
              key={installation.id}
              className="rounded-lg border border-surface-border bg-surface/40 px-3 py-2"
            >
              <div className="flex items-center gap-2">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${installationTypeBadgeClass(installation.installation_type)}`}
                >
                  {INSTALLATION_TYPE_LABELS[installation.installation_type]}
                </span>
                <span className="text-sm font-medium">
                  {installation.tracker.model || "Rastreador"}
                </span>
              </div>
              <p className="mt-1 font-mono text-xs text-surface-muted">
                IMEI {installation.tracker.imei}
              </p>
              <p className="mt-1 text-xs text-surface-muted">
                {formatLastSeen(installation.tracker.last_seen_at)}
              </p>
            </div>
          ))}
        </div>
      )}
      <button
        type="button"
        onClick={onLinkTracker}
        className="mt-2 inline-flex items-center gap-2 rounded-lg border border-surface-border px-3 py-1.5 text-xs hover:bg-slate-700/30"
      >
        <RadioTower className="h-3.5 w-3.5" />
        Vincular Rastreador
      </button>
    </div>
  );
}

function VehicleThumbnail({ vehicle, size }: { vehicle: Vehicle; size: "md" | "lg" }) {
  const sizeClass = size === "lg" ? "h-44 w-full" : "h-16 w-16 shrink-0";
  if (vehicle.cover_image) {
    return (
      <div className={`overflow-hidden rounded-xl border border-surface-border bg-slate-900/40 ${sizeClass}`}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={vehicle.cover_image}
          alt={vehicleDisplayName(vehicle)}
          className="h-full w-full object-cover"
        />
      </div>
    );
  }
  return (
    <div
      className={`flex items-center justify-center rounded-xl border border-surface-border bg-gradient-to-br from-slate-800 to-slate-900 text-surface-muted ${sizeClass}`}
    >
      <Car className={size === "lg" ? "h-10 w-10" : "h-7 w-7"} />
    </div>
  );
}

function StatusBadge({ status }: { status: VehicleStatus }) {
  const styles: Record<VehicleStatus, string> = {
    ACTIVE: "bg-emerald-500/15 text-emerald-300",
    INACTIVE: "bg-orange-500/15 text-orange-300",
    PENDING_INSTALLATION: "bg-amber-500/15 text-amber-300",
    IN_STOCK: "bg-blue-500/15 text-blue-300",
    DECOMMISSIONED: "bg-slate-500/20 text-slate-300",
  };
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${styles[status]}`}>
      {VEHICLE_STATUS_LABELS[status]}
    </span>
  );
}

function ActionMenu({
  onEdit,
  onStatus,
  onDelete,
}: {
  onEdit: () => void;
  onStatus: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="absolute right-4 top-14 z-10 w-44 rounded-xl border border-surface-border bg-surface-card p-1 shadow-2xl">
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

function VehicleListSkeleton({ desktop = false }: { desktop?: boolean }) {
  return (
    <>
      {Array.from({ length: desktop ? 5 : 3 }).map((_, index) => (
        <div
          key={index}
          className={`animate-pulse rounded-xl border border-surface-border bg-surface-card ${
            desktop ? "flex items-center gap-4 p-4" : "overflow-hidden"
          }`}
        >
          <div className={desktop ? "h-16 w-16 rounded-xl bg-slate-700/50" : "h-44 bg-slate-700/50"} />
          <div className={`space-y-3 ${desktop ? "flex-1" : "p-4"}`}>
            <div className="h-4 w-1/3 rounded bg-slate-700/50" />
            <div className="h-3 w-1/2 rounded bg-slate-700/40" />
            <div className="h-3 w-1/4 rounded bg-slate-700/40" />
          </div>
        </div>
      ))}
    </>
  );
}

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="rounded-xl border border-dashed border-surface-border bg-surface-card px-6 py-14 text-center">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-brand/10 text-brand">
        <Car className="h-7 w-7" />
      </div>
      <h3 className="mt-4 text-lg font-semibold">Nenhum veículo encontrado</h3>
      <p className="mt-2 text-sm text-surface-muted">
        Cadastre o primeiro veículo da frota ou ajuste os filtros de busca.
      </p>
      <button
        type="button"
        onClick={onCreate}
        className="mt-6 inline-flex items-center gap-2 rounded-lg bg-brand px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-hover"
      >
        <Plus className="h-4 w-4" />
        Novo Veículo
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
  customers,
  onChange,
  onApply,
  onClose,
}: {
  filters: Filters;
  customers: Customer[];
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
              onChange={(e) =>
                onChange({ ...filters, status: e.target.value as VehicleStatus | "" })
              }
              className="mt-1 w-full rounded-lg border border-surface-border bg-surface px-3 py-2.5"
            >
              <option value="">Todos</option>
              {Object.entries(VEHICLE_STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm text-surface-muted">
            Cliente
            <select
              value={filters.customer_id === "" ? "" : String(filters.customer_id)}
              onChange={(e) =>
                onChange({
                  ...filters,
                  customer_id: e.target.value ? Number(e.target.value) : "",
                })
              }
              className="mt-1 w-full rounded-lg border border-surface-border bg-surface px-3 py-2.5"
            >
              <option value="">Todos</option>
              {customers.map((customer) => (
                <option key={customer.id} value={customer.id}>
                  {customer.full_name}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm text-surface-muted">
            Ordenar por
            <select
              value={filters.sort_by}
              onChange={(e) =>
                onChange({ ...filters, sort_by: e.target.value as Filters["sort_by"] })
              }
              className="mt-1 w-full rounded-lg border border-surface-border bg-surface px-3 py-2.5"
            >
              <option value="plate">Placa</option>
              <option value="nickname">Apelido</option>
              <option value="brand">Marca</option>
              <option value="model">Modelo</option>
              <option value="created_at">Data de cadastro</option>
              <option value="updated_at">Última atualização</option>
            </select>
          </label>
          <label className="block text-sm text-surface-muted">
            Ordem
            <select
              value={filters.sort_order}
              onChange={(e) =>
                onChange({ ...filters, sort_order: e.target.value as "asc" | "desc" })
              }
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
