"use client";

import { useState, useRef, useEffect } from "react";
import { MessageCircle, X, Send, Loader2, Receipt } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { cn, formatMoney } from "@/lib/utils";
import type { ChatResponse } from "@/lib/types";

type ChatTurn = { question: string; response?: ChatResponse; error?: string; pending?: boolean };

/**
 * Floating, expandable chat over PayPal's real transaction history. The
 * model only proposes search hints and narrates already-matched real
 * results (see api_server.py's /api/chat) -- the transaction chips shown
 * here are exactly what was retrieved, not a paraphrase, so the answer
 * stays checkable against the citations below it.
 */
export function ChatWidget() {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [isPending, setIsPending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const toggleRef = useRef<HTMLButtonElement>(null);

  // Keyboard contract: opening moves focus into the question field; Escape
  // (or the toggle) closes and hands focus back to the toggle, so a
  // keyboard user is never left on a control that no longer exists.
  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  const close = () => {
    setOpen(false);
    toggleRef.current?.focus();
  };

  const examples = [t("chat.example1"), t("chat.example2"), t("chat.example3")];

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: reduce ? "auto" : "smooth" });
  }, [turns, open]);

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const q = question.trim();
    if (!q || isPending) return;
    setQuestion("");
    setTurns((prev) => [...prev, { question: q, pending: true }]);
    setIsPending(true);
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      const data = await response.json();
      setTurns((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (!response.ok) {
          next[next.length - 1] = { ...last, pending: false, error: data.error ?? t("action.genericError") };
        } else {
          next[next.length - 1] = { ...last, pending: false, response: data as ChatResponse };
        }
        return next;
      });
    } catch {
      setTurns((prev) => {
        const next = [...prev];
        next[next.length - 1] = { ...next[next.length - 1], pending: false, error: t("action.genericError") };
        return next;
      });
    } finally {
      setIsPending(false);
    }
  };

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col items-end gap-3">
      {open && (
        <div
          id="durin-chat-panel"
          role="dialog"
          aria-labelledby="durin-chat-title"
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              event.stopPropagation();
              close();
            }
          }}
          className="flex h-[min(480px,calc(100dvh-6.5rem))] w-[min(360px,calc(100vw-2.5rem))] flex-col overflow-hidden rounded-2xl border border-ink-900/10 bg-white shadow-lift"
        >
          <div className="border-b border-ink-900/[0.07] px-4 py-3">
            <p id="durin-chat-title" className="text-[13.5px] font-semibold text-ink-900">
              {t("chat.title")}
            </p>
            <p className="text-[11.5px] text-ink-500">{t("chat.subtitle")}</p>
          </div>

          <div ref={scrollRef} aria-live="polite" className="flex-1 overflow-y-auto px-4 py-3">
            {turns.length === 0 && (
              <div className="flex flex-col gap-3">
                <p className="text-[12.5px] text-ink-500">{t("chat.empty")}</p>
                <div>
                  <p className="text-[11.5px] font-semibold uppercase tracking-wide text-ink-500">{t("chat.examples")}</p>
                  {/* Examples only fill the field; the person still reads, edits and sends. */}
                  <ul className="m-0 mt-1.5 flex list-none flex-col gap-1.5 p-0">
                    {examples.map((example) => (
                      <li key={example}>
                        <button
                          type="button"
                          onClick={() => {
                            setQuestion(example);
                            inputRef.current?.focus();
                          }}
                          className="btn-ghost w-full rounded-xl px-3 py-2 text-left text-[12.5px] text-ink-700"
                        >
                          {example}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
                <p className="text-[11.5px] leading-snug text-ink-500">{t("chat.scope")}</p>
              </div>
            )}
            <div className="flex flex-col gap-4">
              {turns.map((turn, i) => (
                <div key={i} className="flex flex-col gap-2">
                  <div className="ml-auto max-w-[85%] rounded-2xl rounded-br-sm bg-ink-900 px-3 py-2 text-[12.5px] text-white">
                    {turn.question}
                  </div>
                  {turn.pending && (
                    <div className="flex items-center gap-1.5 text-[12px] text-ink-500">
                      <Loader2 className="h-3.5 w-3.5 animate-spin" /> {t("chat.sending")}
                    </div>
                  )}
                  {turn.error && <div className="rounded-xl bg-state-exceptionBg px-3 py-2 text-[12px] text-state-exception">{turn.error}</div>}
                  {turn.response && (
                    <div className="flex flex-col gap-2">
                      <div className="max-w-[90%] rounded-2xl rounded-bl-sm bg-ink-900/[0.04] px-3 py-2 text-[12.5px] text-ink-900">
                        {turn.response.answer}
                      </div>
                      {turn.response.transactions.length > 0 && (
                        <div className="flex flex-col gap-1.5">
                          {turn.response.transactions.map((txn) => (
                            <div key={txn.transactionId} className="flex items-center gap-2 rounded-lg bg-state-readyBg/50 px-2.5 py-1.5 text-[11px]">
                              <Receipt className="h-3 w-3 shrink-0 text-state-ready" />
                              <span className="truncate text-ink-700">{txn.counterpartyName || txn.counterpartyEmail || txn.transactionId}</span>
                              <span className="ml-auto shrink-0 font-mono font-semibold text-ink-900">{formatMoney(txn.amountValue, txn.currency)}</span>
                            </div>
                          ))}
                        </div>
                      )}
                      <p className="font-mono text-[10.5px] text-ink-500">
                        {turn.response.totalTransactionsScanned} {t("chat.scanned")} {t("chat.over")} {turn.response.searchedMonthsBack} {t("chat.months")}
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <form onSubmit={onSubmit} className="flex items-center gap-2 border-t border-ink-900/[0.07] p-3">
            <input
              ref={inputRef}
              type="text"
              aria-label={t("chat.inputLabel")}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={t("chat.placeholder")}
              className="field-input flex-1"
            />
            <button
              type="submit"
              disabled={isPending || !question.trim()}
              className="btn-primary flex h-9 w-9 shrink-0 items-center justify-center rounded-full disabled:opacity-40"
              aria-label={t("chat.send")}
            >
              {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </button>
          </form>
        </div>
      )}

      <button
        ref={toggleRef}
        type="button"
        onClick={() => (open ? close() : setOpen(true))}
        aria-label={open ? t("chat.close") : t("chat.open")}
        aria-expanded={open}
        aria-controls="durin-chat-panel"
        className={cn(
          "flex h-12 w-12 items-center justify-center rounded-full shadow-lift transition-transform hover:scale-105",
          open ? "bg-ink-900 text-white" : "btn-primary",
        )}
      >
        {open ? <X className="h-5 w-5" /> : <MessageCircle className="h-5 w-5" />}
      </button>
    </div>
  );
}
