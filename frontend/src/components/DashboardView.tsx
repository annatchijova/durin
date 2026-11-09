"use client";

import { useI18n } from "@/lib/i18n";
import type { CaseSummary } from "@/lib/types";
import { CaseCard } from "./CaseCard";
import { RunPipelineForm } from "./RunPipelineForm";

export function DashboardView({ cases }: { cases: CaseSummary[] }) {
  const { t } = useI18n();
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-[26px] font-semibold text-ink-900">{t("dashboard.title")}</h1>
        <p className="mt-1 text-[14px] text-ink-500">{t("dashboard.subtitle")}</p>
      </div>

      <RunPipelineForm />

      {cases.length === 0 ? (
        <div className="card-solid rounded-2xl p-8 text-center shadow-soft">
          <p className="text-[14px] text-ink-500">{t("dashboard.empty")}</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {cases.map((summary) => (
            <CaseCard key={summary.reportId} summary={summary} />
          ))}
        </div>
      )}
    </div>
  );
}
