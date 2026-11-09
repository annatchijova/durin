"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import type { CaseSummary } from "@/lib/types";
import { formatDate } from "@/lib/utils";
import { useI18n, type Key } from "@/lib/i18n";
import { StateBadge } from "./StateBadge";

export function CaseCard({ summary }: { summary: CaseSummary }) {
  const { t, lang } = useI18n();
  const { metrics } = summary;
  const stageKey = `stage.${summary.stage}` as Key;

  return (
    <Link
      href={`/cases/${encodeURIComponent(summary.reportId)}`}
      className="card-solid card-hover block rounded-2xl p-5 shadow-soft"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-mono text-[12px] text-ink-500">{summary.reportId}</p>
          <p className="mt-1 text-[13px] text-ink-700">{formatDate(summary.createdAt, lang)}</p>
        </div>
        <span className="rounded-full bg-ink-900/[0.05] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-ink-700">
          {t(stageKey)}
        </span>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <StateBadge state="ready" size="sm" label={`${metrics.readyCount} ${t("caseCard.ready")}`} />
        <StateBadge state="exception" size="sm" label={`${metrics.excludedCount} ${t("caseCard.excluded")}`} />
        {summary.contradictionCount > 0 && (
          <StateBadge state="review" size="sm" label={`${summary.contradictionCount} ${t("caseCard.contradictions")}`} />
        )}
      </div>
      <div className="mt-4 flex items-center justify-end text-[12.5px] font-semibold text-brand">
        {t("caseCard.viewJourney")} <ArrowRight className="ml-1 h-3.5 w-3.5" />
      </div>
    </Link>
  );
}
