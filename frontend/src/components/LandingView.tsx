"use client";

import Link from "next/link";
import { ArrowRight, Sparkles, ShieldCheck, FileCheck, MessageCircle } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { DurinHeroVisual } from "./DurinHeroVisual";

export function LandingView() {
  const { t } = useI18n();

  const features = [
    { icon: FileCheck, title: t("landing.feature1.title"), desc: t("landing.feature1.desc") },
    { icon: ShieldCheck, title: t("landing.feature2.title"), desc: t("landing.feature2.desc") },
    { icon: Sparkles, title: t("landing.feature3.title"), desc: t("landing.feature3.desc") },
  ];

  return (
    <div className="mx-auto max-w-5xl pb-16 pt-4">
      <div className="grid items-center gap-10 lg:grid-cols-[1.05fr_0.95fr]">
        <div>
          <div className="animate-fade-up inline-flex items-center gap-2 rounded-full border border-ink-900/8 bg-white px-2 py-1 pl-3 shadow-soft">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-brand/10 px-2.5 py-1 text-[11.5px] font-bold text-brand-deep">
              <span className="h-1.5 w-1.5 rounded-full bg-brand shadow-[0_0_0_4px_rgba(0,112,224,0.16)]" />
              {t("landing.badge")}
            </span>
          </div>

          <h1 className="animate-fade-up mt-5 text-[clamp(36px,5vw,58px)] font-semibold leading-[1.02] tracking-[-0.03em] text-ink-900">
            {t("landing.title1")}
            <br />
            <span className="bg-gradient-to-r from-brand-light to-brand-deep bg-clip-text text-transparent">{t("landing.title2")}</span>
          </h1>

          <p className="animate-fade-up mt-5 max-w-[540px] text-[17px] leading-[1.6] text-ink-700">{t("landing.subtitle")}</p>

          <div className="animate-fade-up mt-7 flex flex-wrap gap-3">
            <Link href="/cases" className="btn-primary shadow-soft inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-bold">
              {t("landing.cta")}
              <ArrowRight className="h-4 w-4" />
            </Link>
            <a href="#how" className="btn-ghost inline-flex items-center gap-2 rounded-full px-5 py-3 text-sm font-semibold">
              {t("landing.ctaSecondary")}
            </a>
          </div>
        </div>

        <DurinHeroVisual />
      </div>

      <div id="how" className="mt-20 grid gap-4 sm:grid-cols-3">
        {features.map((f) => {
          const Icon = f.icon;
          return (
            <div key={f.title} className="card-solid rounded-2xl p-5 shadow-soft">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand/10 text-brand-deep">
                <Icon className="h-4.5 w-4.5" />
              </span>
              <p className="mt-3 text-[14.5px] font-semibold text-ink-900">{f.title}</p>
              <p className="mt-1 text-[13px] leading-[1.5] text-ink-500">{f.desc}</p>
            </div>
          );
        })}
      </div>

      <div className="mt-6 flex flex-col items-start gap-4 rounded-3xl bg-ink-900 p-8 text-white sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.12em] text-white/50">
            <MessageCircle className="h-3.5 w-3.5" /> {t("landing.chat.eyebrow")}
          </p>
          <p className="mt-2 text-[20px] font-semibold">{t("landing.chat.title")}</p>
          <p className="mt-1.5 max-w-[520px] text-[13.5px] leading-[1.55] text-white/70">{t("landing.chat.desc")}</p>
        </div>
      </div>
    </div>
  );
}
