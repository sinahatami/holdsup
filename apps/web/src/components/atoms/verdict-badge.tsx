import {
  CheckCircle2,
  CircleHelp,
  CircleSlash,
  CircleDot,
  Scale,
  type LucideIcon,
} from "lucide-react";
import type { Label } from "@/lib/api/client";
import { strings } from "@/lib/strings";
import { cn } from "@/lib/utils";

// Each verdict has its own icon and words, so colour is never the only signal.
// Colours come from the --v / --vbg tokens set per [data-verdict] in globals.css.
export const verdictIcon: Record<Label, LucideIcon> = {
  supported: CheckCircle2,
  supported_framing_matters: Scale,
  partly_supported: CircleDot,
  not_supported: CircleSlash,
  cant_check: CircleHelp,
};

/**
 * A verdict as a rubber stamp: a double rule, capitals, a slight tilt. `large` is the stamp
 * on a claim; the small one sits in lists.
 */
export function VerdictBadge({
  label,
  large = false,
  text,
}: {
  label: Label;
  large?: boolean;
  /** Other words for the same look, e.g. "Can't check confidently". */
  text?: string;
}) {
  const Icon = verdictIcon[label];
  return (
    <span
      data-verdict={label}
      style={{
        color: "var(--v)",
        background: "var(--vbg)",
        borderColor: "var(--v)",
      }}
      className={cn(
        "inline-flex items-center gap-2 border-double font-semibold tracking-[0.08em] uppercase",
        large
          ? "-rotate-2 border-4 px-4 py-1.5 text-base"
          : "border-[3px] px-2.5 py-0.5 text-xs",
      )}
    >
      <Icon className={large ? "size-5" : "size-3.5"} aria-hidden />
      {text ?? strings.verdicts[label]}
    </span>
  );
}
