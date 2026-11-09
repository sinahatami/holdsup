"use client";

import { ArrowRight, Loader2 } from "lucide-react";
import {
  useState,
  type KeyboardEvent,
  type ReactNode,
  type SubmitEvent,
} from "react";
import { pill } from "@/components/atoms/pill";
import { CharCounter } from "@/components/molecules/char-counter";
import { ExampleList } from "@/components/molecules/example-list";
import { useModifierKey } from "@/hooks/use-modifier-key";
import { useSubmitCheck } from "@/hooks/use-submit-check";
import { strings } from "@/lib/strings";

const ERROR_ID = "claim-error";
const HINT_ID = "claim-hint";

const kbd =
  "bg-muted rounded-md border px-1.5 py-0.5 font-mono text-[0.6875rem] font-medium";

/**
 * The claim box, its submit button and the examples. `children` is a slot under
 * the box and above the examples: the home page puts the sample receipt there.
 */
export function CheckForm({ children }: { children?: ReactNode }) {
  const [text, setText] = useState("");
  const { submit, busy, error } = useSubmitCheck();
  const modifier = useModifierKey();
  const t = strings.home;
  const tooLong = text.length > t.maxChars;
  const empty = !text.trim();
  const message = tooLong ? t.tooLong : error;

  function onSubmit(e: SubmitEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy || empty || tooLong) return;
    void submit(text.trim());
  }

  // Cmd+Enter on a Mac, Ctrl+Enter elsewhere; either works on any device.
  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      e.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-6">
      <div className="glass focus-within:ring-ring/40 focus-within:border-ring flex flex-col gap-2 rounded-3xl p-4 shadow-(--shadow-lift) transition focus-within:ring-4">
        <label
          htmlFor="claim"
          className="text-muted-foreground px-1 text-sm font-medium"
        >
          {t.inputLabel}
        </label>
        <textarea
          id="claim"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={t.placeholder}
          rows={3}
          className="placeholder:text-muted-foreground/85 w-full resize-none bg-transparent px-1 text-lg leading-8 outline-none"
          aria-describedby={message ? `${HINT_ID} ${ERROR_ID}` : HINT_ID}
          aria-keyshortcuts="Control+Enter Meta+Enter"
        />
        <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
          <CharCounter count={text.length} max={t.maxChars} />
          <div className="ms-auto flex items-center gap-4">
            <span
              id={HINT_ID}
              className="text-muted-foreground hidden items-center gap-1 text-xs sm:flex"
            >
              <kbd className={kbd}>{modifier}</kbd>+
              <kbd className={kbd}>Enter</kbd>
              <span className="ms-1">{t.shortcut}</span>
            </span>
            <button
              type="submit"
              disabled={busy || empty || tooLong}
              className={pill({ tone: "primary" })}
            >
              {busy ? t.submitting : t.submit}
              {busy ? (
                <Loader2 className="size-4 animate-spin" aria-hidden />
              ) : (
                <ArrowRight className="size-4 rtl:rotate-180" aria-hidden />
              )}
            </button>
          </div>
        </div>
      </div>
      {message && (
        <p
          id={ERROR_ID}
          role="alert"
          className="text-destructive px-2 text-sm font-medium"
        >
          {message}
        </p>
      )}
      {children}
      <ExampleList
        heading={t.examplesHeading}
        examples={t.examples}
        onPick={setText}
      />
    </form>
  );
}
