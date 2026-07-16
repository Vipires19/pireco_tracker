"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, Trash2, X } from "lucide-react";

import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/contexts/ToastContext";
import { ApiError } from "@/lib/api";
import type { Customer } from "@/lib/customers";
import {
  CUSTOMER_USER_ROLE_LABELS,
  CUSTOMER_USER_STATUS_LABELS,
  createCustomerUser,
  deleteCustomerUser,
  fetchCustomerUsers,
  mapCustomerUserError,
  updateCustomerUser,
  type CustomerUser,
  type CustomerUserRole,
  type CustomerUserStatus,
} from "@/lib/customerUsers";

type FormState = {
  full_name: string;
  email: string;
  password: string;
  role: CustomerUserRole;
  status: CustomerUserStatus;
};

const EMPTY_FORM: FormState = {
  full_name: "",
  email: "",
  password: "",
  role: "VIEWER",
  status: "ACTIVE",
};

export function CustomerUsersDrawer({
  customer,
  onClose,
}: {
  customer: Customer;
  onClose: () => void;
}) {
  const { accessToken } = useAuth();
  const { showToast } = useToast();
  const [users, setUsers] = useState<CustomerUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    if (!accessToken) return;
    setLoading(true);
    try {
      const response = await fetchCustomerUsers(accessToken, customer.id);
      setUsers(response.items);
    } catch (err) {
      showToast(
        err instanceof ApiError ? mapCustomerUserError(err.message) : "Erro ao carregar usuários",
        "error",
      );
    } finally {
      setLoading(false);
    }
  }, [accessToken, customer.id, showToast]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleCreate() {
    if (!accessToken) return;
    if (!form.full_name.trim() || !form.email.trim() || form.password.length < 8) {
      showToast("Preencha nome, e-mail e senha (mín. 8 caracteres)", "error");
      return;
    }
    setSaving(true);
    try {
      await createCustomerUser(accessToken, customer.id, {
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        password: form.password,
        role: form.role,
        status: form.status,
      });
      showToast("Usuário criado com sucesso");
      setForm(EMPTY_FORM);
      await load();
    } catch (err) {
      showToast(
        err instanceof ApiError ? mapCustomerUserError(err.message) : "Erro ao criar usuário",
        "error",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleToggleStatus(user: CustomerUser) {
    if (!accessToken) return;
    const next: CustomerUserStatus = user.status === "ACTIVE" ? "INACTIVE" : "ACTIVE";
    try {
      await updateCustomerUser(accessToken, customer.id, user.id, { status: next });
      await load();
    } catch (err) {
      showToast(
        err instanceof ApiError ? mapCustomerUserError(err.message) : "Erro ao alterar status",
        "error",
      );
    }
  }

  async function handleRoleChange(user: CustomerUser, role: CustomerUserRole) {
    if (!accessToken) return;
    try {
      await updateCustomerUser(accessToken, customer.id, user.id, { role });
      await load();
    } catch (err) {
      showToast(
        err instanceof ApiError ? mapCustomerUserError(err.message) : "Erro ao alterar papel",
        "error",
      );
    }
  }

  async function handleDelete(user: CustomerUser) {
    if (!accessToken) return;
    if (!window.confirm(`Remover o usuário ${user.full_name}?`)) return;
    try {
      await deleteCustomerUser(accessToken, customer.id, user.id);
      showToast("Usuário removido");
      await load();
    } catch (err) {
      showToast(
        err instanceof ApiError ? mapCustomerUserError(err.message) : "Erro ao remover usuário",
        "error",
      );
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button type="button" className="absolute inset-0 bg-black/60" onClick={onClose} />
      <aside className="relative flex h-full w-full max-w-lg flex-col overflow-y-auto border-l border-surface-border bg-surface p-6">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-xl font-semibold">Usuários do Cliente</h2>
            <p className="mt-1 text-sm text-surface-muted">{customer.full_name}</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-2 hover:bg-slate-700/40">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mt-6 rounded-xl border border-surface-border bg-surface-card p-4">
          <h3 className="text-sm font-semibold">Novo usuário</h3>
          <div className="mt-3 grid gap-3">
            <input
              value={form.full_name}
              onChange={(e) => setForm((c) => ({ ...c, full_name: e.target.value }))}
              placeholder="Nome completo"
              className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none ring-brand focus:ring-2"
            />
            <input
              value={form.email}
              onChange={(e) => setForm((c) => ({ ...c, email: e.target.value }))}
              placeholder="E-mail"
              type="email"
              className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none ring-brand focus:ring-2"
            />
            <input
              value={form.password}
              onChange={(e) => setForm((c) => ({ ...c, password: e.target.value }))}
              placeholder="Senha (mín. 8 caracteres)"
              type="password"
              className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none ring-brand focus:ring-2"
            />
            <div className="grid grid-cols-2 gap-3">
              <select
                value={form.role}
                onChange={(e) => setForm((c) => ({ ...c, role: e.target.value as CustomerUserRole }))}
                className="rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm"
              >
                {Object.entries(CUSTOMER_USER_ROLE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              <select
                value={form.status}
                onChange={(e) =>
                  setForm((c) => ({ ...c, status: e.target.value as CustomerUserStatus }))
                }
                className="rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm"
              >
                {Object.entries(CUSTOMER_USER_STATUS_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              onClick={() => void handleCreate()}
              disabled={saving}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-hover disabled:opacity-50"
            >
              <Plus className="h-4 w-4" />
              Adicionar usuário
            </button>
          </div>
        </div>

        <div className="mt-6 space-y-3">
          {loading ? (
            <p className="text-sm text-surface-muted">Carregando usuários...</p>
          ) : users.length === 0 ? (
            <p className="text-sm text-surface-muted">Nenhum usuário cadastrado para este cliente.</p>
          ) : (
            users.map((user) => (
              <div
                key={user.id}
                className="rounded-xl border border-surface-border bg-surface-card p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium">{user.full_name}</p>
                    <p className="text-xs text-surface-muted">{user.email}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => void handleDelete(user)}
                    className="rounded-lg p-2 text-red-400 hover:bg-slate-700/40"
                    aria-label={`Remover ${user.full_name}`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-3">
                  <select
                    value={user.role}
                    onChange={(e) =>
                      void handleRoleChange(user, e.target.value as CustomerUserRole)
                    }
                    className="rounded-lg border border-surface-border bg-surface px-3 py-2 text-xs"
                  >
                    {Object.entries(CUSTOMER_USER_ROLE_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => void handleToggleStatus(user)}
                    className="rounded-lg border border-surface-border px-3 py-2 text-xs"
                  >
                    {user.status === "ACTIVE" ? "🟢 Ativo" : "🔴 Inativo"}
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </aside>
    </div>
  );
}
