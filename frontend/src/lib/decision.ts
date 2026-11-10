// The decision summary and the dashboard are projections of the case state
// api_server.py already sealed and stored. Nothing in this file decides
// anything: it selects and counts fields that already exist, and it never
// adds amounts (totals come pre-computed from the engine as strings). This
// is the single place those projections live, so the summary panel, the
// case cards, and the journey can never disagree with each other.

import type { Case, CaseStage, CaseSummary, Row } from "./types";

export type NextActionKind =
  | "PREPARE_PROPOSAL"
  | "REVIEW_EXCEPTIONS"
  | "REVIEW_EXTRACTION"
  | "REVIEW_AND_APPROVE"
  | "SUBMIT_TO_PAYPAL"
  | "RESOLVE_SUBMISSION"
  | "REFRESH_PAYPAL"
  | "NONE";

export type Actor = "source" | "ai" | "engine" | "human" | "paypal";

/** Journey anchors. The summary only ever links to these; it never mutates. */
export const STEP_ANCHOR = {
  evidence: "step-evidence",
  extraction: "step-extraction",
  contradictions: "step-contradictions",
  proposal: "step-proposal",
  approval: "step-approval",
  paypal: "step-paypal",
  exceptions: "exceptions",
} as const;

export const ACTION_TARGET: Record<NextActionKind, { anchor: string | null; actor: Actor | null }> = {
  PREPARE_PROPOSAL: { anchor: STEP_ANCHOR.proposal, actor: "engine" },
  REVIEW_EXCEPTIONS: { anchor: STEP_ANCHOR.exceptions, actor: "human" },
  REVIEW_EXTRACTION: { anchor: STEP_ANCHOR.extraction, actor: "human" },
  REVIEW_AND_APPROVE: { anchor: STEP_ANCHOR.approval, actor: "human" },
  SUBMIT_TO_PAYPAL: { anchor: STEP_ANCHOR.paypal, actor: "human" },
  RESOLVE_SUBMISSION: { anchor: STEP_ANCHOR.paypal, actor: "human" },
  REFRESH_PAYPAL: { anchor: STEP_ANCHOR.paypal, actor: "paypal" },
  NONE: { anchor: null, actor: null },
};

export function nextAction(stage: CaseStage, readyCount: number, excludedCount: number): NextActionKind {
  switch (stage) {
    case "EXTRACTED":
      if (readyCount > 0) return "PREPARE_PROPOSAL";
      return excludedCount > 0 ? "REVIEW_EXCEPTIONS" : "REVIEW_EXTRACTION";
    case "PROPOSED":
      return "REVIEW_AND_APPROVE";
    case "APPROVED":
      return "SUBMIT_TO_PAYPAL";
    case "SUBMISSION_UNCERTAIN":
      return "RESOLVE_SUBMISSION";
    case "SUBMITTED":
      return "REFRESH_PAYPAL";
    case "RECONCILED":
      return "NONE";
  }
}

const IDENTITY_CONFLICT_REASONS = ["CONFLICTING_SUPPLIER_IDENTITY", "CONFLICTING_INVOICE_FACTS"];

/**
 * The engine raises supplier-identity and invoice-fact conflicts as row
 * reasons (supplier_operations.py), not as report.contradictions, so both
 * have to be counted for "contradictions" to mean the same thing everywhere.
 */
export function identityConflictRows(rows: Row[]): Row[] {
  return rows.filter((row) => row.reasons.some((reason) => IDENTITY_CONFLICT_REASONS.includes(reason)));
}

export type MoneyLine = { amount: string; currency: string };

export type CaseDecision = {
  stage: CaseStage;
  action: NextActionKind;
  /** Sealed proposal total when a proposal exists; otherwise the engine's ready totals by currency. */
  amounts: MoneyLine[];
  amountBasis: "proposal" | "ready";
  suppliers: string[];
  includedCount: number;
  excludedCount: number;
  contradictionCount: number;
  extractionFailureCount: number;
  uncitedInvoiceCount: number;
  proposalDigest: string | null;
  payout: { batchId: string; providerBatchStatus: string } | null;
  submissionError: { status: number | null } | null;
};

export function projectDecision(caseData: Case): CaseDecision {
  const { report, proposal } = caseData;
  const readyRows = report.rows.filter((row) => row.status === "READY_FOR_REVIEW");
  const excludedRows = report.rows.filter((row) => row.status === "EXCLUDED");
  const amounts: MoneyLine[] = proposal
    ? [{ amount: proposal.totalAmount, currency: proposal.currency }]
    : Object.entries(report.metrics.readyAmountsByCurrency ?? {})
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([currency, amount]) => ({ amount, currency }));
  return {
    stage: caseData.stage,
    action: nextAction(caseData.stage, readyRows.length, excludedRows.length),
    amounts,
    amountBasis: proposal ? "proposal" : "ready",
    suppliers: Array.from(new Set(report.rows.map((row) => row.supplier).filter(Boolean))).sort(),
    includedCount: proposal ? proposal.items.length : readyRows.length,
    excludedCount: excludedRows.length,
    contradictionCount: report.contradictions.length + identityConflictRows(report.rows).length,
    extractionFailureCount: caseData.extractionErrors.length,
    uncitedInvoiceCount: report.extractedInvoices.filter((invoice) => invoice.requiresReview).length,
    proposalDigest: caseData.proposalDigest,
    payout: caseData.normalizedPayout
      ? { batchId: caseData.normalizedPayout.payoutBatchId, providerBatchStatus: caseData.normalizedPayout.providerBatchStatus }
      : null,
    submissionError: caseData.payoutError && !caseData.payoutResponse ? { status: caseData.payoutError.status } : null,
  };
}

/** Lifecycle position for the compact stage indicator (uncertain sits on the PayPal slot). */
export const LIFECYCLE: CaseStage[] = ["EXTRACTED", "PROPOSED", "APPROVED", "SUBMITTED", "RECONCILED"];

export function lifecycleIndex(stage: CaseStage): number {
  return stage === "SUBMISSION_UNCERTAIN" ? LIFECYCLE.indexOf("SUBMITTED") : LIFECYCLE.indexOf(stage);
}

// ---------------------------------------------------------------- dashboard

export function summaryContradictionCount(summary: CaseSummary): number {
  return summary.contradictionCount + (summary.identityConflictCount ?? 0);
}

export function summaryNextAction(summary: CaseSummary): NextActionKind {
  return nextAction(summary.stage, summary.metrics.readyCount, summary.metrics.excludedCount);
}

export function summaryAmounts(summary: CaseSummary): MoneyLine[] {
  return Object.entries(summary.metrics.readyAmountsByCurrency ?? {})
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([currency, amount]) => ({ amount, currency }));
}

export const VIEW_IDS = ["all", "needsReview", "awaitingApproval", "submitted", "uncertain", "reconciled"] as const;
export type ViewId = (typeof VIEW_IDS)[number];

/**
 * Every dashboard count is `cases.filter(VIEW_PREDICATE[view]).length`, and
 * selecting the tile applies that same predicate to the list -- a metric
 * can never show a number its own filter does not reproduce. Views overlap
 * on purpose (a reconciled case can still carry excluded invoices).
 */
export const VIEW_PREDICATE: Record<ViewId, (summary: CaseSummary) => boolean> = {
  all: () => true,
  needsReview: (s) => s.metrics.excludedCount > 0 || summaryContradictionCount(s) > 0,
  awaitingApproval: (s) => s.stage === "PROPOSED",
  submitted: (s) => s.stage === "SUBMITTED",
  uncertain: (s) => s.stage === "SUBMISSION_UNCERTAIN",
  reconciled: (s) => s.stage === "RECONCILED",
};

export function isViewId(value: unknown): value is ViewId {
  return typeof value === "string" && (VIEW_IDS as readonly string[]).includes(value);
}

export const DATE_RANGES = ["any", "24h", "7d", "30d"] as const;
export type DateRange = (typeof DATE_RANGES)[number];

const RANGE_MS: Record<Exclude<DateRange, "any">, number> = {
  "24h": 24 * 3600 * 1000,
  "7d": 7 * 24 * 3600 * 1000,
  "30d": 30 * 24 * 3600 * 1000,
};

export function withinRange(iso: string, range: DateRange, now: number): boolean {
  if (range === "any") return true;
  const created = Date.parse(iso);
  if (Number.isNaN(created)) return false;
  return now - created <= RANGE_MS[range];
}
