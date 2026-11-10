"use client";

import { Download, Printer } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { downloadText } from "@/lib/export";

/**
 * Two export paths, both over data already on the page: a CSV file built
 * by the caller (lib/export.ts) and a PDF through the browser's print
 * dialog, which renders the page under the print stylesheet. No server
 * round-trip, so this also works in the recorded demo.
 */
export function ExportMenu({ filename, csv }: { filename: string; csv: () => string }) {
  const { t } = useI18n();
  return (
    <div className="print-hidden flex flex-wrap items-center gap-2" role="group" aria-label={t("export.label")}>
      <button
        type="button"
        onClick={() => downloadText(`${filename}.csv`, csv())}
        className="btn-ghost inline-flex min-h-[38px] items-center gap-2 rounded-full px-4 text-[13px] font-semibold"
      >
        <Download className="h-3.5 w-3.5" aria-hidden="true" />
        {t("export.csv")}
      </button>
      <button
        type="button"
        onClick={() => window.print()}
        className="btn-ghost inline-flex min-h-[38px] items-center gap-2 rounded-full px-4 text-[13px] font-semibold"
      >
        <Printer className="h-3.5 w-3.5" aria-hidden="true" />
        {t("export.pdf")}
      </button>
    </div>
  );
}
