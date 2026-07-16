"use client";

import { useCallback, useEffect, useState } from "react";
import { KeyRound, Pencil, Plus, UserCheck, UserMinus, X } from "lucide-react";

import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/contexts/ToastContext";
import { ApiError } from "@/lib/api";
import type { Customer } from "@/lib/customers";
import {
  CUSTOMER_USER_ROLE_LABELS,
  CUSTOMER_USER_STATUS_LABELS,
  createCustomerUser,
  fetchCustomerUsers,
  formatLastLogin,
  mapCustomerUserError,
  resetCustomerUserPassword,
  updateCustomerUser,
  updateCustomerUserStatus,
  type CustomerUser,
  type CustomerUserRole,
} from "@/lib/customerUsers";

type Mode = "list" | "create" | "edit" | "reset";

type FormState = {
  full_name: string;
  email: string;
  password: string;
  password_confirm: string;
  role: CustomerUserRole;
  must_change_password: boolean;
};

const EMPTY_FORM: FormState = {
  full_name: "",
  email: "",
  password: "",
  password_confirm: "",
  role: "VIEWER",
  must_change_password: true,
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
  const [mode, setMode] = useState<Mode>("list");
  const [selected, setSelected] = useState<CustomerUser | null>(null);
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

  function openCreate() {
    setSelected(null);
    setForm(EMPTY_FORM);
    setMode("create");
  }

  function openEdit(user: CustomerUser) {
    setSelected(user);
    setForm({
      full_name: user.full_name,
      email: user.email,
      password: "",
      password_confirm: "",
      role: user.role,
      must_change_password: user.must_change_password,
    });
    setMode("edit");
  }

  function openReset(user: CustomerUser) {
    setSelected(user);
    setForm({
      ...EMPTY_FORM,
      must_change_password: true,
    });
    setMode("reset");
  }

  async function handleSave() {
    if (!accessToken) return;
    if (mode === "create") {
      if (!form.full_name.trim() || !form.email.trim() || form.password.length < 8) {
        showToast("Preencha nome, e-mail e senha (mín. 8 caracteres)", "error");
        return;
      }
      if (form.password !== form.password_confirm) {
        showToast("As senhas não coincidem", "error");
        return;
      }
    }
    if (mode === "reset") {
      if (form.password.length < 8) {
        showToast("Senha deve ter no mínimo 8 caracteres", "error");
        return;
      }
      if (form.password !== form.password_confirm) {
        showToast("As senhas não coincidem", "error");
        return;
      }
    }

    setSaving(true);
    try {
      if (mode === "create") {
        await createCustomerUser(accessToken, {
          customer_id: customer.id,
          full_name: form.full_name.trim(),
          email: form.email.trim(),
          password: form.password,
          password_confirm: form.password_confirm,
          role: form.role,
          must_change_password: form.must_change_password,
        });
        showToast("Acesso criado com sucesso");
      } else if (mode === "edit" && selected) {
        await updateCustomerUser(accessToken, selected.id, {
          full_name: form.full_name.trim(),
          email: form.email.trim(),
          role: form.role,
          must_change_password: form.must_change_password,
        });
        showToast("Acesso atualizado");
      } else if (mode === "reset" && selected) {
        await resetCustomerUserPassword(accessToken, selected.id, {
          password: form.password,
          password_confirm: form.password_confirm,
          must_change_password: form.must_change_password,
        });
        showToast("Senha redefinida");
      }
      setMode("list");
      await load();
    } catch (err) {
      showToast(
        err instanceof ApiError ? mapCustomerUserError(err.message) : "Erro ao salvar",
        "error",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleToggleStatus(user: CustomerUser) {
    if (!accessToken) return;
    const next = user.status === "ACTIVE" ? "INACTIVE" : "ACTIVE";
    try {
      await updateCustomerUserStatus(accessToken, user.id, next);
      showToast(next === "ACTIVE" ? "Usuário ativado" : "Usuário desativado");
      await load();
    } catch (err) {
      showToast(
        err instanceof ApiError ? mapCustomerUserError(err.message) : "Erro ao alterar status",
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
            <h2 className="text-xl font-semibold">Portal do Cliente</h2>
            <p className="mt-1 text-sm text-surface-muted">{customer.full_name}</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-2 hover:bg-slate-700/40">
            <X className="h-5 w-5" />
          </button>
        </div>

        {mode === "list" ? (
          <>
            <button
              type="button"
              onClick={openCreate}
              className="mt-6 inline-flex items-center justify-center gap-2 rounded-lg bg-brand px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-hover"
            >
              <Plus className="h-4 w-4" />
              Criar acesso
            </button>

            <div className="mt-6 space-y-3">
              {loading ? (
                <p className="text-sm text-surface-muted">Carregando usuários...</p>
              ) : users.length === 0 ? (
                <p className="text-sm text-surface-muted">
                  Nenhum acesso cadastrado para este cliente.
                </p>
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
                      <span
                        className={
                          user.status === "ACTIVE"
                            ? "rounded-full bg-emerald-500/15 px-2.5 py-1 text-xs text-emerald-300"
                            : "rounded-full bg-orange-500/15 px-2.5 py-1 text-xs text-orange-300"
                        }
                      >
                        {CUSTOMER_USER_STATUS_LABELS[user.status]}
                      </span>
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-surface-muted">
                      <div>
                        <p>Função</p>
                        <p className="mt-0.5 font-medium text-slate-200">
                          {CUSTOMER_USER_ROLE_LABELS[user.role]}
                        </p>
                      </div>
                      <div>
                        <p>Último acesso</p>
                        <p className="mt-0.5 font-medium text-slate-200">
                          {formatLastLogin(user.last_login_at)}
                        </p>
                      </div>
                    </div>
                    {user.must_change_password && (
                      <p className="mt-2 text-xs text-amber-300">
                        Exige troca de senha no próximo acesso
                      </p>
                    )}
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => openEdit(user)}
                        className="inline-flex items-center gap-1 rounded-lg border border-surface-border px-2.5 py-1.5 text-xs hover:bg-slate-700/30"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                        Editar
                      </button>
                      <button
                        type="button"
                        onClick={() => openReset(user)}
                        className="inline-flex items-center gap-1 rounded-lg border border-surface-border px-2.5 py-1.5 text-xs hover:bg-slate-700/30"
                      >
                        <KeyRound className="h-3.5 w-3.5" />
                        Redefinir senha
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleToggleStatus(user)}
                        className="inline-flex items-center gap-1 rounded-lg border border-surface-border px-2.5 py-1.5 text-xs hover:bg-slate-700/30"
                      >
                        {user.status === "ACTIVE" ? (
                          <>
                            <UserMinus className="h-3.5 w-3.5" />
                            Desativar
                          </>
                        ) : (
                          <>
                            <UserCheck className="h-3.5 w-3.5" />
                            Ativar
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </>
        ) : (
          <div className="mt-6 space-y-4">
            <button
              type="button"
              onClick={() => setMode("list")}
              className="text-sm text-surface-muted hover:text-slate-200"
            >
              ← Voltar
            </button>
            <h3 className="text-lg font-semibold">
              {mode === "create" && "Criar acesso"}
              {mode === "edit" && "Editar acesso"}
              {mode === "reset" && "Redefinir senha"}
            </h3>

            {(mode === "create" || mode === "edit") && (
              <>
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
                <select
                  value={form.role}
                  onChange={(e) => setForm((c) => ({ ...c, role: e.target.value as CustomerUserRole }))}
                  className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm"
                >
                  {Object.entries(CUSTOMER_USER_ROLE_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </>
            )}

            {(mode === "create" || mode === "reset") && (
              <>
                <input
                  value={form.password}
                  onChange={(e) => setForm((c) => ({ ...c, password: e.target.value }))}
                  placeholder="Senha (mín. 8 caracteres)"
                  type="password"
                  className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none ring-brand focus:ring-2"
                />
                <input
                  value={form.password_confirm}
                  onChange={(e) => setForm((c) => ({ ...c, password_confirm: e.target.value }))}
                  placeholder="Confirmar senha"
                  type="password"
                  className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none ring-brand focus:ring-2"
                />
              </>
            )}

            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.must_change_password}
                onChange={(e) =>
                  setForm((c) => ({ ...c, must_change_password: e.target.checked }))
                }
                className="h-4 w-4 rounded border-surface-border"
              />
              Exigir troca de senha no primeiro acesso
            </label>

            <button
              type="button"
              onClick={() => void handleSave()}
              disabled={saving}
              className="w-full rounded-lg bg-brand py-2.5 text-sm font-medium text-white hover:bg-brand-hover disabled:opacity-50"
            >
              {saving ? "Salvando..." : "Salvar"}
            </button>
          </div>
        )}
      </aside>
    </div>
  );
}
