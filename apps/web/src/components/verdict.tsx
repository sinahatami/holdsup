import {
  CheckCircle2,
  CircleHelp,
  CircleSlash,
  CircleDot,
  Scale,
} from "lucide-react";
import type { ComponentType } from "react";
import type { Label } from "@/lib/api/client";
import { strings } from "@/lib/strings";

// Each verdict has its own icon and words, so colour is never the only signal.
const look: Record<
  Label,
  {
    Icon: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
    tone: string;
  }
> = {
  supported: {
    Icon: CheckCircle2,
    tone: "border-emerald-700 bg-emerald-50 text-emerald-950",
  },
  supported_framing_matters: {
    Icon: Scale,
    tone: "border-amber-700 bg-amber-50 text-amber-950",
  },
  partly_supported: {
    Icon: CircleDot,
    tone: "border-orange-700 bg-orange-50 text-orange-950",
  },
  not_supported: {
    Icon: CircleSlash,
    tone: "border-rose-700 bg-rose-50 text-rose-950",
  },
  cant_check: {
    Icon: CircleHelp,
    tone: "border-slate-600 bg-slate-100 text-slate-900",
  },
};

export function VerdictBadge({ label }: { label: Label }) {
  const { Icon, tone } = look[label];
  return (
    <span
      data-verdict={label}
      className={`inline-flex items-center gap-2 rounded-md border px-3 py-1 text-sm font-semibold ${tone}`}
    >
      <Icon className="size-4" aria-hidden />
      {strings.verdicts[label]}
    </span>
  );
}
