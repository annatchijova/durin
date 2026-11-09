"use client";

import { motion } from "framer-motion";
import { FileText, Sparkles, ShieldAlert, ShieldCheck, CircleCheck } from "lucide-react";
import { useI18n } from "@/lib/i18n";

const STEPS = [
  { icon: FileText, labelKey: "hero.step1Label" as const, subKey: "hero.step1Sub" as const },
  { icon: Sparkles, labelKey: "hero.step2Label" as const, subKey: "hero.step2Sub" as const },
  { icon: ShieldAlert, labelKey: "hero.step3Label" as const, subKey: "hero.step3Sub" as const },
  { icon: ShieldCheck, labelKey: "hero.step4Label" as const, subKey: "hero.step4Sub" as const },
];

const GLYPHS = ["INV-2026-001", "42.50 USD", "SUCCESS", "sb-…paypal.com"];

/**
 * The hero panel's animated pipeline is the same six-step journey the
 * journey page renders with real data (CaseJourneyView.tsx) -- compressed
 * to four beats here. It is not a separate claim; it is the same promise,
 * shown before the merchant has a case to look at yet.
 */
export function DurinHeroVisual() {
  const { t } = useI18n();
  return (
    <div className="relative">
      {GLYPHS.map((g, i) => (
        <motion.span
          key={g}
          initial={{ opacity: 0 }}
          animate={{ opacity: [0, 0.5, 0], y: [8, -18] }}
          transition={{ duration: 7 + i, repeat: Infinity, delay: i * 0.9, ease: "easeInOut" }}
          className="pointer-events-none absolute z-0 hidden font-mono text-[11px] text-brand/40 md:block"
          style={{ left: `${8 + i * 22}%`, top: `${16 + (i % 2) * 42}%` }}
        >
          {g}
        </motion.span>
      ))}

      <div className="card-solid shadow-lift relative z-10 rounded-3xl p-2">
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#0B1220] via-[#0F2A52] to-[#003087] p-6">
          <motion.div
            animate={{ scale: [1, 1.06, 1], opacity: [0.85, 1, 0.85] }}
            transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
            className="absolute -right-10 -top-12 h-44 w-44 rounded-full bg-brand/25 blur-2xl"
          />
          <div className="absolute -left-8 -bottom-10 h-36 w-36 rounded-full bg-brand-light/15 blur-2xl" />

          <div className="relative">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-white/10 text-white">
                  <CircleCheck className="h-4.5 w-4.5" />
                </span>
                <div>
                  <p className="text-[14px] font-extrabold tracking-tight text-white">DURIN-DEMO</p>
                  <p className="text-[10.5px] font-semibold uppercase tracking-[0.1em] text-white/50">{t("hero.sealedCase")}</p>
                </div>
              </div>
              <motion.span
                animate={{ opacity: [1, 0.4, 1] }}
                transition={{ duration: 2.4, repeat: Infinity }}
                className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-2.5 py-1 text-[10.5px] font-bold uppercase tracking-wide text-white/90"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                {t("hero.live")}
              </motion.span>
            </div>

            <div className="mt-7 space-y-2.5">
              {STEPS.map((s, i) => {
                const Icon = s.icon;
                return (
                  <motion.div
                    key={s.labelKey}
                    initial={{ opacity: 0, x: -14 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 + i * 0.18, duration: 0.5, ease: "easeOut" }}
                    className="flex items-center gap-3 rounded-xl bg-white/[0.06] px-3 py-2.5"
                  >
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-white/10 text-white">
                      <Icon className="h-3.5 w-3.5" />
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-[12.5px] font-semibold text-white">{t(s.labelKey)}</p>
                      <p className="truncate text-[10.5px] text-white/50">{t(s.subKey)}</p>
                    </div>
                    {i === STEPS.length - 1 && (
                      <motion.span
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: 0.2 + STEPS.length * 0.18 + 0.2 }}
                        className="ml-auto rounded-full bg-emerald-400/20 px-2 py-0.5 text-[10px] font-bold text-emerald-300"
                      >
                        SUCCESS
                      </motion.span>
                    )}
                  </motion.div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
