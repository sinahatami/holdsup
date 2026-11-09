"use client";

import { useEffect, useState } from "react";

/** The whole seconds left, counting down from `seconds` to 0 once a second. */
export function useCountdown(seconds: number): number {
  const [left, setLeft] = useState(Math.max(0, Math.ceil(seconds)));
  useEffect(() => {
    if (left <= 0) return;
    const timer = setTimeout(() => setLeft(left - 1), 1000);
    return () => clearTimeout(timer);
  }, [left]);
  return left;
}
