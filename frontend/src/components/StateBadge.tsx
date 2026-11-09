"use client";

import { cn } from "@/lib/utils";
import { useI18n, type Key } from "@/lib/i18n";
import type { UiState } from "@/lib/classify";

const STYLE: Record<UiState, { text: string; bg: string }> = {
  ready: { text: "text-state-ready", bg: "bg-state-readyBg" },
  exception: { text: "text-state-exception", bg: "bg-state-exceptionBg" },
  review: { text: "text-state-review", bg: "bg-state-reviewBg" },
  pending: { text: "text-state-pending", bg: "bg-state-pendingBg" },
};

const STATE_KEY: Record<UiState, Key> = {
  ready: "state.ready",
  exception: "state.exception",
  review: "state.review",
  pending: "state.pending",
};

export function StateBadge({ state, size = "md", label }: { state: UiState; size?: "sm" | "md"; label?: string }) {
  const { t } = useI18n();
  const s = STYLE[state];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-semibold",
        s.text,
        s.bg,
        size === "sm" ? "px-2.5 py-0.5 text-[11px]" : "px-3 py-1 text-[12.5px]",
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", state === "pending" ? "border border-current bg-transparent" : "bg-current")} />
      {label ?? t(STATE_KEY[state])}
    </span>
  );
}
