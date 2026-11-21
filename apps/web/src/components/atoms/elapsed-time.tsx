"use client";

import { useEffect, useState } from "react";
import { strings } from "@/lib/strings";

/**
 * Seconds since this mounted, counted up once a second ("12 s", "1 min 5 s"), so a long
 * stage visibly moves. Shown from the second second on. Decorative: the stage's state is
 * said in words beside it, and a number changing every second would be noise to a screen
 * reader.
 */
export function ElapsedTime() {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const timer = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, []);
  if (seconds < 2) return null;
  return (
    <span
      aria-hidden
      data-testid="elapsed"
      className="text-muted-foreground text-xs font-normal tabular-nums"
    >
      {strings.progress.elapsed(seconds)}
    </span>
  );
}
