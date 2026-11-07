"use client";

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
    <form onSubmit={onSubmit} className="flex flex-col gap-3">
      <label htmlFor="claim" className="font-medium">
        {strings.home.inputLabel}
      </label>
      <textarea
        id="claim"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={strings.home.placeholder}
        rows={4}
        className="bg-background w-full rounded-md border p-3"
        aria-describedby={error || tooLong ? "claim-error" : undefined}
      />
      {(error || tooLong) && (
        <p id="claim-error" role="alert" className="text-sm text-rose-800">
          {tooLong ? strings.home.tooLong : error}
        </p>
      )}
      <button
        type="submit"
        disabled={busy || !text.trim() || tooLong}
        className="bg-primary text-primary-foreground self-start rounded-md px-4 py-2 font-medium disabled:opacity-60"
      >
        {busy ? strings.home.submitting : strings.home.submit}
      </button>
      <div className="flex flex-col gap-2">
        <h2 className="text-sm font-medium">{strings.home.examplesHeading}</h2>
        <ul className="flex flex-col gap-1">
          {strings.home.examples.map((ex) => (
            <li key={ex}>
              <button
                type="button"
                className="text-start underline"
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
