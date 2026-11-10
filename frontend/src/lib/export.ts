// Export helpers. Everything here is a projection of data the engine
// already stored (same discipline as lib/decision.ts): a CSV row is the
// stored fields of one invoice row or one case summary, nothing is
// re-computed or summed, and amounts stay the engine's strings. The PDF
// path is the browser's print dialog over the page's print stylesheet
// (globals.css `@media print`), the same approach /vertice uses, so the
// document a merchant files is exactly what the screen showed.

import type { Case, CaseSummary } from "./types";
import { summaryAmounts, summaryContradictionCount, summaryNextAction } from "./decision";

type Cell = string | number | null | undefined;

/** RFC 4180 cell quoting; a leading =,+,-,@ is prefixed so spreadsheets do not treat it as a formula. */
function csvCell(value: Cell): string {
  if (value === null || value === undefined) return "";
  let text = String(value);
  if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`;
  if (/[",\r\n]/.test(text)) text = `"${text.replace(/"/g, '""')}"`;
  return text;
}

export function toCsv(header: string[], rows: Cell[][]): string {
  const lines = [header, ...rows].map((row) => row.map(csvCell).join(","));
  // BOM so Excel opens UTF-8 (accented supplier names) correctly.
  return `﻿${lines.join("\r\n")}\r\n`;
}

export const CASE_ROWS_HEADER = [
  "reportId",
  "stage",
  "invoiceId",
  "supplier",
  "invoiceNumber",
  "recipient",
  "amount",
  "currency",
  "dueDate",
  "status",
  "operationState",
  "reasons",
  "failedChecks",
  "sourceId",
  "sourceHash",
  "requiresReview",
  "proposalDigest",
  "approverId",
  "payoutBatchId",
  "providerBatchStatus",
];

/** One line per engine row (ready or excluded), joined with the extraction provenance of its invoice. */
export function caseRowsCsv(caseData: Case): string {
  const byInvoice = new Map(caseData.report.extractedInvoices.map((invoice) => [invoice.invoiceId, invoice]));
  const rows = caseData.report.rows.map((row) => {
    const invoice = byInvoice.get(row.invoiceId);
    const anyField = invoice ? Object.values(invoice.provenance)[0] : undefined;
    return [
      caseData.reportId,
      caseData.stage,
      row.invoiceId,
      row.supplier,
      row.invoiceNumber,
      row.recipient,
      row.amount,
      row.currency,
      row.dueDate ?? "",
      row.status,
      row.operationState,
      row.reasons.join("; "),
      row.checks.filter((check) => check.status !== "pass").map((check) => `${check.key}:${check.status}`).join("; "),
      anyField?.provenance.sourceId ?? "",
      anyField?.provenance.sourceHash ?? "",
      invoice ? String(invoice.requiresReview) : "",
      caseData.proposalDigest ?? "",
      caseData.authorization?.approverId ?? "",
      caseData.normalizedPayout?.payoutBatchId ?? "",
      caseData.normalizedPayout?.providerBatchStatus ?? "",
    ];
  });
  return toCsv(CASE_ROWS_HEADER, rows);
}

export const CASES_HEADER = [
  "reportId",
  "createdAt",
  "stage",
  "nextAction",
  "suppliers",
  "invoiceCount",
  "readyCount",
  "excludedCount",
  "contradictions",
  "readyAmounts",
];

/** One line per case in the dashboard, with the same counts the tiles show. */
export function casesCsv(cases: CaseSummary[]): string {
  const rows = cases.map((summary) => [
    summary.reportId,
    summary.createdAt,
    summary.stage,
    summaryNextAction(summary),
    (summary.suppliers ?? []).join("; "),
    summary.metrics.invoiceCount,
    summary.metrics.readyCount,
    summary.metrics.excludedCount,
    summaryContradictionCount(summary),
    summaryAmounts(summary)
      .map((line) => `${line.amount} ${line.currency}`)
      .join("; "),
  ]);
  return toCsv(CASES_HEADER, rows);
}

export function downloadText(filename: string, text: string, mime = "text/csv;charset=utf-8"): void {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  // Revoke after the click has been dispatched; some browsers read the URL asynchronously.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** File-safe stamp from an ISO timestamp: 2026-11-09T14:51:04Z -> 20261109-1451. */
export function fileStamp(iso: string): string {
  const match = iso.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
  return match ? `${match[1]}${match[2]}${match[3]}-${match[4]}${match[5]}` : "export";
}
