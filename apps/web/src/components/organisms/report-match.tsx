"use client";

import { Flag, Loader2 } from "lucide-react";
import { useEffect, useId, useRef, useState, type SubmitEvent } from "react";
import { pill } from "@/components/atoms/pill";
import { CharCounter } from "@/components/molecules/char-counter";
import { useReport } from "@/hooks/use-report";
import type { ReportKind } from "@/lib/api/client";
import { strings } from "@/lib/strings";

const t = strings.report;

const KINDS = Object.keys(t.kinds) as ReportKind[];

/**
 * "Report a wrong match": a reader says a claim was checked against the wrong
 * statistic or read wrongly, with an optional note. No account is needed. The
 * form opens in place, takes focus, and gives it back when closed; the outcome
 * is said in a status line that is always on the page, so it is read out.
 */
export function ReportMatch({
  checkId,
  claimIndex,
}: {
  checkId: string;
  claimIndex: number;
}) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<ReportKind>("wrong_series");
  const [note, setNote] = useState("");
  const { phase, error, send } = useReport(checkId, claimIndex);
  const toggle = useRef<HTMLButtonElement>(null);
  const firstChoice = useRef<HTMLInputElement>(null);
  const sending = phase === "sending";

  useEffect(() => {
    if (open) firstChoice.current?.focus();
  }, [open]);

  function close() {
    setOpen(false);
    toggle.current?.focus();
  }

  function onSubmit(e: SubmitEvent<HTMLFormElement>) {
    e.preventDefault();
    void send(kind, note);
  }

  return (
    <div className="flex flex-col gap-4 border-t pt-4">
      <p role="status" className="text-sm font-medium empty:hidden">
        {phase === "sent" ? t.thanks : null}
      </p>
      {phase !== "sent" && (
        <>
          <div>
            <button
              ref={toggle}
              type="button"
              aria-expanded={open}
              aria-controls={`${id}-form`}
              onClick={() => (open ? close() : setOpen(true))}
              className={pill({ tone: "glass" })}
            >
              <Flag className="size-4" aria-hidden />
              {t.open}
            </button>
          </div>
          {open && (
            <form
              id={`${id}-form`}
              onSubmit={onSubmit}
              className="flex flex-col gap-4"
            >
              <fieldset className="flex flex-col gap-2">
                <legend className="mb-1 text-sm font-medium">
                  {t.heading}
                </legend>
                {KINDS.map((k, i) => (
                  <label key={k} className="flex items-start gap-2 text-sm">
                    <input
                      ref={i === 0 ? firstChoice : undefined}
                      type="radio"
                      name={`${id}-kind`}
                      value={k}
                      checked={kind === k}
                      onChange={() => setKind(k)}
                      className="accent-brand mt-1 size-4"
                    />
                    {t.kinds[k]}
                  </label>
                ))}
              </fieldset>
              <div className="flex flex-col gap-1.5">
                <label htmlFor={`${id}-note`} className="text-sm font-medium">
                  {t.noteLabel}
                </label>
                <textarea
                  id={`${id}-note`}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  maxLength={t.maxNote}
                  rows={3}
                  autoComplete="off"
                  aria-describedby={`${id}-anonymous`}
                  className="bg-background/50 focus-visible:ring-ring/50 w-full rounded-xl border p-3 text-sm leading-6 outline-none focus-visible:ring-4"
                />
                <div className="flex flex-wrap items-center justify-between gap-x-3">
                  <p
                    id={`${id}-anonymous`}
                    className="text-muted-foreground text-xs"
                  >
                    {t.anonymous}
                  </p>
                  <CharCounter count={note.length} max={t.maxNote} />
                </div>
              </div>
              {error && (
                <p
                  role="alert"
                  className="text-destructive text-sm font-medium"
                >
                  {error}
                </p>
              )}
              <div className="flex flex-wrap gap-2">
                <button
                  type="submit"
                  disabled={sending}
                  className={pill({ tone: "primary" })}
                >
                  {sending ? t.sending : t.send}
                  {sending && (
                    <Loader2 className="size-4 animate-spin" aria-hidden />
                  )}
                </button>
                <button
                  type="button"
                  onClick={close}
                  className={pill({ tone: "glass" })}
                >
                  {t.cancel}
                </button>
              </div>
            </form>
          )}
        </>
      )}
    </div>
  );
}
