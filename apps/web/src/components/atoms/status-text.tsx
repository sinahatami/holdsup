import type { ReactNode } from "react";

/** A pulsing, politely announced "working on it" line. */
export function StatusText({ children }: { children: ReactNode }) {
  return (
    <p role="status" className="text-muted-foreground animate-pulse">
      {children}
    </p>
  );
}
