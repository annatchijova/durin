"use client";

import { cn } from "@/lib/utils";
import { useI18n, type Key } from "@/lib/i18n";
import type { ExtractedInvoice } from "@/lib/types";

const FIELD_ORDER = ["supplier", "invoiceNumber", "amount", "currency", "recipient", "dueDate", "concept"];

/**
 * What the model extracted, each value next to the exact excerpt that
 * grounds it. One definition list serves every width: stacked on narrow
 * screens (label + citation state, value, excerpt), four columns from `md`
 * up. The excerpt and the cited/uncited state are the proof behind the
 * value, so nothing here may clip or scroll out of view -- long recipients
 * and emails wrap instead.
 */
export function FieldEvidence({ invoice }: { invoice: ExtractedInvoice }) {
  const { t } = useI18n();
  return (
    <dl className="m-0 rounded-xl border border-ink-900/[0.07] text-[13px]">
      {FIELD_ORDER.map((field) => {
        const entry = invoice.provenance[field];
        if (!entry) return null;
        const supported = entry.provenance.validationStatus === "SUPPORTED";
        return (
          <div
            key={field}
            className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-1 border-b border-ink-900/[0.05] px-3 py-2.5 last:border-0 md:grid-cols-[7.5rem_minmax(0,1fr)_minmax(0,1.3fr)_auto] md:items-start"
          >
            <dt className="text-[12px] font-medium text-ink-500">{t(`field.${field}` as Key)}</dt>
            <dd className="col-span-2 m-0 font-medium text-ink-900 [overflow-wrap:anywhere] md:col-span-1">{entry.value}</dd>
            <dd className={cn("col-span-2 m-0 font-mono text-[11.5px] [overflow-wrap:anywhere] md:col-span-1", supported ? "text-ink-500" : "text-state-review")}>
              <span className="sr-only">{t("evidence.excerptLabel")} </span>
              &ldquo;{entry.provenance.evidenceExcerpt || "—"}&rdquo;
            </dd>
            <dd className="col-start-2 row-start-1 m-0 justify-self-end md:col-start-4">
              <span className="sr-only">{t("evidence.statusLabel")} </span>
              <span
                className={cn(
                  "whitespace-nowrap rounded-full px-2 py-0.5 text-[10.5px] font-semibold uppercase tracking-wide",
                  supported ? "bg-state-readyBg text-state-ready" : "bg-state-reviewBg text-state-review",
                )}
              >
                {supported ? t("evidence.cited") : t("evidence.uncited")}
              </span>
            </dd>
          </div>
        );
      })}
    </dl>
  );
}
