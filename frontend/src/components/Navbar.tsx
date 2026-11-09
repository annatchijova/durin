"use client";

import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { LanguageToggle } from "./LanguageToggle";

export function Navbar() {
  const { t } = useI18n();
  return (
    <header className="nav-glass">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-5 py-3.5">
        <Link href="/" className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-ink-900 text-white">
            <ShieldCheck className="h-4.5 w-4.5" />
          </span>
          <span className="text-[15px] font-bold tracking-tight text-ink-900">Durin</span>
          <span className="hidden text-[12px] text-ink-500 sm:inline">— {t("nav.tagline")}</span>
        </Link>
        <div className="flex items-center gap-4">
          <Link href="/" className="text-[13px] font-semibold text-ink-700 hover:text-brand">
            {t("nav.cases")}
          </Link>
          <LanguageToggle />
        </div>
      </div>
    </header>
  );
}
