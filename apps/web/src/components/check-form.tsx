"use client";

import { ArrowRight, Loader2, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ApiError, submitCheck } from "@/lib/api/client";
import { strings } from "@/lib/strings";

export function CheckForm() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const tooLong = text.length > strings.home.maxChars;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!text.trim() || tooLong || busy) return;
    setBusy(true);
    setError(null);
    try {
      const accepted = await submitCheck(text.trim());
      router.push(`/check/${accepted.id}`);
    } catch (err) {
      setBusy(false);
      setError(
        err instanceof ApiError
          ? (err.problem.detail ?? err.problem.title)
          : "Network error",
      );
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-6">
      <div className="glass focus-within:ring-ring/40 focus-within:border-ring flex flex-col gap-2 rounded-3xl p-4 shadow-(--shadow-lift) transition focus-within:ring-4">
        <label
          htmlFor="claim"
          className="text-muted-foreground px-1 text-sm font-medium"
        >
          {strings.home.inputLabel}
        </label>
        <textarea
          id="claim"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={strings.home.placeholder}
          rows={4}
          className="placeholder:text-muted-foreground/70 w-full resize-none bg-transparent px-1 text-lg leading-8 outline-none"
          aria-describedby={error || tooLong ? "claim-error" : undefined}
        />
        <div className="flex items-center justify-between gap-3">
          <span
            aria-hidden
            className={`px-1 text-xs tabular-nums ${tooLong ? "text-destructive" : "text-muted-foreground"}`}
          >
            {text.length.toLocaleString()} /{" "}
            {strings.home.maxChars.toLocaleString()}
          </span>
          <button
            type="submit"
            disabled={busy || !text.trim() || tooLong}
            className="shine bg-primary text-primary-foreground inline-flex items-center gap-2 rounded-full px-6 py-2.5 font-semibold shadow-lg shadow-(color:--brand)/30 transition hover:-translate-y-0.5 hover:brightness-110 active:translate-y-0 disabled:translate-y-0 disabled:opacity-50 disabled:shadow-none"
          >
            {busy ? strings.home.submitting : strings.home.submit}
            {busy ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : (
              <ArrowRight className="size-4" aria-hidden />
            )}
          </button>
        </div>
      </div>
      {(error || tooLong) && (
        <p
          id="claim-error"
          role="alert"
          className="text-destructive px-2 text-sm font-medium"
        >
          {tooLong ? strings.home.tooLong : error}
        </p>
      )}
      <div className="flex flex-col gap-3">
        <h2 className="text-muted-foreground flex items-center gap-2 px-1 text-sm font-medium">
          <Sparkles className="text-brand size-4" aria-hidden />
          {strings.home.examplesHeading}
        </h2>
        <ul className="flex flex-col gap-2">
          {strings.home.examples.map((ex) => (
            <li key={ex}>
              <button
                type="button"
                className="glass hover:border-brand/60 hover:bg-accent w-full rounded-2xl px-4 py-3 text-start text-sm leading-6 transition hover:-translate-y-0.5"
                onClick={() => setText(ex)}
              >
                {ex}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </form>
  );
}
