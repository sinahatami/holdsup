import {
  CircleCheck,
  CircleMinus,
  CircleSlash,
  Hourglass,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";
import type { ProviderState, StatusResponse } from "@/lib/api/client";
import { formatTimestamp } from "@/lib/format";
import { leftText, stateText, statusSummary, stepsText } from "@/lib/status";
import { strings } from "@/lib/strings";

const t = strings.status;

// Each state has its own icon as well as its words: never colour alone.
const ICON: Record<ProviderState, LucideIcon> = {
  ready: CircleCheck,
  cooling_down: Hourglass,
  failing: TriangleAlert,
  out_of_budget: CircleSlash,
  not_configured: CircleMinus,
};

/** The router's providers now: a sentence on whether checks can run, then one row each. */
export function ProviderStatusTable({
  status,
}: {
  status: StatusResponse | null;
}) {
  if (status === null) {
    return <p className="glass rounded-2xl p-5">{t.down}</p>;
  }
  return (
    <div className="flex flex-col gap-4">
      <p className="leading-7">
        {statusSummary(status)}{" "}
        <span className="text-muted-foreground">
          {t.asOf(formatTimestamp(status.checked_at))}
        </span>
      </p>
      <div
        role="region"
        aria-label={t.caption}
        tabIndex={0}
        className="glass focus-visible:ring-brand overflow-x-auto rounded-2xl outline-none [contain:inline-size] focus-visible:ring-2"
      >
        <table className="w-full text-sm">
          <caption className="text-muted-foreground p-4 text-start">
            {t.caption}
          </caption>
          <thead>
            <tr className="border-t">
              <th scope="col" className="px-4 py-2 text-start font-medium">
                {t.columns.model}
              </th>
              <th scope="col" className="px-4 py-2 text-start font-medium">
                {t.columns.state}
              </th>
              <th scope="col" className="px-4 py-2 text-end font-medium">
                {t.columns.left}
              </th>
              <th scope="col" className="px-4 py-2 text-start font-medium">
                {t.columns.steps}
              </th>
            </tr>
          </thead>
          <tbody>
            {status.providers.map((p) => {
              const Icon = ICON[p.state];
              return (
                <tr key={p.name} className="border-t" data-state={p.state}>
                  <th scope="row" className="px-4 py-2 text-start font-medium">
                    {p.label}
                  </th>
                  <td className="px-4 py-2">
                    <span className="inline-flex items-center gap-1.5">
                      <Icon className="size-4 shrink-0" aria-hidden />
                      {stateText(p)}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-end whitespace-nowrap tabular-nums">
                    {leftText(p)}
                  </td>
                  <td className="text-muted-foreground px-4 py-2">
                    {stepsText(p)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-muted-foreground text-sm leading-6">{t.capNote}</p>
    </div>
  );
}
