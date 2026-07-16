"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Eye,
  Filter,
  Pencil,
  Plus,
  Search,
  Trash2,
  UserCheck,
  UserCog,
  UserMinus,
  Users,
} from "lucide-react";

import { CustomerFormDrawer } from "@/components/customers/CustomerFormDrawer";
import { CustomerUsersDrawer } from "@/components/customers/CustomerUsersDrawer";
import { ActionMenu } from "@/components/ui/ActionMenu";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/contexts/ToastContext";
import { ApiError } from "@/lib/api";
import {
  createCustomer,
  deleteCustomer,
  fetchCustomers,
  updateCustomer,
  updateCustomerStatus,
  type Customer,
  type CustomerListResponse,
  type CustomerPayload,
  type CustomerStatus,
} from "@/lib/customers";
import { formatDocument, maskPhone } from "@/lib/masks";

type Filters = {
  search: string;
  status: CustomerStatus | "";
};

export function CustomersManager() {
  const { accessToken } = useAuth();
  const { showToast } = useToast();
  const [data, setData] = useState<CustomerListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<Filters>({ search: "", status: "" });
  const [appliedFilters, setAppliedFilters] = useState<Filters>({ search: "", status: "" });
  const [page, setPage] = useState(1);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerMode, setDrawerMode] = useState<"create" | "edit">("create");
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);
  const [viewCustomer, setViewCustomer] = useState<Customer | null>(null);
  const [usersCustomer, setUsersCustomer] = useState<Customer | null>(null);

  const loadCustomers = useCallback(async () => {
    if (!accessToken) return;
    setLoading(true);
    try {
      const response = await fetchCustomers(accessToken, {
        search: appliedFilters.search || undefined,
        status: appliedFilters.status || undefined,
        page,
        page_size: 20,
        sort_by: "full_name",
        sort_order: "asc",
      });
      setData(response);
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : "Erro ao carregar clientes", "error");
    } finally {
      setLoading(false);
    }
  }, [accessToken, appliedFilters, page, showToast]);

  useEffect(() => {
    void loadCustomers();
  }, [loadCustomers]);

  function openCreate() {
    setDrawerMode("create");
    setSelectedCustomer(null);
    setDrawerOpen(true);
  }

  function openEdit(customer: Customer) {
    setDrawerMode("edit");
    setSelectedCustomer(customer);
    setDrawerOpen(true);
  }

  async function handleSave(payload: CustomerPayload) {
    if (!accessToken) return;
    const body: CustomerPayload = {
      ...payload,
      secondary_phone: payload.secondary_phone || null,
      email: payload.email || null,
      zip_code: payload.zip_code || null,
      street: payload.street || null,
      number: payload.number || null,
      complement: payload.complement || null,
      district: payload.district || null,
      city: payload.city || null,
      state: payload.state || null,
      notes: payload.notes || null,
    };

    try {
      if (drawerMode === "create") {
        await createCustomer(accessToken, body);
        showToast("Cliente cadastrado com sucesso");
      } else if (selectedCustomer) {
        await updateCustomer(accessToken, selectedCustomer.id, body);
        showToast("Cliente atualizado com sucesso");
      }
      await loadCustomers();
    } catch (err) {
      throw err instanceof ApiError ? err : new Error("Falha ao salvar cliente");
    }
  }

  async function handleToggleStatus(customer: Customer) {
    if (!accessToken) return;
    const nextStatus: CustomerStatus = customer.status === "ACTIVE" ? "INACTIVE" : "ACTIVE";
    try {
      await updateCustomerStatus(accessToken, customer.id, nextStatus);
      showToast(
        nextStatus === "ACTIVE" ? "Cliente ativado com sucesso" : "Cliente inativado com sucesso",
      );
      await loadCustomers();
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : "Erro ao alterar status", "error");
    }
  }

  async function handleDelete(customer: Customer) {
    if (!accessToken) return;
    if (!window.confirm(`Excluir o cliente ${customer.full_name}?`)) return;
    try {
      await deleteCustomer(accessToken, customer.id);
      showToast("Cliente excluído com sucesso");
      await loadCustomers();
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : "Erro ao excluir cliente", "error");
    }
  }

  function applyFilters() {
    setAppliedFilters(filters);
    setPage(1);
    setFilterDrawerOpen(false);
  }

  const stats = data?.stats ?? { total: 0, active: 0, inactive: 0 };
  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Clientes</h1>
          <p className="text-surface-muted">Gestão completa da base de clientes do ERP</p>
        </div>
        <button
          type="button"
          onClick={openCreate}
          className="hidden items-center justify-center gap-2 rounded-lg bg-brand px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-hover lg:inline-flex"
        >
          <Plus className="h-4 w-4" />
          Novo Cliente
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard title="Total" value={stats.total} icon={Users} accent="bg-blue-500/20 text-blue-400" />
        <StatCard
          title="Ativos"
          value={stats.active}
          icon={UserCheck}
          accent="bg-emerald-500/20 text-emerald-400"
        />
        <StatCard
          title="Inativos"
          value={stats.inactive}
          icon={UserMinus}
          accent="bg-orange-500/20 text-orange-400"
        />
      </div>

      <div className="rounded-xl border border-surface-border bg-surface-card p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-surface-muted" />
            <input
              value={filters.search}
              onChange={(e) => setFilters((current) => ({ ...current, search: e.target.value }))}
              onKeyDown={(e) => e.key === "Enter" && applyFilters()}
              placeholder="Buscar por nome, documento, telefone, e-mail ou cidade..."
              className="w-full rounded-lg border border-surface-border bg-surface py-2.5 pl-10 pr-3 text-sm outline-none ring-brand focus:ring-2"
            />
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={applyFilters}
              className="rounded-lg bg-brand px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-hover"
            >
              Buscar
            </button>
            <button
              type="button"
              onClick={() => setFilterDrawerOpen(true)}
              className="inline-flex items-center gap-2 rounded-lg border border-surface-border px-4 py-2.5 text-sm hover:bg-slate-700/30"
            >
              <Filter className="h-4 w-4" />
              Filtros
            </button>
          </div>
        </div>
      </div>

      <div className="hidden overflow-hidden rounded-xl border border-surface-border bg-surface-card lg:block">
        <table className="min-w-full text-sm">
          <thead className="border-b border-surface-border bg-slate-900/40 text-left text-surface-muted">
            <tr>
              <th className="px-4 py-3 font-medium">Cliente</th>
              <th className="px-4 py-3 font-medium">Documento</th>
              <th className="px-4 py-3 font-medium">Contato</th>
              <th className="px-4 py-3 font-medium">Cidade</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-right">Ações</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-surface-muted">
                  Carregando clientes...
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-surface-muted">
                  Nenhum cliente encontrado.
                </td>
              </tr>
            ) : (
              items.map((customer) => (
                <tr key={customer.id} className="border-b border-surface-border/70 hover:bg-slate-800/30">
                  <td className="px-4 py-3 font-medium">{customer.full_name}</td>
                  <td className="px-4 py-3 text-surface-muted">
                    {formatDocument(customer.document, customer.document_type)}
                  </td>
                  <td className="px-4 py-3 text-surface-muted">
                    <div>{maskPhone(customer.phone)}</div>
                    <div className="text-xs">{customer.email}</div>
                  </td>
                  <td className="px-4 py-3 text-surface-muted">{customer.city ?? "—"}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={customer.status} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="inline-flex justify-end">
                      <ActionMenu
                        ariaLabel={`Ações de ${customer.full_name}`}
                        items={[
                          { label: "Visualizar", icon: Eye, onClick: () => setViewCustomer(customer) },
                          { label: "Editar", icon: Pencil, onClick: () => openEdit(customer) },
                          { label: "Usuários", icon: UserCog, onClick: () => setUsersCustomer(customer) },
                          {
                            label: customer.status === "ACTIVE" ? "Inativar" : "Ativar",
                            icon: customer.status === "ACTIVE" ? UserMinus : UserCheck,
                            onClick: () => void handleToggleStatus(customer),
                          },
                          {
                            label: "Excluir",
                            icon: Trash2,
                            danger: true,
                            onClick: () => void handleDelete(customer),
                          },
                        ]}
                      />
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="space-y-3 lg:hidden">
        {loading ? (
          <div className="rounded-xl border border-surface-border bg-surface-card p-6 text-center text-surface-muted">
            Carregando clientes...
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-xl border border-surface-border bg-surface-card p-6 text-center text-surface-muted">
            Nenhum cliente encontrado.
          </div>
        ) : (
          items.map((customer) => (
            <div
              key={customer.id}
              className="rounded-xl border border-surface-border bg-surface-card p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold">{customer.full_name}</h3>
                  <p className="mt-1 text-sm text-surface-muted">
                    {formatDocument(customer.document, customer.document_type)}
                  </p>
                </div>
                <StatusBadge status={customer.status} />
              </div>
              <div className="mt-3 space-y-1 text-sm text-surface-muted">
                <p>{maskPhone(customer.phone)}</p>
                <p>{customer.email ?? "Sem e-mail"}</p>
                <p>{customer.city ?? "Cidade não informada"}</p>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setViewCustomer(customer)}
                  className="rounded-lg border border-surface-border px-3 py-1.5 text-xs"
                >
                  Ver
                </button>
                <button
                  type="button"
                  onClick={() => openEdit(customer)}
                  className="rounded-lg border border-surface-border px-3 py-1.5 text-xs"
                >
                  Editar
                </button>
                <button
                  type="button"
                  onClick={() => setUsersCustomer(customer)}
                  className="rounded-lg border border-surface-border px-3 py-1.5 text-xs"
                >
                  Usuários
                </button>
                <button
                  type="button"
                  onClick={() => void handleToggleStatus(customer)}
                  className="rounded-lg border border-surface-border px-3 py-1.5 text-xs"
                >
                  {customer.status === "ACTIVE" ? "Inativar" : "Ativar"}
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {data && data.pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-surface-muted">
            Página {data.page} de {data.pages} — {data.total} clientes
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
              disabled={page >= data.pages}
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
        aria-label="Novo cliente"
      >
        <Plus className="h-6 w-6" />
      </button>

      <CustomerFormDrawer
        open={drawerOpen}
        mode={drawerMode}
        customer={selectedCustomer}
        onClose={() => setDrawerOpen(false)}
        onSubmit={handleSave}
      />

      {viewCustomer && (
        <ViewDrawer customer={viewCustomer} onClose={() => setViewCustomer(null)} />
      )}

      {usersCustomer && (
        <CustomerUsersDrawer
          customer={usersCustomer}
          onClose={() => setUsersCustomer(null)}
        />
      )}

      {filterDrawerOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-black/60"
            onClick={() => setFilterDrawerOpen(false)}
          />
          <aside className="absolute bottom-0 left-0 right-0 rounded-t-2xl border border-surface-border bg-surface-card p-5">
            <h3 className="text-lg font-semibold">Filtros</h3>
            <label className="mt-4 block text-sm text-surface-muted">
              Status
              <select
                value={filters.status}
                onChange={(e) =>
                  setFilters((current) => ({
                    ...current,
                    status: e.target.value as CustomerStatus | "",
                  }))
                }
                className="mt-1 w-full rounded-lg border border-surface-border bg-surface px-3 py-2.5"
              >
                <option value="">Todos</option>
                <option value="ACTIVE">Ativos</option>
                <option value="INACTIVE">Inativos</option>
              </select>
            </label>
            <button
              type="button"
              onClick={applyFilters}
              className="mt-4 w-full rounded-lg bg-brand py-2.5 text-sm font-medium text-white"
            >
              Aplicar filtros
            </button>
          </aside>
        </div>
      )}
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
    <div className="rounded-xl border border-surface-border bg-surface-card p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-surface-muted">{title}</p>
          <p className="mt-2 text-3xl font-bold">{value}</p>
        </div>
        <div className={`rounded-lg p-2 ${accent}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: CustomerStatus }) {
  return (
    <span
      className={
        status === "ACTIVE"
          ? "rounded-full bg-emerald-500/15 px-2.5 py-1 text-xs font-medium text-emerald-300"
          : "rounded-full bg-orange-500/15 px-2.5 py-1 text-xs font-medium text-orange-300"
      }
    >
      {status === "ACTIVE" ? "Ativo" : "Inativo"}
    </span>
  );
}

function ViewDrawer({ customer, onClose }: { customer: Customer; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button type="button" className="absolute inset-0 bg-black/60" onClick={onClose} />
      <aside className="relative h-full w-full max-w-lg overflow-y-auto border-l border-surface-border bg-surface p-6">
        <h2 className="text-xl font-semibold">{customer.full_name}</h2>
        <p className="mt-1 text-sm text-surface-muted">Detalhes do cliente</p>
        <div className="mt-6 space-y-4 text-sm">
          <Detail label="Documento" value={formatDocument(customer.document, customer.document_type)} />
          <Detail label="Telefone" value={maskPhone(customer.phone)} />
          <Detail label="E-mail" value={customer.email ?? "—"} />
          <Detail label="Cidade" value={customer.city ?? "—"} />
          <Detail label="Estado" value={customer.state ?? "—"} />
          <Detail label="Endereço" value={[customer.street, customer.number].filter(Boolean).join(", ") || "—"} />
          <Detail label="Observações" value={customer.notes ?? "—"} />
          <Detail label="Status" value={customer.status === "ACTIVE" ? "Ativo" : "Inativo"} />
        </div>
      </aside>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-surface-muted">{label}</p>
      <p className="mt-1 font-medium">{value}</p>
    </div>
  );
}
