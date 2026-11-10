"use client";

import { Bot, Cog, FileText, UserCheck, Landmark, type LucideIcon } from "lucide-react";
import { useI18n, type Key } from "@/lib/i18n";
import type { Actor } from "@/lib/decision";

const ICON: Record<Actor, LucideIcon> = { source: FileText, ai: Bot, engine: Cog, human: UserCheck, paypal: Landmark };

const ORDER: Actor[] = ["ai", "engine", "human", "paypal"];

/** Who owns a step. Deliberately neutral in colour: colour is reserved for states. */
export function ActorChip({ actor }: { actor: Actor }) {
  const { t } = useI18n();
  const Icon = ICON[actor];
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-ink-900/10 bg-white px-2 py-0.5 text-[10.5px] font-semibold uppercase tracking-wide text-ink-700">
      <Icon className="h-3 w-3" aria-hidden="true" />
      {t(`actorChip.${actor}` as Key)}
    </span>
  );
}

/** The ownership boundary, kept visible inside the case instead of only on the landing page. */
export function ActorLegend() {
  const { t } = useI18n();
  return (
    <ul aria-label={t("actors.legend")} className="m-0 flex list-none flex-wrap items-center gap-x-4 gap-y-1.5 p-0 text-[12px] text-ink-700">
      {ORDER.map((actor) => {
        const Icon = ICON[actor];
        return (
          <li key={actor} className="inline-flex items-center gap-1.5">
            <Icon className="h-3.5 w-3.5 text-ink-500" aria-hidden="true" />
            {t(`actor.${actor}` as Key)}
          </li>
        );
      })}
    </ul>
  );
}
