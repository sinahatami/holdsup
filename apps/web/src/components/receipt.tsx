import { ChevronDown } from "lucide-react";
import type { ClaimResult, CheckResult } from "@/lib/api/client";
import { strings } from "@/lib/strings";

const fmt = (n: number | null | undefined) =>
  n === null || n === undefined ? "—" : String(Number(n.toPrecision(10)));

/** The basic receipt: what was matched, where the data came from, and every calculation. */
export function Receipt({
  claim: raw,
  versions,
}: {
  claim: ClaimResult;
  versions: CheckResult["versions"];
}) {
  // Fields the API defaults to empty lists are optional in the generated types.
  const claim = {
    ...raw,
    operations: raw.operations ?? [],
    models: raw.models ?? [],
  };
  const r = strings.receipt;
  return (
    <details
      className="group bg-background/50 rounded-2xl border p-5 open:shadow-(--shadow-soft)"
      data-testid="receipt"
    >
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-lg font-semibold [&::-webkit-details-marker]:hidden">
        {r.heading}
        <ChevronDown
          className="text-muted-foreground size-5 transition group-open:rotate-180"
          aria-hidden
        />
      </summary>
      <div className="mt-4 flex flex-col gap-5 text-sm">
        {claim.indicator && (
          <dl className="grid gap-x-4 gap-y-1 sm:grid-cols-[max-content_1fr]">
            <dt className="text-muted-foreground font-medium">{r.indicator}</dt>
            <dd>{claim.indicator.name}</dd>
            <dt className="text-muted-foreground font-medium">
              {r.definition}
            </dt>
            <dd>{claim.indicator.definition}</dd>
          </dl>
        )}
        {claim.data ? (
          <dl className="grid gap-x-4 gap-y-1 sm:grid-cols-[max-content_1fr]">
            <dt className="text-muted-foreground font-medium">{r.source}</dt>
            <dd>
              <a
                className="text-brand font-medium underline underline-offset-4"
                href={claim.data.url}
              >
                {claim.data.source}
              </a>
            </dd>
            <dt className="text-muted-foreground font-medium">{r.dataset}</dt>
            <dd>{claim.data.dataset}</dd>
            <dt className="text-muted-foreground font-medium">{r.retrieved}</dt>
            <dd>{claim.data.retrieved_at}</dd>
            <dt className="text-muted-foreground font-medium">
              {r.fingerprint}
            </dt>
            <dd className="bg-muted rounded-md px-2 py-1 font-mono text-xs break-all">
              {claim.data.raw_sha256}
            </dd>
          </dl>
        ) : (
          <p>{r.noData}</p>
        )}
        {claim.operations.length > 0 && (
          <div>
            <h3 className="text-muted-foreground mb-2 text-xs font-semibold tracking-widest uppercase">
              {r.operations}
            </h3>
            <ol className="flex flex-col gap-2">
              {claim.operations.map((op, i) => (
                <li key={i} className="bg-muted/50 rounded-xl border p-3">
                  <code className="text-brand font-mono font-medium">
                    {op.op}(
                    {Object.entries(op.args)
                      .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
                      .join(", ")}
                    )
                  </code>
                  {op.value !== null && op.value !== undefined && (
                    <span>
                      {" "}
                      → {r.result} {fmt(op.value)}
                      {op.unit ? ` ${op.unit}` : ""}
                    </span>
                  )}
                  {op.inputs.length > 0 && (
                    <ul className="text-muted-foreground mt-1">
                      {op.inputs.map((p, j) => (
                        <li key={j}>
                          {p.geo} {p.period}: {fmt(p.value)}
                        </li>
                      ))}
                    </ul>
                  )}
                  {(op.flags ?? []).length > 0 && (
                    <ul className="mt-1" data-testid="op-notes">
                      {(op.flags ?? []).map((f, j) => (
                        <li key={j}>
                          <span className="font-medium">{r.note}:</span>{" "}
                          {f.detail}
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ol>
          </div>
        )}
        <p className="text-muted-foreground">
          {r.versions}: {r.app} {versions.app}, {r.catalog} {versions.catalog},{" "}
          {r.tolerances} {versions.tolerances}.
          {claim.models.length > 0 && (
            <>
              {" "}
              {r.models}:{" "}
              {claim.models.map((m) => `${m.provider}/${m.model}`).join(", ")}.
            </>
          )}
        </p>
      </div>
    </details>
  );
}
