"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";

import type { Customer, CustomerPayload, DocumentType } from "@/lib/customers";
import { maskCnpj, maskCpf, maskPhone, maskZipCode } from "@/lib/masks";

type CustomerFormDrawerProps = {
  open: boolean;
  mode: "create" | "edit";
  customer?: Customer | null;
  onClose: () => void;
  onSubmit: (payload: CustomerPayload) => Promise<void>;
};

const emptyForm: CustomerPayload = {
  full_name: "",
  document: "",
  document_type: "CPF",
  phone: "",
  secondary_phone: "",
  email: "",
  zip_code: "",
  street: "",
  number: "",
  complement: "",
  district: "",
  city: "",
  state: "",
  notes: "",
};

export function CustomerFormDrawer({
  open,
  mode,
  customer,
  onClose,
  onSubmit,
}: CustomerFormDrawerProps) {
  const [form, setForm] = useState<CustomerPayload>(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    if (customer) {
      setForm({
        full_name: customer.full_name,
        document:
          customer.document_type === "CPF"
            ? maskCpf(customer.document)
            : maskCnpj(customer.document),
        document_type: customer.document_type,
        phone: maskPhone(customer.phone),
        secondary_phone: customer.secondary_phone ? maskPhone(customer.secondary_phone) : "",
        email: customer.email ?? "",
        zip_code: customer.zip_code ? maskZipCode(customer.zip_code) : "",
        street: customer.street ?? "",
        number: customer.number ?? "",
        complement: customer.complement ?? "",
        district: customer.district ?? "",
        city: customer.city ?? "",
        state: customer.state ?? "",
        notes: customer.notes ?? "",
      });
    } else {
      setForm(emptyForm);
    }
    setError(null);
  }, [open, customer]);

  if (!open) return null;

  function updateField<K extends keyof CustomerPayload>(key: K, value: CustomerPayload[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit(form);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao salvar cliente");
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
        aria-label="Fechar"
      />
      <aside className="relative flex h-full w-full max-w-xl flex-col border-l border-surface-border bg-surface shadow-2xl">
        <div className="flex items-center justify-between border-b border-surface-border px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold">
              {mode === "create" ? "Novo Cliente" : "Editar Cliente"}
            </h2>
            <p className="text-sm text-surface-muted">Preencha os dados do cliente</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-surface-muted hover:bg-slate-700/40"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} noValidate className="flex-1 overflow-y-auto px-6 py-5">
          <div className="space-y-6">
            <section>
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-brand">
                Dados pessoais
              </h3>
              <div className="space-y-3">
                <Field label="Nome completo" required>
                  <input
                    required
                    value={form.full_name}
                    onChange={(e) => updateField("full_name", e.target.value)}
                    className={inputClass}
                  />
                </Field>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Tipo de documento" required>
                    <select
                      value={form.document_type}
                      onChange={(e) =>
                        updateField("document_type", e.target.value as DocumentType)
                      }
                      className={inputClass}
                    >
                      <option value="CPF">CPF</option>
                      <option value="CNPJ">CNPJ</option>
                    </select>
                  </Field>
                  <Field label="CPF/CNPJ" required>
                    <input
                      required
                      value={form.document}
                      onChange={(e) =>
                        updateField(
                          "document",
                          form.document_type === "CPF"
                            ? maskCpf(e.target.value)
                            : maskCnpj(e.target.value),
                        )
                      }
                      className={inputClass}
                    />
                  </Field>
                </div>
              </div>
            </section>

            <section>
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-brand">
                Contato
              </h3>
              <div className="space-y-3">
                <Field label="Telefone" required>
                  <input
                    required
                    value={form.phone}
                    onChange={(e) => updateField("phone", maskPhone(e.target.value))}
                    className={inputClass}
                  />
                </Field>
                <Field label="Telefone secundário">
                  <input
                    value={form.secondary_phone ?? ""}
                    onChange={(e) => updateField("secondary_phone", maskPhone(e.target.value))}
                    className={inputClass}
                  />
                </Field>
                <Field label="E-mail">
                  <input
                    type="email"
                    value={form.email ?? ""}
                    onChange={(e) => updateField("email", e.target.value)}
                    className={inputClass}
                  />
                </Field>
              </div>
            </section>

            <section>
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-brand">
                Endereço
              </h3>
              <div className="space-y-3">
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="CEP">
                    <input
                      value={form.zip_code ?? ""}
                      onChange={(e) => updateField("zip_code", maskZipCode(e.target.value))}
                      className={inputClass}
                    />
                  </Field>
                  <Field label="Estado">
                    <input
                      maxLength={2}
                      value={form.state ?? ""}
                      onChange={(e) => updateField("state", e.target.value.toUpperCase())}
                      className={inputClass}
                    />
                  </Field>
                </div>
                <Field label="Rua">
                  <input
                    value={form.street ?? ""}
                    onChange={(e) => updateField("street", e.target.value)}
                    className={inputClass}
                  />
                </Field>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Número">
                    <input
                      value={form.number ?? ""}
                      onChange={(e) => updateField("number", e.target.value)}
                      className={inputClass}
                    />
                  </Field>
                  <Field label="Complemento">
                    <input
                      value={form.complement ?? ""}
                      onChange={(e) => updateField("complement", e.target.value)}
                      className={inputClass}
                    />
                  </Field>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Bairro">
                    <input
                      value={form.district ?? ""}
                      onChange={(e) => updateField("district", e.target.value)}
                      className={inputClass}
                    />
                  </Field>
                  <Field label="Cidade">
                    <input
                      value={form.city ?? ""}
                      onChange={(e) => updateField("city", e.target.value)}
                      className={inputClass}
                    />
                  </Field>
                </div>
              </div>
            </section>

            <section>
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-brand">
                Observações
              </h3>
              <textarea
                rows={4}
                value={form.notes ?? ""}
                onChange={(e) => updateField("notes", e.target.value)}
                className={`${inputClass} resize-none`}
              />
            </section>
          </div>

          {error && (
            <p className="mt-4 rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-400">{error}</p>
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
              {submitting ? "Salvando..." : "Salvar cliente"}
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
