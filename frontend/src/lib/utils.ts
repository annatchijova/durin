import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function shortHash(hash: string, length = 10): string {
  if (!hash || hash.length <= length * 2) return hash;
  return `${hash.slice(0, length)}…${hash.slice(-6)}`;
}

export function formatDate(iso: string, lang: "en" | "es" = "en"): string {
  try {
    return new Date(iso).toLocaleString(lang === "es" ? "es-AR" : "en-US", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function formatMoney(amount: string, currency: string): string {
  const value = Number.parseFloat(amount);
  if (Number.isNaN(value)) return `${amount} ${currency}`;
  return `${value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`;
}
