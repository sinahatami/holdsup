import { CheckCircle2, CircleSlash } from "lucide-react";
import { StatusChip } from "@/components/atoms/status-chip";
import type { PartView } from "@/lib/receipt";
import { strings } from "@/lib/strings";

const t = strings.receipt.compared;

function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-semibold tabular-nums">{value}</dd>
    </div>
  );
}

/**
 * One piece of a claim the verdict compared: the figure claimed beside the
 * official one, how far apart they may be, and whether it holds. The result is
 * said in words and with an icon, so colour is never the only signal.
 */
export function PartRow({ part }: { part: PartView }) {
  const Icon = part.holds ? CheckCircle2 : CircleSlash;
  return (
    <li className="bg-card flex flex-col gap-2 border p-4">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <p className="font-medium">
          {part.label}
          {part.period && (
            <span className="text-muted-foreground font-normal">
              {" "}
              · {part.period}
            </span>
          )}
        </p>
        <StatusChip
          verdict={part.holds ? "supported" : "not_supported"}
          icon={Icon}
        >
          {part.holds ? t.holds : t.fails}
        </StatusChip>
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-3">
        <Figure label={t.claimed} value={part.claimed} />
        <Figure label={t.official} value={part.official} />
        {part.gap && <Figure label={t.gap} value={part.gap} />}
      </dl>
      {part.note && (
        <p className="text-muted-foreground text-sm">{part.note}</p>
      )}
    </li>
  );
}
