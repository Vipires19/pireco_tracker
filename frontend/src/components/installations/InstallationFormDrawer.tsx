"use client";

import { useEffect, useMemo, useState } from "react";
import { X } from "lucide-react";

import type { Customer } from "@/lib/customers";
import type { InstallationChecklist, InstallationPayload, InstallationType } from "@/lib/installations";
import { CHECKLIST_LABELS, INSTALLATION_TYPE_LABELS } from "@/lib/installations";
import type { Tracker } from "@/lib/trackers";
import type { Vehicle } from "@/lib/vehicles";

export type InstallationFormValues = InstallationPayload;

type InstallationFormDrawerProps = {
  open: boolean;
  customers: Customer[];
  vehicles: Vehicle[];
  trackers: Tracker[];
  initialCustomerId?: number | null;
  initialVehicleId?: number | null;
  initialTrackerId?: number | null;
  technicianId: number;
  technicianName: string;
  onClose: () => void;
  onSubmit: (payload: InstallationFormValues) => Promise<void>;
};

const emptyChecklist: InstallationChecklist = {
  power_connected: false,
  gps_ok: false,
  gsm_ok: false,
  ignition_ok: false,
  blocking_ok: false,
  test_drive_completed: false,
  customer_present: false,
};

const emptyForm: InstallationFormValues = {
  tracker_id: 0,
  vehicle_id: 0,
  installation_type: "PRIMARY",
  installation_notes: "",
  checklist: emptyChecklist,
  complete: true,
};

export function InstallationFormDrawer({
  open,
  customers,
  vehicles,
  trackers,
  initialCustomerId,
  initialVehicleId,
  initialTrackerId,
  technicianId,
  technicianName,
  onClose,
  onSubmit,
}: InstallationFormDrawerProps) {
  const [customerId, setCustomerId] = useState<number>(0);
  const [form, setForm] = useState<InstallationFormValues>(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const filteredVehicles = useMemo(
    () => (customerId ? vehicles.filter((vehicle) => vehicle.customer_id === customerId) : []),
    [customerId, vehicles],
  );

  const installableTrackers = useMemo(
    () =>
      trackers.filter((tracker) =>
        ["IN_STOCK", "PENDING_INSTALLATION", "NEW"].includes(tracker.status),
      ),
    [trackers],
  );

  useEffect(() => {
    if (!open) return;
    const resolvedCustomer =
      initialCustomerId ??
      vehicles.find((vehicle) => vehicle.id === initialVehicleId)?.customer_id ??
      customers[0]?.id ??
      0;
    setCustomerId(resolvedCustomer);
    setForm({
      ...emptyForm,
      vehicle_id: initialVehicleId ?? 0,
      tracker_id: initialTrackerId ?? 0,
      installed_by: technicianId,
    });
    setError(null);
  }, [
    open,
    initialCustomerId,
    initialVehicleId,
    initialTrackerId,
    technicianId,
    customers,
    vehicles,
  ]);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  function updateChecklist(key: keyof InstallationChecklist, value: boolean) {
    setForm((current) => ({
      ...current,
      checklist: { ...current.checklist, [key]: value },
    }));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!form.vehicle_id) {
      setError("Selecione um veículo");
      return;
    }
    if (!form.tracker_id) {
      setError("Selecione um rastreador");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit({
        ...form,
        installed_by: technicianId,
        complete: true,
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao salvar instalação");
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
        aria-labelledby="installation-drawer-title"
      >
        <div className="flex items-center justify-between border-b border-surface-border px-6 py-4">
          <div>
            <h2 id="installation-drawer-title" className="text-lg font-semibold">
              Nova Instalação
            </h2>
            <p className="text-sm text-surface-muted">Vincule um rastreador a um veículo</p>
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
                Cliente e Veículo
              </h3>
              <div className="space-y-3">
                <Field label="Cliente" required>
                  <select
                    required
                    value={customerId || ""}
                    onChange={(e) => {
                      const nextCustomerId = Number(e.target.value);
                      setCustomerId(nextCustomerId);
                      setForm((current) => ({ ...current, vehicle_id: 0 }));
                    }}
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
                <Field label="Veículo" required>
                  <select
                    required
                    value={form.vehicle_id || ""}
                    onChange={(e) =>
                      setForm((current) => ({ ...current, vehicle_id: Number(e.target.value) }))
                    }
                    className={inputClass}
                    disabled={!customerId}
                  >
                    <option value="" disabled>
                      Selecione o veículo
                    </option>
                    {filteredVehicles.map((vehicle) => (
                      <option key={vehicle.id} value={vehicle.id}>
                        {vehicle.plate}
                        {vehicle.nickname ? ` — ${vehicle.nickname}` : ""}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>
            </section>

            <section>
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-brand">
                Rastreador
              </h3>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Equipamento" required>
                  <select
                    required
                    value={form.tracker_id || ""}
                    onChange={(e) =>
                      setForm((current) => ({ ...current, tracker_id: Number(e.target.value) }))
                    }
                    className={inputClass}
                  >
                    <option value="" disabled>
                      Selecione o rastreador
                    </option>
                    {installableTrackers.map((tracker) => (
                      <option key={tracker.id} value={tracker.id}>
                        {tracker.model || "Sem modelo"} — IMEI {tracker.imei}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Tipo" required>
                  <select
                    value={form.installation_type}
                    onChange={(e) =>
                      setForm((current) => ({
                        ...current,
                        installation_type: e.target.value as InstallationType,
                      }))
                    }
                    className={inputClass}
                  >
                    {Object.entries(INSTALLATION_TYPE_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>
            </section>

            <section>
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-brand">
                Técnico
              </h3>
              <div className="rounded-lg border border-surface-border bg-slate-900/30 px-4 py-3 text-sm">
                {technicianName}
              </div>
            </section>

            <section>
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-brand">
                Checklist
              </h3>
              <div className="grid gap-2 sm:grid-cols-2">
                {(Object.keys(CHECKLIST_LABELS) as Array<keyof InstallationChecklist>).map(
                  (key) => (
                    <label
                      key={key}
                      className="flex items-center gap-2 rounded-lg border border-surface-border px-3 py-2.5 text-sm"
                    >
                      <input
                        type="checkbox"
                        checked={form.checklist[key]}
                        onChange={(e) => updateChecklist(key, e.target.checked)}
                        className="h-4 w-4 rounded border-surface-border bg-surface text-brand"
                      />
                      {CHECKLIST_LABELS[key]}
                    </label>
                  ),
                )}
              </div>
            </section>

            <section>
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-brand">
                Observações
              </h3>
              <textarea
                rows={3}
                value={form.installation_notes ?? ""}
                onChange={(e) =>
                  setForm((current) => ({ ...current, installation_notes: e.target.value }))
                }
                className={`${inputClass} resize-none`}
                placeholder="Detalhes da instalação..."
              />
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
              {submitting ? "Salvando..." : "Salvar instalação"}
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
