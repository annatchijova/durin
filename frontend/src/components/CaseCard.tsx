"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import type { CaseSummary } from "@/lib/types";
import { cn, formatDate, formatMoney } from "@/lib/utils";
import { useI18n, type Key } from "@/lib/i18n";
import { summaryAmounts, summaryContradictionCount, summaryNextAction } from "@/lib/decision";
import { StateBadge } from "./StateBadge";

/**
 * A case recognizable by its business content (who, how much, what is
 * next), with the report ID and timestamp kept as audit metadata. Every
 * value is a projection of the summary the API returned; when an older
 * backend omits the supplier list, the card falls back to the report ID
 * instead of guessing.
 */
export function CaseCard({ summary }: { summary: CaseSummary }) {
  const { t, lang } = useI18n();
  const { metrics } = summary;
  const suppliers = summary.suppliers ?? [];
  const amounts = summaryAmounts(summary);
  const contradictions = summaryContradictionCount(summary);
  const action = summaryNextAction(summary);
  const uncertain = summary.stage === "SUBMISSION_UNCERTAIN";
  const title =
    suppliers.length === 0 ? summary.reportId : suppliers.length === 1 ? suppliers[0] : `${suppliers.length} ${t("caseCard.suppliers")}`;

  return (
    <Link href={`/cases/${encodeURIComponent(summary.reportId)}`} className="card-solid card-hover flex h-full flex-col rounded-2xl p-5 shadow-soft">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className={cn("text-[15px] font-semibold text-ink-900 [overflow-wrap:anywhere]", suppliers.length === 0 && "font-mono text-[13px]")}>{title}</h3>
          {suppliers.length > 1 && <p className="mt-0.5 truncate text-[12px] text-ink-500">{suppliers.join(", ")}</p>}
        </div>
        <span
          className={cn(
            "shrink-0 rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide",
            uncertain ? "bg-state-exceptionBg text-state-exception" : "bg-ink-900/[0.05] text-ink-700",
          )}
        >
          {t(`stage.${summary.stage}` as Key)}
        </span>
      </div>

      {amounts.length > 0 && (
        <p className="mt-3 text-[13px] text-ink-500">
          {t("caseCard.readyTotal")}{" "}
          {amounts.map((line, i) => (
            <span key={line.currency}>
              {i > 0 && " · "}
              <strong className="text-[15px] font-semibold text-ink-900">{formatMoney(line.amount, line.currency)}</strong>
            </span>
          ))}
        </p>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <StateBadge state="ready" size="sm" label={`${metrics.readyCount} ${t("caseCard.ready")}`} />
        <StateBadge state="exception" size="sm" label={`${metrics.excludedCount} ${t("caseCard.excluded")}`} />
        {contradictions > 0 && <StateBadge state="review" size="sm" label={`${contradictions} ${t("caseCard.contradictions")}`} />}
      </div>

      <p className="mt-3 truncate font-mono text-[11.5px] text-ink-500">
        {suppliers.length > 0 && <>{summary.reportId} · </>}
        {formatDate(summary.createdAt, lang)}
      </p>

      <div className="mt-auto flex items-center justify-between gap-3 pt-4 text-[12.5px]">
        <span className="min-w-0 text-ink-700">
          {t("caseCard.next")} <strong className="font-semibold text-ink-900">{t(`next.${action}` as Key)}</strong>
        </span>
        <span className="inline-flex shrink-0 items-center font-semibold text-brand">
          {t("caseCard.viewJourney")} <ArrowRight className="ml-1 h-3.5 w-3.5" aria-hidden="true" />
        </span>
      </div>
    </Link>
  );
}
