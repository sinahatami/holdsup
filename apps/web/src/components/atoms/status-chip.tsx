import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import type { Label } from "@/lib/api/client";

/**
 * A small square stamp on a receipt line ("Holds", "No problem found"), in a verdict's colours.
 * It says its result in words and with an icon, so colour is never the only signal.
 */
export function StatusChip({
  verdict,
  icon: Icon,
  children,
}: {
  verdict: Label;
  icon: LucideIcon;
  children: ReactNode;
}) {
  return (
    <span
      data-verdict={verdict}
      style={{
        color: "var(--v)",
        background: "var(--vbg)",
        borderColor: "var(--v)",
      }}
      className="inline-flex items-center gap-1.5 border px-2 py-0.5 text-xs font-semibold tracking-wide uppercase"
    >
      <Icon className="size-3.5" aria-hidden />
      {children}
    </span>
  );
}
