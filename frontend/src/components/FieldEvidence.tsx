"use client";

import { cn } from "@/lib/utils";
import { useI18n, type Key } from "@/lib/i18n";
import type { ExtractedInvoice } from "@/lib/types";

const FIELD_ORDER = ["supplier", "invoiceNumber", "amount", "currency", "recipient", "dueDate", "concept"];

/** What the model extracted, each value next to the exact excerpt that grounds it. */
export function FieldEvidence({ invoice }: { invoice: ExtractedInvoice }) {
  const { t } = useI18n();
  return (
    <div className="overflow-hidden rounded-xl border border-ink-900/[0.07]">
      <table className="w-full text-left text-[13px]">
        <tbody>
          {FIELD_ORDER.map((field) => {
            const entry = invoice.provenance[field];
            if (!entry) return null;
            const supported = entry.provenance.validationStatus === "SUPPORTED";
            return (
              <tr key={field} className="border-b border-ink-900/[0.05] last:border-0">
                <td className="w-32 px-3 py-2 align-top text-[12px] font-medium text-ink-500">{t(`field.${field}` as Key)}</td>
                <td className="px-3 py-2 align-top font-medium text-ink-900">{entry.value}</td>
                <td className="px-3 py-2 align-top">
                  <span className={cn("block font-mono text-[11.5px]", supported ? "text-ink-500" : "text-state-review")}>
                    &ldquo;{entry.provenance.evidenceExcerpt || "—"}&rdquo;
                  </span>
                </td>
                <td className="px-3 py-2 text-right align-top">
                  <span
                    className={cn(
                      "rounded-full px-2 py-0.5 text-[10.5px] font-semibold uppercase tracking-wide",
                      supported ? "bg-state-readyBg text-state-ready" : "bg-state-reviewBg text-state-review",
                    )}
                  >
                    {supported ? t("evidence.cited") : t("evidence.uncited")}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
