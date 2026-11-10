"use client";

import { useState } from "react";
import { useI18n, type Key } from "@/lib/i18n";
import type { CaseStage, CaseSummary } from "@/lib/types";
import { cn } from "@/lib/utils";
import { DATE_RANGES, VIEW_IDS, VIEW_PREDICATE, withinRange, type DateRange, type ViewId } from "@/lib/decision";
import { CaseCard } from "./CaseCard";
import { RunPipelineForm } from "./RunPipelineForm";

const STAGES: CaseStage[] = ["EXTRACTED", "PROPOSED", "APPROVED", "SUBMITTED", "SUBMISSION_UNCERTAIN", "RECONCILED"];

// Only views that mean "someone has to look at this" are tinted when non-empty.
const VIEW_TONE: Partial<Record<ViewId, string>> = {
  needsReview: "text-state-review",
  uncertain: "text-state-exception",
};

export function DashboardView({ cases, initialView = "all" }: { cases: CaseSummary[]; initialView?: ViewId }) {
  const { t } = useI18n();
  const [view, setView] = useState<ViewId>(initialView);
  const [stage, setStage] = useState<CaseStage | "any">("any");
  const [range, setRange] = useState<DateRange>("any");

  const selectView = (next: ViewId) => {
    setView(next);
    // Keep the view in the URL so a filtered queue can be bookmarked or shared.
    const url = new URL(window.location.href);
    if (next === "all") url.searchParams.delete("view");
    else url.searchParams.set("view", next);
    window.history.replaceState(null, "", url);
  };

  // `range` is "any" on first render, so Date.now() never runs during hydration.
  const now = range === "any" ? 0 : Date.now();
  const visible = cases.filter(
    (summary) => VIEW_PREDICATE[view](summary) && (stage === "any" || summary.stage === stage) && withinRange(summary.createdAt, range, now),
  );
  const filtered = view !== "all" || stage !== "any" || range !== "any";

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
        <section aria-labelledby="queue-title" className="flex flex-col gap-4">
          <h2 id="queue-title" className="text-[16px] font-semibold text-ink-900">
            {t("dashboard.queueHeading")}
          </h2>

          {/* Each tile's number is the length of the list its own filter produces. */}
          <div role="group" aria-label={t("dashboard.viewsLabel")} className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {VIEW_IDS.map((id) => {
              const count = cases.filter(VIEW_PREDICATE[id]).length;
              const selected = view === id;
              return (
                <button
                  key={id}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => selectView(id)}
                  className={cn(
                    "rounded-2xl border bg-white px-4 py-3 text-left transition-colors",
                    selected ? "border-ink-900 shadow-soft" : "border-ink-900/[0.08] hover:border-ink-900/25",
                  )}
                >
                  <span className={cn("block text-[24px] font-semibold leading-tight tracking-tight", count > 0 && VIEW_TONE[id] ? VIEW_TONE[id] : "text-ink-900")}>
                    {count}
                  </span>
                  <span className="mt-0.5 block text-[12px] font-medium text-ink-700">{t(`view.${id}` as Key)}</span>
                </button>
              );
            })}
          </div>

          <div className="flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1 text-[12px] font-medium text-ink-700">
              {t("filter.stage")}
              <select value={stage} onChange={(e) => setStage(e.target.value as CaseStage | "any")} className="field-input min-w-[170px]">
                <option value="any">{t("filter.stageAny")}</option>
                {STAGES.map((s) => (
                  <option key={s} value={s}>
                    {t(`stage.${s}` as Key)}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-[12px] font-medium text-ink-700">
              {t("filter.date")}
              <select value={range} onChange={(e) => setRange(e.target.value as DateRange)} className="field-input min-w-[170px]">
                {DATE_RANGES.map((r) => (
                  <option key={r} value={r}>
                    {t(`filter.date.${r}` as Key)}
                  </option>
                ))}
              </select>
            </label>
            {filtered && (
              <button
                type="button"
                onClick={() => {
                  selectView("all");
                  setStage("any");
                  setRange("any");
                }}
                className="btn-ghost min-h-[38px] rounded-full px-4 text-[13px] font-semibold"
              >
                {t("filter.clear")}
              </button>
            )}
            <p role="status" className="ml-auto text-[12.5px] text-ink-500">
              {t("filter.showing")} {visible.length} {t("filter.of")} {cases.length} {t("filter.cases")}
            </p>
          </div>

          {visible.length === 0 ? (
            <div className="card-solid rounded-2xl p-8 text-center shadow-soft">
              <p className="text-[14px] text-ink-500">{t("filter.noMatch")}</p>
            </div>
          ) : (
            <ul className="m-0 grid list-none grid-cols-1 gap-4 p-0 sm:grid-cols-2 lg:grid-cols-3">
              {visible.map((summary) => (
                <li key={summary.reportId} className="min-w-0">
                  <CaseCard summary={summary} />
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
