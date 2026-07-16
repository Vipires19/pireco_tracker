"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";

import { digitsOnly } from "@/lib/masks";
import type { Tracker, TrackerOrigin, TrackerPayload, TrackerStatus } from "@/lib/trackers";
import { TRACKER_ORIGIN_LABELS, TRACKER_STATUS_LABELS } from "@/lib/trackers";

export type TrackerFormValues = TrackerPayload;

type TrackerFormDrawerProps = {
  open: boolean;
  mode: "create" | "edit";
  tracker?: Tracker | null;
  onClose: () => void;
  onSubmit: (payload: TrackerFormValues) => Promise<void>;
};

const emptyForm: TrackerFormValues = {
  imei: "",
  model: "",
  manufacturer: "",
  firmware: "",
  tracker_phone_number: "",
  sim_imei: "",
  sim_iccid: "",
  carrier: "",
  apn: "",
  serial_number: "",
  notes: "",
  origin: "MANUAL",
  status: "NEW",
};

export function TrackerFormDrawer({
  open,
  mode,
  tracker,
  onClose,
  onSubmit,
}: TrackerFormDrawerProps) {
  const [form, setForm] = useState<TrackerFormValues>(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    if (tracker) {
      setForm({
        imei: tracker.imei,
        model: tracker.model ?? "",
        manufacturer: tracker.manufacturer ?? "",
        firmware: tracker.firmware ?? "",
        tracker_phone_number: tracker.tracker_phone_number ?? "",
        sim_imei: tracker.sim_imei ?? "",
        sim_iccid: tracker.sim_iccid ?? "",
        carrier: tracker.carrier ?? "",
        apn: tracker.apn ?? "",
        serial_number: tracker.serial_number ?? "",
        notes: tracker.notes ?? "",
        origin: tracker.origin,
        status: tracker.status,
      });
    } else {
      setForm(emptyForm);
    }
    setError(null);
  }, [open, tracker]);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  function updateField<K extends keyof TrackerFormValues>(key: K, value: TrackerFormValues[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!form.imei || digitsOnly(form.imei).length !== 15) {
      setError("Informe um IMEI válido (15 dígitos)");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit(form);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao salvar rastreador");
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
        aria-labelledby="tracker-drawer-title"
      >
        <div className="flex items-center justify-between border-b border-surface-border px-6 py-4">
          <div>
            <h2 id="tracker-drawer-title" className="text-lg font-semibold">
              {mode === "create" ? "Novo Rastreador" : "Editar Rastreador"}
            </h2>
            <p className="text-sm text-surface-muted">Gestão de estoque de equipamentos</p>
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
                Equipamento
              </h3>
              <div className="space-y-3">
                <Field label="IMEI" required>
                  <input
                    required
                    value={form.imei}
                    onChange={(e) => updateField("imei", digitsOnly(e.target.value).slice(0, 15))}
                    placeholder="867686031234567"
                    inputMode="numeric"
                    maxLength={15}
                    className={inputClass}
                  />
                </Field>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Modelo">
                    <input
                      value={form.model ?? ""}
                      onChange={(e) => updateField("model", e.target.value)}
                      placeholder="GT06N"
                      className={inputClass}
                    />
                  </Field>
                  <Field label="Fabricante">
                    <input
                      value={form.manufacturer ?? ""}
                      onChange={(e) => updateField("manufacturer", e.target.value)}
                      placeholder="Concox"
                      className={inputClass}
                    />
                  </Field>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Firmware">
                    <input
                      value={form.firmware ?? ""}
                      onChange={(e) => updateField("firmware", e.target.value)}
                      placeholder="v1.2.3"
                      className={inputClass}
                    />
                  </Field>
                  <Field label="Número de série">
                    <input
                      value={form.serial_number ?? ""}
                      onChange={(e) => updateField("serial_number", e.target.value)}
                      className={inputClass}
                    />
                  </Field>
                </div>
              </div>
            </section>

            <section>
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-brand">
                Chip / Conectividade
              </h3>
              <div className="space-y-3">
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Número do chip">
                    <input
                      value={form.tracker_phone_number ?? ""}
                      onChange={(e) =>
                        updateField("tracker_phone_number", digitsOnly(e.target.value).slice(0, 11))
                      }
                      placeholder="11987654321"
                      inputMode="numeric"
                      className={inputClass}
                    />
                  </Field>
                  <Field label="IMEI do chip">
                    <input
                      value={form.sim_imei ?? ""}
                      onChange={(e) => updateField("sim_imei", digitsOnly(e.target.value).slice(0, 15))}
                      inputMode="numeric"
                      maxLength={15}
                      className={inputClass}
                    />
                  </Field>
                </div>
                <Field label="ICCID">
                  <input
                    value={form.sim_iccid ?? ""}
                    onChange={(e) => updateField("sim_iccid", digitsOnly(e.target.value).slice(0, 20))}
                    inputMode="numeric"
                    maxLength={20}
                    className={inputClass}
                  />
                </Field>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Operadora">
                    <input
                      value={form.carrier ?? ""}
                      onChange={(e) => updateField("carrier", e.target.value)}
                      placeholder="Vivo"
                      className={inputClass}
                    />
                  </Field>
                  <Field label="APN">
                    <input
                      value={form.apn ?? ""}
                      onChange={(e) => updateField("apn", e.target.value)}
                      placeholder="zap.vivo.com.br"
                      className={inputClass}
                    />
                  </Field>
                </div>
              </div>
            </section>

            <section>
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-brand">
                Classificação
              </h3>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Origem">
                  <select
                    value={form.origin}
                    onChange={(e) => updateField("origin", e.target.value as TrackerOrigin)}
                    className={inputClass}
                  >
                    {Object.entries(TRACKER_ORIGIN_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Status">
                  <select
                    value={form.status ?? "NEW"}
                    onChange={(e) => updateField("status", e.target.value as TrackerStatus)}
                    className={inputClass}
                  >
                    {Object.entries(TRACKER_STATUS_LABELS)
                      .filter(([value]) => value !== "INSTALLED")
                      .map(([value, label]) => (
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
                Observações
              </h3>
              <Field label="Notas">
                <textarea
                  rows={3}
                  value={form.notes ?? ""}
                  onChange={(e) => updateField("notes", e.target.value)}
                  className={`${inputClass} resize-none`}
                />
              </Field>
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
              {submitting ? "Salvando..." : "Salvar rastreador"}
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
