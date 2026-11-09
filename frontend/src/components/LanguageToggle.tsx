"use client";

import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";

export function LanguageToggle() {
  const { lang, setLang } = useI18n();
  return (
    <div className="flex items-center overflow-hidden rounded-full border border-ink-900/10 text-[11px] font-semibold">
      {(["en", "es"] as const).map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => setLang(option)}
          className={cn(
            "px-2.5 py-1 uppercase tracking-wide transition-colors",
            lang === option ? "bg-ink-900 text-white" : "text-ink-500 hover:text-ink-900",
          )}
        >
          {option}
        </button>
      ))}
    </div>
  );
}
