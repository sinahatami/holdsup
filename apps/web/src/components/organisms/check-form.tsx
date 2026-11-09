"use client";

import { ArrowRight, Loader2 } from "lucide-react";
import { useState, type ReactNode, type SubmitEvent } from "react";
import { pill } from "@/components/atoms/pill";
import { CharCounter } from "@/components/molecules/char-counter";
import { ExampleList } from "@/components/molecules/example-list";
import { useSubmitCheck } from "@/hooks/use-submit-check";
import { strings } from "@/lib/strings";

const ERROR_ID = "claim-error";

/**
 * The claim box, its submit button and the examples. `children` is a slot under
 * the box and above the examples: the home page puts the sample receipt there.
 */
export function CheckForm({ children }: { children?: ReactNode }) {
  const [text, setText] = useState("");
  const { submit, busy, error } = useSubmitCheck();
  const t = strings.home;
  const tooLong = text.length > t.maxChars;
  const empty = !text.trim();
  const message = tooLong ? t.tooLong : error;

  function onSubmit(e: SubmitEvent<HTMLFormElement>) {
    e.preventDefault();
    if (empty || tooLong) return;
    void submit(text.trim());
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
          placeholder={t.placeholder}
          rows={3}
          className="placeholder:text-muted-foreground/70 w-full resize-none bg-transparent px-1 text-lg leading-8 outline-none"
          aria-describedby={message ? ERROR_ID : undefined}
        />
        <div className="flex items-center justify-between gap-3">
          <CharCounter count={text.length} max={t.maxChars} />
          <button
            type="submit"
            disabled={busy || empty || tooLong}
            className={pill({ tone: "primary" })}
          >
            {busy ? t.submitting : t.submit}
            {busy ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : (
              <ArrowRight className="size-4" aria-hidden />
            )}
          </button>
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
