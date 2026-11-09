"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";

export function ActionButton({
  url,
  body,
  label,
  pendingLabel,
  variant = "primary",
}: {
  url: string;
  body?: Record<string, unknown>;
  label: string;
  pendingLabel?: string;
  variant?: "primary" | "ghost";
}) {
  const router = useRouter();
  const { t } = useI18n();
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const onClick = () => {
    setError(null);
    startTransition(async () => {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body ?? {}),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({ error: response.statusText }));
        setError(data.error ?? t("action.genericError"));
        return;
      }
      router.refresh();
    });
  };

  return (
    <div>
      <button
        type="button"
        onClick={onClick}
        disabled={isPending}
        className={cn(
          "inline-flex min-h-[38px] items-center gap-2 rounded-full px-4 text-[13px] font-semibold",
          variant === "primary" ? "btn-primary" : "btn-ghost",
        )}
      >
        {isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
        {isPending ? pendingLabel ?? label : label}
      </button>
      {error && <p className="mt-1.5 text-[12px] text-state-exception">{error}</p>}
    </div>
  );
}
