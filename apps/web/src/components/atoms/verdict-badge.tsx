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
        borderColor: "color-mix(in oklch, var(--v) 30%, transparent)",
      }}
      className={cn(
        "inline-flex items-center gap-2 rounded-full border font-semibold",
        large ? "px-4 py-1.5 text-base" : "px-3 py-1 text-sm",
      )}
    >
      <Icon className={large ? "size-5" : "size-4"} aria-hidden />
      {text ?? strings.verdicts[label]}
    </span>
  );
}
