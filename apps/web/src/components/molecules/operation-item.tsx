import type { Operation } from "@/lib/api/client";
import {
  formatCall,
  formatNumber,
  formatPeriod,
  placeName,
  withUnit,
} from "@/lib/format";
import { opGloss } from "@/lib/receipt";
import { strings } from "@/lib/strings";

const t = strings.receipt.recompute;

/** A calculation that reads a whole series lists too many figures to show open. */
const OPEN_UP_TO = 8;

function Inputs({ inputs }: { inputs: Operation["inputs"] }) {
  const list = (
    <ul>
      {inputs.map((p, i) => (
        <li key={i}>
          {placeName(p.geo)}, {formatPeriod(p.period)}:{" "}
          <span className="font-semibold tabular-nums">
            {formatNumber(p.value)}
          </span>
        </li>
      ))}
    </ul>
  );
  const heading = `${t.figuresUsed} (${inputs.length})`;
  if (inputs.length <= OPEN_UP_TO) {
    return (
      <div className="text-sm">
        <p className="text-muted-foreground">{t.figuresUsed}</p>
        {list}
      </div>
    );
  }
  return (
    <details className="text-sm">
      <summary className="text-muted-foreground cursor-pointer">
        {heading}
      </summary>
      {list}
    </details>
  );
}

/**
 * One calculation in the receipt: what it does in words, the call itself, the
 * figures it used, its result, and any notes on how a figure was chosen.
 */
export function OperationItem({
  op,
  step,
  decides,
}: {
  op: Operation;
  /** Its place in the plan, counting from 1. */
  step: number;
  /** Whether this calculation is one the verdict is decided by. */
  decides: boolean;
}) {
  const flags = op.flags ?? [];
  const gloss = opGloss(op);
  return (
    <li className="bg-muted/50 flex flex-col gap-2 rounded-xl border p-3">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="font-semibold">{t.step(step)}</span>
        {decides && (
          <span className="bg-background rounded-full border px-2 py-0.5 text-xs font-medium">
            {t.decides}
          </span>
        )}
      </div>
      {gloss && <p className="text-sm">{gloss}</p>}
      <code className="text-brand font-mono text-sm font-medium break-all">
        {formatCall(op.op, op.args)}
      </code>
      {op.inputs.length > 0 && <Inputs inputs={op.inputs} />}
      {op.value !== null && op.value !== undefined && (
        <p className="text-sm">
          {t.result}:{" "}
          <span className="font-semibold tabular-nums">
            {withUnit(formatNumber(op.value), op.unit)}
          </span>
        </p>
      )}
      {flags.length > 0 && (
        <ul className="text-sm" data-testid="op-notes">
          {flags.map((f, j) => (
            <li key={j}>
              <span className="font-medium">{t.note}:</span> {f.detail}
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}
