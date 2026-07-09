export function digitsOnly(value: string): string {
  return value.replace(/\D/g, "");
}

export function maskCpf(value: string): string {
  const digits = digitsOnly(value).slice(0, 11);
  return digits
    .replace(/(\d{3})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
}

export function maskCnpj(value: string): string {
  const digits = digitsOnly(value).slice(0, 14);
  return digits
    .replace(/(\d{2})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d)/, "$1/$2")
    .replace(/(\d{4})(\d{1,2})$/, "$1-$2");
}

export function maskPhone(value: string): string {
  const digits = digitsOnly(value).slice(0, 11);
  if (digits.length <= 10) {
    return digits.replace(/(\d{2})(\d{4})(\d{0,4})/, "($1) $2-$3").trim();
  }
  return digits.replace(/(\d{2})(\d{5})(\d{0,4})/, "($1) $2-$3").trim();
}

export function maskZipCode(value: string): string {
  const digits = digitsOnly(value).slice(0, 8);
  return digits.replace(/(\d{5})(\d{0,3})/, "$1-$2").trim();
}

export function formatDocument(document: string, type: "CPF" | "CNPJ"): string {
  return type === "CPF" ? maskCpf(document) : maskCnpj(document);
}

export function maskPlate(value: string): string {
  const cleaned = value.replace(/[^A-Za-z0-9]/g, "").toUpperCase().slice(0, 7);
  if (cleaned.length <= 3) return cleaned;
  if (cleaned.length <= 4) return `${cleaned.slice(0, 3)}-${cleaned.slice(3)}`;
  if (cleaned.length <= 5) return `${cleaned.slice(0, 3)}-${cleaned.slice(3, 4)}${cleaned.slice(4)}`;
  return `${cleaned.slice(0, 3)}-${cleaned.slice(3, 4)}${cleaned.slice(4, 5)}${cleaned.slice(5)}`;
}

export function formatPlate(plate: string): string {
  return maskPlate(plate);
}
