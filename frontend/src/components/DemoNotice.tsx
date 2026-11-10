"use client";

import { Film } from "lucide-react";
import { useI18n } from "@/lib/i18n";

/** Rendered on every page while DURIN_DEMO_SNAPSHOT=1: the data is a recording, not a live backend. */
export function DemoNotice({ recordedOn }: { recordedOn: string }) {
  const { t } = useI18n();
  return (
    <div role="status" className="print-hidden border-b border-state-review/20 bg-state-reviewBg text-state-review">
      <p className="mx-auto flex max-w-6xl items-start gap-2 px-5 py-2 text-[12.5px] leading-snug">
        <Film className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        <span>
          <strong className="font-semibold">{t("demo.title")}</strong> {t("demo.desc")} {recordedOn}. {t("demo.actions")}
        </span>
      </p>
    </div>
  );
}
