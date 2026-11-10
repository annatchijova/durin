"use client";

import Link from "next/link";
import { ArrowRight, Sparkles, ShieldCheck, FileCheck, MessageCircle, Presentation, Code2, PlayCircle } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { DurinHeroVisual } from "./DurinHeroVisual";
import { NightSeaCanvas } from "./NightSeaCanvas";

const REPO_URL = "https://github.com/annatchijova/durin";
// Set at build time on the host (NEXT_PUBLIC_DURIN_SLIDES_URL); until the deck exists the link is shown disabled, not invented.
const SLIDES_URL = process.env.NEXT_PUBLIC_DURIN_SLIDES_URL ?? "";

/**
 * Landing laid out like /vertice's start page: masthead question, lede that
 * states the problem, the three possible answers as stamps, then the links
 * a judge needs (demo, slides, repository) and a colophon. The night sea
 * (NightSeaCanvas) runs behind the whole page.
 */
export function LandingView() {
  const { t } = useI18n();

  const features = [
    { icon: FileCheck, title: t("landing.feature1.title"), desc: t("landing.feature1.desc") },
    { icon: ShieldCheck, title: t("landing.feature2.title"), desc: t("landing.feature2.desc") },
    { icon: Sparkles, title: t("landing.feature3.title"), desc: t("landing.feature3.desc") },
  ];

  const outcomes = [
    { verdict: "ready", stamp: t("landing.outcome.ready.stamp"), text: t("landing.outcome.ready.text") },
    { verdict: "exception", stamp: t("landing.outcome.exception.stamp"), text: t("landing.outcome.exception.text") },
    { verdict: "review", stamp: t("landing.outcome.review.stamp"), text: t("landing.outcome.review.text") },
  ] as const;

  return (
    <div className="landing-scene">
      <NightSeaCanvas />
      <div className="landing-content mx-auto max-w-6xl">
        <section aria-labelledby="hero-heading" className="landing-hero">
          <div className="landing-hero-main">
            <p className="landing-eyebrow">{t("landing.badge")}</p>
            <h1 id="hero-heading" className="landing-title">
              {t("landing.title1")}
              <br />
              <span className="landing-title-accent">{t("landing.title2")}</span>
            </h1>
            <p className="landing-lede">{t("landing.subtitle")}</p>

            <div className="landing-links">
              <Link href="/cases" className="btn-primary landing-link">
                <PlayCircle className="h-4 w-4" aria-hidden="true" />
                {t("landing.link.demo")}
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              {SLIDES_URL ? (
                <a href={SLIDES_URL} target="_blank" rel="noopener noreferrer" className="btn-ghost landing-link">
                  <Presentation className="h-4 w-4" aria-hidden="true" />
                  {t("landing.link.slides")}
                </a>
              ) : (
                <span className="btn-ghost landing-link landing-link-disabled" aria-disabled="true">
                  <Presentation className="h-4 w-4" aria-hidden="true" />
                  {t("landing.link.slidesSoon")}
                </span>
              )}
              <a href={REPO_URL} target="_blank" rel="noopener noreferrer" className="btn-ghost landing-link">
                <Code2 className="h-4 w-4" aria-hidden="true" />
                {t("landing.link.repo")}
              </a>
            </div>
            <p className="landing-fine">{t("landing.fine")}</p>
          </div>

          <aside className="landing-outcomes" aria-labelledby="outcomes-heading">
            <h2 id="outcomes-heading" className="landing-eyebrow">
              {t("landing.outcomes.heading")}
            </h2>
            <ul className="m-0 flex list-none flex-col gap-5 p-0">
              {outcomes.map((outcome) => (
                <li key={outcome.verdict}>
                  <p className="landing-stamp" data-verdict={outcome.verdict}>
                    {outcome.stamp}
                  </p>
                  <p className="landing-outcome-text">{outcome.text}</p>
                </li>
              ))}
            </ul>
            <p className="landing-hint">{t("landing.outcomes.hint")}</p>
          </aside>
        </section>

        <section aria-labelledby="how-heading" className="mt-6">
          <h2 id="how-heading" className="landing-eyebrow">
            {t("landing.ctaSecondary")}
          </h2>
          <div className="grid items-start gap-6 lg:grid-cols-[1fr_1fr]">
            <div className="grid gap-4">
              {features.map((f) => {
                const Icon = f.icon;
                return (
                  <div key={f.title} className="card-solid rounded-2xl p-5 shadow-soft">
                    <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand/15 text-brand-light">
                      <Icon className="h-4.5 w-4.5" />
                    </span>
                    <p className="mt-3 text-[14.5px] font-semibold">{f.title}</p>
                    <p className="landing-muted mt-1 text-[13px] leading-[1.5]">{f.desc}</p>
                  </div>
                );
              })}
            </div>
            <DurinHeroVisual />
          </div>
        </section>

        <section className="mt-10 flex flex-col items-start gap-4 rounded-3xl border border-white/10 bg-black/30 p-8 text-white backdrop-blur-sm sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.12em] text-white/50">
              <MessageCircle className="h-3.5 w-3.5" /> {t("landing.chat.eyebrow")}
            </p>
            <p className="mt-2 text-[20px] font-semibold">{t("landing.chat.title")}</p>
            <p className="mt-1.5 max-w-[520px] text-[13.5px] leading-[1.55] text-white/70">{t("landing.chat.desc")}</p>
          </div>
        </section>

        <footer className="landing-colophon">
          <p>
            Durin · Apache-2.0 ·{" "}
            <a href={REPO_URL} target="_blank" rel="noopener noreferrer">
              {t("landing.colophon")}
            </a>
          </p>
        </footer>
      </div>
    </div>
  );
}
