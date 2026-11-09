"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Loader2, ShieldCheck } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { formatMoney } from "@/lib/utils";

export function ApproveForm({ reportId, totalAmount, currency }: { reportId: string; totalAmount: string; currency: string }) {
  const router = useRouter();
  const { t } = useI18n();
  const [approverId, setApproverId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!approverId.trim()) {
      setError(t("approve.required"));
      return;
    }
    setError(null);
    startTransition(async () => {
      const response = await fetch(`/api/cases/${encodeURIComponent(reportId)}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approverId: approverId.trim() }),
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
    <form onSubmit={onSubmit} className="rounded-xl border border-ink-900/[0.08] bg-white p-4">
      <p className="text-[13px] text-ink-700">
        {t("approve.description")} <strong className="font-semibold text-ink-900">{formatMoney(totalAmount, currency)}</strong>. {t("approve.note")}
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <input
          type="text"
          value={approverId}
          onChange={(e) => setApproverId(e.target.value)}
          placeholder={t("approve.placeholder")}
          className="field-input max-w-[260px]"
        />
        <button type="submit" disabled={isPending} className="btn-primary inline-flex min-h-[38px] items-center gap-2 rounded-full px-4 text-[13px] font-semibold">
          {isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShieldCheck className="h-3.5 w-3.5" />}
          {t("approve.submit")}
        </button>
      </div>
      {error && <p className="mt-1.5 text-[12px] text-state-exception">{error}</p>}
    </form>
  );
}
