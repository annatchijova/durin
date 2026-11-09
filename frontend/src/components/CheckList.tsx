"use client";

import { Check, X, AlertTriangle } from "lucide-react";
import type { CheckResult } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useI18n, type Key } from "@/lib/i18n";

export function CheckList({ checks }: { checks: CheckResult[] }) {
  const { t } = useI18n();
  return (
    <ul className="m-0 flex flex-col gap-1.5 p-0">
      {checks.map((check) => {
        const key = `check.${check.key}` as Key;
        return (
          <li
            key={check.key}
            className={cn(
              "flex items-start gap-2.5 rounded-xl px-3 py-2",
              check.status === "pass" && "bg-state-readyBg/60",
              check.status === "fail" && "bg-state-exceptionBg/60",
              check.status === "alert" && "bg-state-reviewBg/60",
            )}
          >
            <span
              className={cn(
                "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full",
                check.status === "pass" && "bg-state-ready/15 text-state-ready",
                check.status === "fail" && "bg-state-exception/15 text-state-exception",
                check.status === "alert" && "bg-state-review/15 text-state-review",
              )}
            >
              {check.status === "pass" && <Check className="h-3 w-3" />}
              {check.status === "fail" && <X className="h-3 w-3" />}
              {check.status === "alert" && <AlertTriangle className="h-3 w-3" />}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-[13px] font-medium text-ink-900">{t(key)}</span>
              <span className="block font-mono text-[11.5px] text-ink-500">{check.detail}</span>
            </span>
          </li>
        );
      })}
    </ul>
  );
}
