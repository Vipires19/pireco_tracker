"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";

import type { Customer } from "@/lib/customers";
import { digitsOnly, maskPlate } from "@/lib/masks";
import type {
  Vehicle,
  VehicleCategory,
  VehiclePayload,
  VehicleStatus,
} from "@/lib/vehicles";
import { VEHICLE_CATEGORY_LABELS, VEHICLE_STATUS_LABELS } from "@/lib/vehicles";

export type VehicleFormValues = VehiclePayload & {
  status?: VehicleStatus;
};

type VehicleFormDrawerProps = {
  open: boolean;
  mode: "create" | "edit";
  vehicle?: Vehicle | null;
  customers: Customer[];
  onClose: () => void;
  onSubmit: (payload: VehicleFormValues) => Promise<void>;
};

const emptyForm: VehicleFormValues = {
  customer_id: 0,
  plate: "",
  nickname: "",
  brand: "",
  model: "",
  version: "",
  year_model: null,
  year_manufacture: null,
  category: null,
  renavam: "",
  chassis: "",
  odometer: null,
  status: "ACTIVE",
  notes: "",
  cover_image: "",
};

export function VehicleFormDrawer({
  open,
  mode,
  vehicle,
  customers,
  onClose,
  onSubmit,
}: VehicleFormDrawerProps) {
  const [form, setForm] = useState<VehicleFormValues>(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    if (vehicle) {
      setForm({
        customer_id: vehicle.customer_id,
        plate: maskPlate(vehicle.plate),
        nickname: vehicle.nickname ?? "",
        brand: vehicle.brand ?? "",
        model: vehicle.model ?? "",
        version: vehicle.version ?? "",
        year_model: vehicle.year_model,
        year_manufacture: vehicle.year_manufacture,
        category: vehicle.category,
        renavam: vehicle.renavam ?? "",
        chassis: vehicle.chassis ?? "",
        odometer: vehicle.odometer,
        status: vehicle.status,
        notes: vehicle.notes ?? "",
        cover_image: vehicle.cover_image ?? "",
      });
    } else {
      setForm({
        ...emptyForm,
        customer_id: customers[0]?.id ?? 0,
      });
    }
    setError(null);
  }, [open, vehicle, customers]);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  function updateField<K extends keyof VehicleFormValues>(key: K, value: VehicleFormValues[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!form.customer_id) {
      setError("Selecione um cliente");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit(form);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao salvar veículo");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button
        type="button"
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-label="Fechar drawer"
      />
      <aside
        className="relative flex h-full w-full max-w-xl flex-col border-l border-surface-border bg-surface shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="vehicle-drawer-title"
      >
        <div className="flex items-center justify-between border-b border-surface-border px-6 py-4">
          <div>
            <h2 id="vehicle-drawer-title" className="text-lg font-semibold">
              {mode === "create" ? "Novo Veículo" : "Editar Veículo"}
            </h2>
            <p className="text-sm text-surface-muted">Preencha os dados do veículo</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-surface-muted hover:bg-slate-700/40"
            aria-label="Fechar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} noValidate className="flex-1 overflow-y-auto px-6 py-5">
          <div className="space-y-6">
            <section>
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-brand">
                Identificação
              </h3>
              <div className="space-y-3">
                <Field label="Cliente" required>
                  <select
                    required
                    value={form.customer_id || ""}
                    onChange={(e) => updateField("customer_id", Number(e.target.value))}
                    className={inputClass}
                  >
                    <option value="" disabled>
                      Selecione o cliente
                    </option>
                    {customers.map((customer) => (
                      <option key={customer.id} value={customer.id}>
                        {customer.full_name}
                      </option>
                    ))}
                  </select>
                </Field>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Placa" required>
                    <input
                      required
                      value={form.plate}
                      onChange={(e) => updateField("plate", maskPlate(e.target.value))}
                      placeholder="ABC-1D23"
                      className={inputClass}
                    />
                  </Field>
                  <Field label="Apelido">
                    <input
                      value={form.nickname ?? ""}
                      onChange={(e) => updateField("nickname", e.target.value)}
                      placeholder="Hilux Fazenda"
                      className={inputClass}
                    />
                  </Field>
                </div>
              </div>
            </section>

            <section>
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-brand">
                Veículo
              </h3>
              <div className="space-y-3">
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Marca">
                    <input
                      value={form.brand ?? ""}
                      onChange={(e) => updateField("brand", e.target.value)}
                      className={inputClass}
                    />
                  </Field>
                  <Field label="Modelo">
                    <input
                      value={form.model ?? ""}
                      onChange={(e) => updateField("model", e.target.value)}
                      className={inputClass}
                    />
                  </Field>
                </div>
                <Field label="Versão">
                  <input
                    value={form.version ?? ""}
                    onChange={(e) => updateField("version", e.target.value)}
                    className={inputClass}
                  />
                </Field>
                <div className="grid gap-3 sm:grid-cols-3">
                  <Field label="Ano modelo">
                    <input
                      type="number"
                      min={1900}
                      value={form.year_model ?? ""}
                      onChange={(e) =>
                        updateField("year_model", e.target.value ? Number(e.target.value) : null)
                      }
                      className={inputClass}
                    />
                  </Field>
                  <Field label="Ano fabricação">
                    <input
                      type="number"
                      min={1900}
                      value={form.year_manufacture ?? ""}
                      onChange={(e) =>
                        updateField(
                          "year_manufacture",
                          e.target.value ? Number(e.target.value) : null,
                        )
                      }
                      className={inputClass}
                    />
                  </Field>
                  <Field label="Categoria">
                    <select
                      value={form.category ?? ""}
                      onChange={(e) =>
                        updateField(
                          "category",
                          (e.target.value || null) as VehicleCategory | null,
                        )
                      }
                      className={inputClass}
                    >
                      <option value="">Selecione</option>
                      {Object.entries(VEHICLE_CATEGORY_LABELS).map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </Field>
                </div>
              </div>
            </section>

            <section>
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-brand">
                Documentação
              </h3>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="RENAVAM">
                  <input
                    value={form.renavam ?? ""}
                    onChange={(e) => updateField("renavam", digitsOnly(e.target.value))}
                    maxLength={11}
                    className={inputClass}
                  />
                </Field>
                <Field label="Chassi">
                  <input
                    value={form.chassis ?? ""}
                    onChange={(e) =>
                      updateField("chassis", e.target.value.toUpperCase().replace(/\s/g, ""))
                    }
                    maxLength={17}
                    className={inputClass}
                  />
                </Field>
              </div>
            </section>

            <section>
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-brand">
                Informações
              </h3>
              <div className="space-y-3">
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Odômetro (km)">
                    <input
                      type="number"
                      min={0}
                      value={form.odometer ?? ""}
                      onChange={(e) =>
                        updateField("odometer", e.target.value ? Number(e.target.value) : null)
                      }
                      className={inputClass}
                    />
                  </Field>
                  {mode === "edit" && (
                    <Field label="Status">
                      <select
                        value={form.status ?? "ACTIVE"}
                        onChange={(e) =>
                          updateField("status", e.target.value as VehicleStatus)
                        }
                        className={inputClass}
                      >
                        {Object.entries(VEHICLE_STATUS_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </Field>
                  )}
                </div>
                <Field label="Observações">
                  <textarea
                    rows={3}
                    value={form.notes ?? ""}
                    onChange={(e) => updateField("notes", e.target.value)}
                    className={`${inputClass} resize-none`}
                  />
                </Field>
              </div>
            </section>

            <section>
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-brand">
                Imagem
              </h3>
              <Field label="URL da foto">
                <input
                  type="url"
                  value={form.cover_image ?? ""}
                  onChange={(e) => updateField("cover_image", e.target.value)}
                  placeholder="https://..."
                  className={inputClass}
                />
              </Field>
              {form.cover_image && (
                <div className="mt-3 overflow-hidden rounded-xl border border-surface-border">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={form.cover_image}
                    alt="Pré-visualização do veículo"
                    className="h-40 w-full object-cover"
                    onError={(e) => {
                      e.currentTarget.style.display = "none";
                    }}
                  />
                </div>
              )}
            </section>
          </div>

          {error && (
            <p className="mt-4 rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-400" role="alert">
              {error}
            </p>
          )}

          <div className="sticky bottom-0 mt-6 flex gap-3 border-t border-surface-border bg-surface py-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-lg border border-surface-border px-4 py-2.5 text-sm hover:bg-slate-700/30"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 rounded-lg bg-brand px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-hover disabled:opacity-60"
            >
              {submitting ? "Salvando..." : "Salvar veículo"}
            </button>
          </div>
        </form>
      </aside>
    </div>
  );
}

function Field({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm text-surface-muted">
        {label}
        {required && <span className="text-red-400"> *</span>}
      </span>
      {children}
    </label>
  );
}

const inputClass =
  "w-full rounded-lg border border-surface-border bg-surface px-3 py-2.5 text-sm outline-none ring-brand focus:ring-2";
