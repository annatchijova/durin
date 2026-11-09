// Translates Durin's raw reason codes (automation.py, supplier_operations.py,
// paypal_payouts.py) into the four states the UI actually shows. This file
// is the single place that decision happens, so the dashboard and the
// journey page can never disagree about what counts as an exception.

export type UiState = "ready" | "exception" | "review" | "pending";

const EXCEPTION_REASONS = new Set([
  "CONFLICTING_INVOICE_FACTS",
  "CONFLICTING_SUPPLIER_IDENTITY",
  "OPERATION_MISMATCH",
  "EXCEEDS_PER_PAYMENT_LIMIT",
  "EXCEEDS_BATCH_LIMIT",
  "RECIPIENT_NOT_APPROVED",
  "CURRENCY_NOT_SUPPORTED",
  "FAILED_OPERATION",
  "UNKNOWN_OPERATION_STATE",
  "AMBIGUOUS_OPERATION",
]);

const REVIEW_REASONS = new Set([
  "POSSIBLE_DUPLICATE",
  "POSSIBLE_TYPO",
  "PRICE_ALERT",
  "REQUIRES_SOURCE_REVIEW",
  "PARTIAL_OPERATION",
  "PROVIDER_EVIDENCE_REQUIRED",
  "OVERDUE",
]);

export function classifyReasons(reasons: string[]): UiState {
  if (reasons.length === 0) return "ready";
  if (reasons.some((r) => EXCEPTION_REASONS.has(r))) return "exception";
  if (reasons.some((r) => REVIEW_REASONS.has(r))) return "review";
  return "pending";
}

export function classifyOperationState(operationState: string): UiState {
  const ready = new Set(["SUCCESS", "COMPLETED", "PAID", "MATCHED"]);
  const exception = new Set(["UNCLAIMED", "BLOCKED", "DENIED", "RETURNED", "REFUNDED", "FAILED", "CANCELED", "CANCELLED", "MISMATCHED"]);
  const pending = new Set(["PENDING", "PROCESSING", "ON_HOLD", "UNMATCHED", "UNKNOWN", "AMBIGUOUS"]);
  if (ready.has(operationState)) return "ready";
  if (exception.has(operationState)) return "exception";
  if (pending.has(operationState)) return "pending";
  return "review";
}

export const STATE_LABEL: Record<UiState, string> = {
  ready: "Conciliado",
  exception: "Excepción",
  review: "Requiere revisión",
  pending: "Pendiente",
};
