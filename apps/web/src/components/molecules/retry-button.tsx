"use client";

import { RotateCw } from "lucide-react";
import { pill } from "@/components/atoms/pill";
import { useCountdown } from "@/hooks/use-countdown";
import { useSubmitCheck } from "@/hooks/use-submit-check";
import { strings } from "@/lib/strings";
import { cn } from "@/lib/utils";

/**
 * Sends the same text to be checked again, as a new check. When the API said when to try
 * again, the button waits and counts down, so a retry is not refused straight away.
 */
export function RetryButton({
  text,
  retryAfter,
}: {
  text: string;
  retryAfter?: number | null;
}) {
  const { submit, busy, error } = useSubmitCheck();
  const wait = useCountdown(retryAfter ?? 0);
  const t = strings.problem;
  return (
    <div className="flex flex-col items-start gap-2">
      <button
        type="button"
        disabled={busy || wait > 0}
        onClick={() => void submit(text)}
        className={cn(
          pill({ tone: "glass" }),
          "min-h-11 disabled:cursor-not-allowed disabled:opacity-70",
        )}
      >
        <RotateCw
          className={cn("size-4", busy && "motion-safe:animate-spin")}
          aria-hidden
        />
        {wait > 0 ? t.retryIn(wait) : t.retry}
      </button>
      {error && (
        <p role="alert" className="text-destructive text-sm font-medium">
          {error}
        </p>
      )}
    </div>
  );
}
