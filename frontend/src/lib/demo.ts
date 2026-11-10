// Recorded demo mode for a static host (Vercel) with no api_server.py
// behind it. The three cases under demo-cases/ are verbatim JSON files
// written by api_server.py during real local runs on 2026-11-09 (OpenAI
// extraction, deterministic engine, PayPal sandbox payout), with one
// cosmetic edit: the local scratch directory in each source path was
// replaced by "demo-sources/". Nothing else was touched, nothing was
// composed by hand, and every mutating action is refused with a clear
// message instead of pretending to run.
//
// Enabled only by DURIN_DEMO_SNAPSHOT=1 so a developer whose backend is
// merely down still sees the honest "backend not reachable" notice.

import type { Case, CaseSummary } from "./types";
import reconciled from "./demo-cases/reconciled.json";
import exceptions from "./demo-cases/exceptions.json";
import extractionFailed from "./demo-cases/extraction-failed.json";

export const DEMO_RECORDED_ON = "2026-11-09";

export function demoEnabled(): boolean {
  return process.env.DURIN_DEMO_SNAPSHOT === "1";
}

const CASES: Case[] = [reconciled, exceptions, extractionFailed] as unknown as Case[];

const IDENTITY_CONFLICT_REASONS = new Set(["CONFLICTING_SUPPLIER_IDENTITY", "CONFLICTING_INVOICE_FACTS"]);

/** Same projection api_server.py's list endpoint applies, so the dashboard reads identically. */
function summarize(caseData: Case): CaseSummary {
  const rows = caseData.report.rows;
  return {
    reportId: caseData.reportId,
    createdAt: caseData.createdAt,
    stage: caseData.stage,
    metrics: caseData.report.metrics,
    contradictionCount: caseData.report.contradictions.length,
    identityConflictCount: rows.filter((row) => row.reasons.some((reason) => IDENTITY_CONFLICT_REASONS.has(reason))).length,
    suppliers: Array.from(new Set(rows.map((row) => row.supplier).filter(Boolean))).sort(),
  };
}

export function demoListCases(): CaseSummary[] {
  return [...CASES].sort((a, b) => b.createdAt.localeCompare(a.createdAt)).map(summarize);
}

export function demoGetCase(reportId: string): Case | undefined {
  return CASES.find((caseData) => caseData.reportId === reportId);
}
