import type { ReactNode } from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

type StepState = "done" | "active" | "todo";
type Tone = "ready" | "exception" | "review" | "neutral";

const TONE_RING: Record<Tone, string> = {
  ready: "ring-state-ready/30 bg-state-readyBg text-state-ready",
  exception: "ring-state-exception/30 bg-state-exceptionBg text-state-exception",
  review: "ring-state-review/30 bg-state-reviewBg text-state-review",
  neutral: "",
};

export function JourneyStep({
  index,
  title,
  meta,
  state,
  tone = "neutral",
  isLast = false,
  children,
}: {
  index: number;
  title: string;
  meta?: string;
  state: StepState;
  tone?: Tone;
  isLast?: boolean;
  children?: ReactNode;
}) {
  return (
    <li className="relative grid grid-cols-[28px_1fr] gap-4 pb-8 last:pb-0">
      {!isLast && <span className="absolute left-[13px] top-7 h-[calc(100%-12px)] w-px bg-ink-900/10" />}
      <span
        className={cn(
          "relative z-10 mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 text-[12px] font-bold",
          state === "done" && tone === "neutral" && "border-ink-900 bg-ink-900 text-white",
          state === "done" && tone !== "neutral" && cn("border-current", TONE_RING[tone]),
          state === "active" && "border-brand bg-white text-brand shadow-[0_0_0_4px_rgba(0,112,224,0.12)]",
          state === "todo" && "border-ink-900/15 bg-white text-ink-400",
        )}
      >
        {state === "done" ? <Check className="h-3.5 w-3.5" /> : index}
      </span>
      <div className="min-w-0 pt-0.5">
        <div className="flex flex-wrap items-baseline gap-2">
          <h3 className={cn("text-[15px] font-semibold", state === "todo" ? "text-ink-400" : "text-ink-900")}>{title}</h3>
          {meta && <span className="font-mono text-[11.5px] text-ink-500">{meta}</span>}
        </div>
        {children && <div className="mt-2">{children}</div>}
      </div>
    </li>
  );
}

export function JourneyTimeline({ children }: { children: ReactNode }) {
  return <ol className="m-0 list-none p-0">{children}</ol>;
}
