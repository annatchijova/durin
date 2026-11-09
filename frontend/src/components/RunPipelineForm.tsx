"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Play } from "lucide-react";
import { useI18n } from "@/lib/i18n";

export function RunPipelineForm() {
  const router = useRouter();
  const { t } = useI18n();
  const [sourceDir, setSourceDir] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    startTransition(async () => {
      const response = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sourceDir: sourceDir.trim() || undefined }),
      });
      const data = await response.json().catch(() => ({ error: response.statusText }));
      if (!response.ok) {
        setError(data.error ?? t("action.genericError"));
        return;
      }
      router.push(`/cases/${encodeURIComponent(data.reportId)}`);
    });
  };

  return (
    <form onSubmit={onSubmit} className="card-solid rounded-2xl p-5 shadow-soft">
      <h2 className="text-[14px] font-semibold text-ink-900">{t("runForm.title")}</h2>
      <p className="mt-1 text-[12.5px] text-ink-500">{t("runForm.hint")}</p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <input
          type="text"
          value={sourceDir}
          onChange={(e) => setSourceDir(e.target.value)}
          placeholder={t("runForm.placeholder")}
          className="field-input max-w-sm"
        />
        <button type="submit" disabled={isPending} className="btn-primary inline-flex min-h-[38px] items-center gap-2 rounded-full px-4 text-[13px] font-semibold">
          {isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
          {isPending ? t("runForm.submitting") : t("runForm.submit")}
        </button>
      </div>
      {error && <p className="mt-2 text-[12px] text-state-exception">{error}</p>}
    </form>
  );
}
