import type { ClaimResult } from "@/lib/api/client";
import { formatCall, formatNumber } from "@/lib/format";
import { strings } from "@/lib/strings";

type Operation = NonNullable<ClaimResult["operations"]>[number];

/** One calculation in the receipt: the call, its result, its inputs and notes. */
export function OperationItem({ op }: { op: Operation }) {
  const r = strings.receipt;
  const flags = op.flags ?? [];
  return (
    <li className="bg-muted/50 rounded-xl border p-3">
      <code className="text-brand font-mono font-medium">
        {formatCall(op.op, op.args)}
      </code>
      {op.value !== null && op.value !== undefined && (
        <span>
          {" "}
          → {r.result} {formatNumber(op.value)}
          {op.unit ? ` ${op.unit}` : ""}
        </span>
      )}
      {op.inputs.length > 0 && (
        <ul className="text-muted-foreground mt-1">
          {op.inputs.map((p, j) => (
            <li key={j}>
              {p.geo} {p.period}: {formatNumber(p.value)}
            </li>
          ))}
        </ul>
      )}
      {flags.length > 0 && (
        <ul className="mt-1" data-testid="op-notes">
          {flags.map((f, j) => (
            <li key={j}>
              <span className="font-medium">{r.note}:</span> {f.detail}
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}
