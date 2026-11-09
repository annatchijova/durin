"use client";

import { PlugZap } from "lucide-react";
import { useI18n } from "@/lib/i18n";

/**
 * Shown instead of crashing when api_server.py is unreachable -- expected
 * on a provisional preview deploy (e.g. Vercel) that has no live backend
 * wired up yet. Durin never fabricates data to fill this gap; it says so.
 */
export function BackendOfflineNotice() {
  const { t } = useI18n();
  return (
    <div className="card-solid flex flex-col items-center gap-3 rounded-2xl p-10 text-center shadow-soft">
      <span className="flex h-11 w-11 items-center justify-center rounded-full bg-state-reviewBg text-state-review">
        <PlugZap className="h-5 w-5" />
      </span>
      <p className="text-[15px] font-semibold text-ink-900">{t("offline.title")}</p>
      <p className="max-w-[420px] text-[13px] leading-[1.5] text-ink-500">{t("offline.desc")}</p>
    </div>
  );
}
