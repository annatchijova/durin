"use client";

import type { ReactNode } from "react";
import { useI18n } from "@/lib/i18n";
import type { Case } from "@/lib/types";
import type { Actor } from "@/lib/decision";
import { formatDate, formatMoney, shortHash } from "@/lib/utils";
import { ActorChip } from "./ActorChip";

type ActivityEvent = { key: string; title: string; detail: ReactNode; at: string | null; actor: Actor; raw: unknown };

function str(value: unknown): string | null {
  return typeof value === "string" && value ? value : null;
}

/**
 * A calm, collapsed trace of the case. Every entry is rendered from a
 * structured record already stored on the case (never from model text), in
 * the order api_server.py's lifecycle enforces, and carries its raw record
 * behind a second disclosure. A timestamp is shown only when the record
 * itself has one; the backend does not timestamp individual submit/refresh
 * attempts, and this view says so rather than inventing a time.
 */
export function ActivityLog({ caseData }: { caseData: Case }) {
  const { t, lang } = useI18n();
  const { report, proposal, authorization, normalizedPayout } = caseData;
  const batchHeader = (caseData.payoutResponse?.batch_header ?? null) as Record<string, unknown> | null;

  const events: ActivityEvent[] = [
    {
      key: "intake",
      title: t("activity.intake"),
      detail: `${report.sourceManifest.length} ${t("journey.sources")}`,
      at: report.observedAt,
      actor: "source",
      raw: report.sourceManifest,
    },
    {
      key: "extraction",
      title: t("activity.extraction"),
      detail: `${report.extraction.extractedCount} ${t("activity.extracted")} · ${report.extraction.rejectedExtractionCount + caseData.extractionErrors.length} ${t("activity.rejected")} · ${report.extraction.extractorVersion}`,
      at: caseData.createdAt,
      actor: "ai",
      raw: { extraction: report.extraction, extractionErrors: caseData.extractionErrors },
    },
    {
      key: "verification",
      title: t("activity.verification"),
      detail: `${report.metrics.readyCount} ${t("caseCard.ready")} · ${report.metrics.excludedCount} ${t("caseCard.excluded")}`,
      at: report.observedAt,
      actor: "engine",
      raw: { metrics: report.metrics, contradictions: report.contradictions },
    },
  ];

  if (proposal) {
    events.push({
      key: "proposal",
      title: t("activity.proposal"),
      detail: (
        <>
          {proposal.items.length} {t("activity.items")} · {formatMoney(proposal.totalAmount, proposal.currency)} ·{" "}
          <span className="font-mono">{shortHash(caseData.proposalDigest ?? "", 8)}</span>
        </>
      ),
      at: proposal.createdAt,
      actor: "engine",
      raw: { proposalDigest: caseData.proposalDigest, proposal },
    });
  }
  if (authorization) {
    events.push({
      key: "authorization",
      title: t("activity.authorization"),
      detail: (
        <>
          {authorization.approverId} · <span className="font-mono">{authorization.authorizationId}</span>
        </>
      ),
      at: authorization.approvedAt,
      actor: "human",
      // The proof is an HMAC the engine checks before building a payout; it
      // is not something a reader can verify by eye, so it is left out here.
      raw: { ...authorization, authorizationProof: undefined },
    });
  }
  if (caseData.payoutError) {
    events.push({
      key: "submitFailed",
      title: t("activity.submitFailed"),
      detail: `${t("journey.step6.httpStatus")} ${caseData.payoutError.status ?? t("journey.step6.noStatus")}`,
      at: null,
      actor: "paypal",
      raw: caseData.payoutError,
    });
  }
  if (batchHeader) {
    events.push({
      key: "submitted",
      title: t("activity.submitted"),
      detail: <span className="font-mono">{str(batchHeader.payout_batch_id) ?? "—"}</span>,
      at: str(batchHeader.time_created),
      actor: "paypal",
      raw: caseData.payoutRequest,
    });
  }
  if (normalizedPayout) {
    events.push({
      key: "providerState",
      title: t("activity.providerState"),
      detail: `${normalizedPayout.providerBatchStatus} · ${normalizedPayout.items.length} ${t("activity.items")}`,
      at: batchHeader ? str(batchHeader.time_completed) : null,
      actor: "paypal",
      raw: normalizedPayout,
    });
  }
  if (caseData.reconciledRows) {
    events.push({
      key: "reconciled",
      title: t("activity.reconciled"),
      detail: caseData.reconciledRows.map((row) => `${row.invoiceNumber}: ${row.operationState}`).join(" · "),
      at: null,
      actor: "engine",
      raw: caseData.reconciledRows,
    });
  }

  return (
    <section aria-labelledby="activity-title">
      <details className="card-solid group rounded-2xl shadow-soft">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 rounded-2xl px-5 py-4 [&::-webkit-details-marker]:hidden">
          <h2 id="activity-title" className="text-[16px] font-semibold text-ink-900">
            {t("activity.title")}
          </h2>
          <span className="font-mono text-[12px] text-ink-500">
            {events.length} <span aria-hidden="true" className="ml-1 inline-block transition-transform group-open:rotate-90">›</span>
          </span>
        </summary>
        <div className="border-t border-ink-900/[0.07] px-5 pb-5 pt-3">
          <p className="text-[12.5px] text-ink-500">{t("activity.subtitle")}</p>
          <ol className="m-0 mt-3 flex list-none flex-col gap-3 p-0">
            {events.map((event) => (
              <li key={event.key} className="rounded-xl border border-ink-900/[0.07] px-3.5 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[13.5px] font-semibold text-ink-900">{event.title}</span>
                  <ActorChip actor={event.actor} />
                  <span className="ml-auto font-mono text-[11.5px] text-ink-500">{event.at ? formatDate(event.at, lang) : t("activity.noTime")}</span>
                </div>
                <p className="mt-1 text-[12.5px] text-ink-700 [overflow-wrap:anywhere]">{event.detail}</p>
                <details className="mt-2">
                  <summary className="cursor-pointer text-[12px] font-semibold text-ink-700">{t("activity.raw")}</summary>
                  <pre className="mt-2 max-h-72 overflow-auto rounded-lg bg-ink-900/[0.04] p-3 font-mono text-[11px] leading-relaxed text-ink-700" tabIndex={0}>
                    {JSON.stringify(event.raw, null, 2)}
                  </pre>
                </details>
              </li>
            ))}
          </ol>
        </div>
      </details>
    </section>
  );
}
