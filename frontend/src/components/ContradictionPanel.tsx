"use client";

import { AlertTriangle, ShieldCheck } from "lucide-react";
import type { Contradiction } from "@/lib/types";
import { useI18n, type Key } from "@/lib/i18n";

/**
 * What the model saw differently across sources describing the same
 * obligation. Nobody -- not the model, not this panel -- picks a winner;
 * both values and both source citations stay visible until a human
 * resolves it.
 */
export function ContradictionPanel({ contradictions }: { contradictions: Contradiction[] }) {
  const { t } = useI18n();
  if (contradictions.length === 0) {
    return (
      <div className="flex items-center gap-2 rounded-xl bg-state-readyBg/60 px-3.5 py-2.5 text-[13px] text-state-ready">
        <ShieldCheck className="h-4 w-4 shrink-0" />
        {t("contradiction.none")}
      </div>
    );
  }
  return (
    <ul className="m-0 flex flex-col gap-2.5 p-0">
      {contradictions.map((c, i) => {
        const fieldKey = `contradiction.field.${c.field}` as Key;
        return (
          <li key={i} className="rounded-xl border border-state-review/25 bg-state-reviewBg/50 px-3.5 py-3">
            <div className="flex items-center gap-2 text-[12.5px] font-semibold text-state-review">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
              {t(fieldKey)} {t("contradiction.mismatch")} — {c.supplier} / {c.invoiceNumber}
            </div>
            <div className="mt-2 flex flex-col gap-2">
              {c.observedValues.map((observed, j) => (
                <div key={j} className="rounded-lg bg-white/70 px-3 py-2">
                  <p className="text-[13px] font-medium text-ink-900">&ldquo;{observed.value}&rdquo;</p>
                  <ul className="mt-1 flex flex-col gap-0.5">
                    {observed.sources.map((source, k) => (
                      <li key={k} className="font-mono text-[11px] text-ink-500">
                        {t("contradiction.source")} {source.sourceId} · &ldquo;{source.evidenceExcerpt}&rdquo;
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
