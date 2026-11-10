"use client";

import { ArrowDown } from "lucide-react";
import { useI18n, type Key } from "@/lib/i18n";
import { cn, formatMoney, shortHash } from "@/lib/utils";
import { classifyOperationState } from "@/lib/classify";
import { ACTION_TARGET, LIFECYCLE, STEP_ANCHOR, lifecycleIndex, type CaseDecision } from "@/lib/decision";
import { StateBadge } from "./StateBadge";

/**
 * The decision surface: what this case amounts to and the single next step.
 * It is a read-only projection (see lib/decision.ts) and holds no mutating
 * control -- the one primary action is a link to the journey step where the
 * real control sits beside its evidence. Approval and submission therefore
 * still have exactly one entry point each.
 */
export function DecisionSummary({ decision }: { decision: CaseDecision }) {
  const { t } = useI18n();
  const position = lifecycleIndex(decision.stage);
  const uncertain = decision.stage === "SUBMISSION_UNCERTAIN";
  const target = ACTION_TARGET[decision.action];

  return (
    <section aria-labelledby="decision-summary-title" className="card-solid rounded-2xl p-5 shadow-soft">
      <h2 id="decision-summary-title" className="text-[13px] font-semibold uppercase tracking-wide text-ink-500">
        {t("summary.title")}
      </h2>

      <div className="mt-3">
        <p className="text-[12px] text-ink-500">
          {t("summary.stage")} {position + 1} {t("summary.of")} {LIFECYCLE.length}
        </p>
        <p className={cn("text-[15px] font-semibold", uncertain ? "text-state-exception" : "text-ink-900")}>{t(`stage.${decision.stage}` as Key)}</p>
        <div aria-hidden="true" className="mt-2 flex gap-1">
          {LIFECYCLE.map((stage, i) => (
            <span
              key={stage}
              className={cn(
                "h-1.5 flex-1 rounded-full",
                i > position && "bg-ink-900/10",
                i <= position && (uncertain && i === position ? "bg-state-exception" : "bg-ink-900"),
              )}
            />
          ))}
        </div>
      </div>

      <div className="mt-4 border-t border-ink-900/[0.07] pt-4">
        <p className="text-[12px] text-ink-500">{t(decision.amountBasis === "proposal" ? "summary.amount.proposal" : "summary.amount.ready")}</p>
        {decision.amounts.length > 0 ? (
          decision.amounts.map((line) => (
            <p key={line.currency} className="text-[22px] font-semibold tracking-tight text-ink-900">
              {formatMoney(line.amount, line.currency)}
            </p>
          ))
        ) : (
          <p className="text-[14px] font-medium text-ink-700">{t("summary.amount.none")}</p>
        )}
      </div>

      <dl className="m-0 mt-4 flex flex-col gap-2.5 border-t border-ink-900/[0.07] pt-4 text-[13px]">
        <Line label={t("summary.supplier")}>
          {decision.suppliers.length === 0 ? "—" : decision.suppliers.length === 1 ? decision.suppliers[0] : `${decision.suppliers.length} ${t("summary.suppliers")}`}
        </Line>
        <Line label={t("summary.invoices")}>
          {decision.includedCount} {t("summary.included")}
          {" · "}
          {decision.excludedCount > 0 ? (
            <a href={`#${STEP_ANCHOR.exceptions}`} className="font-semibold text-state-exception underline underline-offset-2">
              {decision.excludedCount} {t("summary.excluded")}
            </a>
          ) : (
            <>0 {t("summary.excluded")}</>
          )}
        </Line>
        <Line label={t("summary.contradictions")}>
          {decision.contradictionCount > 0 ? (
            <a href={`#${STEP_ANCHOR.contradictions}`} className="font-semibold text-state-review underline underline-offset-2">
              {decision.contradictionCount}
            </a>
          ) : (
            "0"
          )}
        </Line>
        {decision.extractionFailureCount > 0 && (
          <Line label={t("summary.extractionFailures")}>
            <a href={`#${STEP_ANCHOR.extraction}`} className="font-semibold text-state-exception underline underline-offset-2">
              {decision.extractionFailureCount}
            </a>
          </Line>
        )}
        {decision.uncitedInvoiceCount > 0 && (
          <Line label={t("summary.uncited")}>
            <a href={`#${STEP_ANCHOR.extraction}`} className="font-semibold text-state-review underline underline-offset-2">
              {decision.uncitedInvoiceCount}
            </a>
          </Line>
        )}
        {decision.proposalDigest && (
          <Line label={t("summary.digest")}>
            <a href={`#${STEP_ANCHOR.proposal}`} title={decision.proposalDigest} className="font-mono text-[12px] text-ink-700 underline underline-offset-2">
              {shortHash(decision.proposalDigest, 8)}
            </a>
          </Line>
        )}
        {decision.payout && (
          <Line label={t("summary.paypal")}>
            <StateBadge size="sm" state={classifyOperationState(decision.payout.providerBatchStatus)} label={decision.payout.providerBatchStatus} />
          </Line>
        )}
        {decision.submissionError && (
          <Line label={t("summary.paypal")}>
            <StateBadge size="sm" state="exception" label={t("summary.submissionError")} />
          </Line>
        )}
      </dl>

      <div className="mt-4 border-t border-ink-900/[0.07] pt-4">
        <p className="text-[12px] text-ink-500">{t("summary.next")}</p>
        {target.anchor ? (
          <a
            href={`#${target.anchor}`}
            onClick={() => {
              // The hash alone scrolls only when there is room to scroll; on a short case
              // nothing visibly happened. Move focus to the step heading so the
              // target is highlighted (globals.css :target) and announced.
              const heading = document.getElementById(target.anchor!);
              heading?.focus({ preventScroll: true });
              heading?.scrollIntoView({ block: "start", behavior: "smooth" });
            }}
            className="btn-primary mt-1.5 inline-flex min-h-[40px] w-full items-center justify-center gap-2 rounded-full px-4 text-[13.5px] font-semibold"
          >
            {t(`next.${decision.action}` as Key)}
            <ArrowDown className="h-3.5 w-3.5" aria-hidden="true" />
          </a>
        ) : (
          <p className="mt-1 text-[14px] font-semibold text-ink-900">{t("next.NONE")}</p>
        )}
        {target.actor && (
          <p className="mt-2 text-[12px] text-ink-500">
            {t("summary.doneBy")} {t(`actor.${target.actor}` as Key)}
          </p>
        )}
        <p className="mt-2 text-[11.5px] leading-snug text-ink-500">{t("summary.note")}</p>
      </div>
    </section>
  );
}

function Line({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-ink-500">{label}</dt>
      <dd className="m-0 min-w-0 text-right font-medium text-ink-900 [overflow-wrap:anywhere]">{children}</dd>
    </div>
  );
}
