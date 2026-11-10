"use client";

import Link from "next/link";
import { useI18n } from "@/lib/i18n";
import type { Case } from "@/lib/types";
import { formatDate, formatMoney, shortHash } from "@/lib/utils";
import { classifyReasons, classifyOperationState } from "@/lib/classify";
import { STEP_ANCHOR, identityConflictRows as findIdentityConflictRows, projectDecision } from "@/lib/decision";
import { DecisionSummary } from "./DecisionSummary";
import { ActivityLog } from "./ActivityLog";
import { ActorChip, ActorLegend } from "./ActorChip";
import { JourneyTimeline, JourneyStep } from "./JourneyStep";
import { CheckList } from "./CheckList";
import { ContradictionPanel } from "./ContradictionPanel";
import { FieldEvidence } from "./FieldEvidence";
import { StateBadge } from "./StateBadge";
import { ActionButton } from "./ActionButton";
import { ApproveForm } from "./ApproveForm";
import { ExportMenu } from "./ExportMenu";
import { caseRowsCsv, fileStamp } from "@/lib/export";

const STAGE_ORDER = ["EXTRACTED", "PROPOSED", "APPROVED", "SUBMITTED", "SUBMISSION_UNCERTAIN", "RECONCILED"];

export function CaseJourneyView({ caseData }: { caseData: Case }) {
  const { t, lang } = useI18n();
  const { report, stage } = caseData;
  const readyRows = report.rows.filter((r) => r.status === "READY_FOR_REVIEW");
  const excludedRows = report.rows.filter((r) => r.status === "EXCLUDED");

  // The deterministic engine also catches contradictions
  // contradiction_detection.py never sees -- a conflicting supplier
  // identity or amount/currency for the same invoice number is caught in
  // supplier_operations.py's own row reasons, not in report.contradictions.
  // Surface both here so this step never says "none found" while rows
  // below are excluded for exactly this.
  const identityConflictRows = findIdentityConflictRows(report.rows);
  const decision = projectDecision(caseData);
  const totalContradictions = decision.contradictionCount;
  // A submission PayPal never confirmed is not "done": its outcome is unknown.
  const submissionUnconfirmed = decision.submissionError !== null;

  const stageIndex = STAGE_ORDER.indexOf(stage);
  const reached = (minStage: string) => stageIndex >= STAGE_ORDER.indexOf(minStage);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="font-mono text-[12px] text-ink-500 [overflow-wrap:anywhere]">{caseData.reportId}</p>
        <div className="mt-1 flex flex-wrap items-center gap-3">
          <h1 className="text-[24px] font-semibold text-ink-900">{t("journey.title")}</h1>
          <span className="text-[13px] text-ink-500">{formatDate(caseData.createdAt, lang)}</span>
        </div>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <ActorLegend />
          <ExportMenu filename={`durin-case-${fileStamp(caseData.createdAt)}`} csv={() => caseRowsCsv(caseData)} />
        </div>
      </div>

      {/* Summary first in the DOM (and on small screens); a sticky side column from lg up. */}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px] lg:items-start">
      <aside className="lg:sticky lg:top-24 lg:order-2 lg:max-h-[calc(100vh-7rem)] lg:overflow-y-auto">
        <DecisionSummary decision={decision} />
      </aside>

      <div className="flex min-w-0 flex-col gap-8 lg:order-1">
      <section aria-labelledby="journey-steps-title" className="card-solid rounded-2xl p-5 shadow-soft sm:p-6">
        <h2 id="journey-steps-title" className="sr-only">
          {t("journey.stepsHeading")}
        </h2>
        <JourneyTimeline>
          <JourneyStep id={STEP_ANCHOR.evidence} actor={<ActorChip actor="source" />} index={1} title={t("journey.step1.title")} state="done" meta={`${report.sourceManifest.length} ${t("journey.sources")}`}>
            <ul className="m-0 flex flex-col gap-1.5 p-0">
              {report.sourceManifest.map((entry) => (
                <li key={entry.sourceId} className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-lg bg-ink-900/[0.03] px-3 py-1.5 text-[12.5px]">
                  <span className="min-w-0 text-ink-700 [overflow-wrap:anywhere]">{entry.source.split("/").pop()}</span>
                  <span className="ml-auto font-mono text-ink-500">{shortHash(entry.sourceHash)}</span>
                  <StateBadge
                    size="sm"
                    state={entry.validationStatus === "EXTRACTED" ? "ready" : entry.validationStatus === "MISSING_EXTRACTION" ? "pending" : "exception"}
                    label={entry.validationStatus}
                  />
                </li>
              ))}
            </ul>
          </JourneyStep>

          <JourneyStep id={STEP_ANCHOR.extraction} actor={<ActorChip actor="ai" />} index={2} title={t("journey.step2.title")} state="done" meta={`${report.extractedInvoices.length} / ${report.extraction.rejectedExtractionCount} ${t("journey.step2.meta")}`}>
            <div className="flex flex-col gap-3">
              {report.extractedInvoices.map((invoice) => (
                <FieldEvidence key={invoice.invoiceId} invoice={invoice} />
              ))}
              {caseData.extractionErrors.length > 0 && (
                <div className="rounded-xl bg-state-exceptionBg/60 px-3 py-2 text-[12.5px] text-state-exception">
                  <p className="font-semibold">
                    {caseData.extractionErrors.length} {t("journey.step2.rejectedNote")}
                  </p>
                  <ul className="m-0 mt-1.5 flex list-none flex-col gap-1 p-0">
                    {caseData.extractionErrors.map((failure) => (
                      <li key={failure.sourceId} className="flex flex-wrap gap-x-2 [overflow-wrap:anywhere]">
                        <span className="font-mono text-[11.5px]">{failure.source.split("/").pop()}</span>
                        <span>{failure.error}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {report.extractedInvoices.length === 0 && (
                <div className="rounded-xl border border-ink-900/[0.08] bg-white p-4 text-[13px] text-ink-700">
                  <p>{t("journey.step2.nothingExtracted")}</p>
                  <Link href="/cases" className="btn-primary mt-3 inline-flex min-h-[38px] items-center rounded-full px-4 text-[13px] font-semibold">
                    {t("journey.step2.runAgain")}
                  </Link>
                </div>
              )}
            </div>
          </JourneyStep>

          <JourneyStep
            id={STEP_ANCHOR.contradictions}
            actor={<ActorChip actor="engine" />}
            index={3}
            title={t("journey.step3.title")}
            state="done"
            tone={totalContradictions > 0 ? "review" : "ready"}
            meta={`${totalContradictions} ${t("journey.step3.found")}`}
          >
            <div className="flex flex-col gap-2.5">
              {(report.contradictions.length > 0 || identityConflictRows.length === 0) && (
                <ContradictionPanel contradictions={report.contradictions} />
              )}
              {identityConflictRows.map((row) => (
                <div key={row.invoiceId} className="rounded-xl border border-state-exception/25 bg-state-exceptionBg/50 px-3.5 py-3">
                  <p className="text-[12.5px] font-semibold text-state-exception">
                    {row.reasons.includes("CONFLICTING_SUPPLIER_IDENTITY") ? t("identity.supplierConflict") : t("identity.factsConflict")}
                  </p>
                  <p className="mt-1 text-[12px] text-ink-700">
                    {row.supplier} · {row.invoiceNumber} · {formatMoney(row.amount, row.currency)} — {t("identity.excludedNote")}
                  </p>
                </div>
              ))}
            </div>
          </JourneyStep>

          <JourneyStep
            id={STEP_ANCHOR.proposal}
            actor={<ActorChip actor="engine" />}
            index={4}
            title={t("journey.step4.title")}
            state={reached("PROPOSED") ? "done" : "active"}
            meta={caseData.proposalDigest ? shortHash(caseData.proposalDigest) : undefined}
          >
            {caseData.proposal ? (
              <div className="rounded-xl border border-ink-900/[0.08] bg-white p-4">
                <p className="text-[13px] text-ink-700">
                  {caseData.proposal.items.length} {t("journey.step4.items")}{" "}
                  <strong className="font-semibold text-ink-900">{formatMoney(caseData.proposal.totalAmount, caseData.proposal.currency)}</strong>
                </p>
                <p className="mt-1 font-mono text-[11px] text-ink-500">{t("journey.step4.digest")} {shortHash(caseData.proposalDigest!, 16)}</p>
              </div>
            ) : readyRows.length > 0 ? (
              <ActionButton url={`/api/cases/${caseData.reportId}/proposal`} label={t("journey.step4.action")} pendingLabel={t("journey.step4.pending")} />
            ) : (
              <p className="text-[13px] text-ink-500">{t("journey.step4.none")}</p>
            )}
          </JourneyStep>

          <JourneyStep id={STEP_ANCHOR.approval} actor={<ActorChip actor="human" />} index={5} title={t("journey.step5.title")} state={reached("APPROVED") ? "done" : caseData.proposal ? "active" : "todo"}>
            {caseData.authorization ? (
              <div className="rounded-xl border border-ink-900/[0.08] bg-white p-4 text-[13px] text-ink-700">
                {t("journey.step5.authorizedBy")} <strong className="font-semibold text-ink-900">{caseData.authorization.approverId}</strong>{" "}
                {t("journey.step5.on")} {formatDate(caseData.authorization.approvedAt, lang)}.
                <p className="mt-1 font-mono text-[11px] text-ink-500">authorizationId {caseData.authorization.authorizationId}</p>
              </div>
            ) : caseData.proposal ? (
              <ApproveForm reportId={caseData.reportId} totalAmount={caseData.proposal.totalAmount} currency={caseData.proposal.currency} />
            ) : (
              <p className="text-[13px] text-ink-500">{t("journey.step5.waiting")}</p>
            )}
          </JourneyStep>

          <JourneyStep
            id={STEP_ANCHOR.paypal}
            actor={<ActorChip actor="paypal" />}
            index={6}
            title={t("journey.step6.title")}
            state={submissionUnconfirmed ? "attention" : reached("SUBMITTED") ? "done" : caseData.authorization ? "active" : "todo"}
            isLast
          >
            {caseData.normalizedPayout ? (
              <div className="flex flex-col gap-3">
                <div className="rounded-xl border border-ink-900/[0.08] bg-white p-4 text-[13px]">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-mono text-[12px] text-ink-500 [overflow-wrap:anywhere]">{t("journey.step6.batch")} {caseData.normalizedPayout.payoutBatchId}</span>
                    <StateBadge state={classifyOperationState(caseData.normalizedPayout.providerBatchStatus)} label={caseData.normalizedPayout.providerBatchStatus} />
                  </div>
                  <ul className="mt-2 flex flex-col gap-1">
                    {caseData.normalizedPayout.items.map((item) => (
                      <li key={item.payoutItemId} className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-mono text-[11.5px] text-ink-500">{item.payoutItemId}</span>
                        <StateBadge size="sm" state={classifyOperationState(item.providerStatus)} label={item.providerStatus} />
                      </li>
                    ))}
                  </ul>
                </div>
                <ActionButton url={`/api/cases/${caseData.reportId}/refresh`} label={t("journey.step6.refresh")} variant="ghost" />
              </div>
            ) : caseData.authorization ? (
              <div className="flex flex-col gap-3">
                {submissionUnconfirmed && (
                  <div role="status" className="rounded-xl border border-state-exception/25 bg-state-exceptionBg/60 px-3.5 py-3 text-[12.5px] text-state-exception">
                    <p className="font-semibold">{t("journey.step6.uncertain")}</p>
                    <p className="mt-1 font-mono text-[11.5px]">
                      {t("journey.step6.httpStatus")} {caseData.payoutError?.status ?? t("journey.step6.noStatus")}
                    </p>
                  </div>
                )}
                <ActionButton url={`/api/cases/${caseData.reportId}/submit`} label={t("journey.step6.action")} pendingLabel={t("journey.step6.pending")} />
              </div>
            ) : (
              <p className="text-[13px] text-ink-500">{t("journey.step6.waiting")}</p>
            )}
          </JourneyStep>
        </JourneyTimeline>
      </section>

      {excludedRows.length > 0 && (
        <section aria-labelledby={STEP_ANCHOR.exceptions}>
          <h2 id={STEP_ANCHOR.exceptions} tabIndex={-1} className="scroll-mt-24 text-[16px] font-semibold text-ink-900 outline-none">
            {t("exceptions.title")}
          </h2>
          <p className="mt-1 text-[13px] text-ink-500">{t("exceptions.subtitle")}</p>
          <div className="mt-3 flex flex-col gap-3">
            {excludedRows.map((row) => (
              <div key={row.invoiceId} className="card-solid rounded-2xl p-4 shadow-soft">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-[13.5px] font-semibold text-ink-900">
                    {row.supplier} · {row.invoiceNumber} · {formatMoney(row.amount, row.currency)}
                  </span>
                  <StateBadge state={classifyReasons(row.reasons)} />
                </div>
                <div className="mt-3">
                  <CheckList checks={row.checks} />
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <ActivityLog caseData={caseData} />
      </div>
      </div>
    </div>
  );
}
