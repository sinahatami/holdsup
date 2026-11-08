import { ChevronDown } from "lucide-react";
import { Eyebrow } from "@/components/atoms/eyebrow";
import { FieldList } from "@/components/molecules/field-list";
import { OperationItem } from "@/components/molecules/operation-item";
import type { ClaimResult, CheckResult } from "@/lib/api/client";
import { strings } from "@/lib/strings";

const r = strings.receipt;

function Sources({ claim }: { claim: ClaimResult }) {
  const { indicator, data } = claim;
  return (
    <>
      {indicator && (
        <FieldList
          fields={[
            { label: r.indicator, value: indicator.name },
            { label: r.definition, value: indicator.definition },
          ]}
        />
      )}
      {data ? (
        <FieldList
          fields={[
            {
              label: r.source,
              value: (
                <a
                  className="text-brand font-medium underline underline-offset-4"
                  href={data.url}
                >
                  {data.source}
                </a>
              ),
            },
            { label: r.dataset, value: data.dataset },
            { label: r.retrieved, value: data.retrieved_at },
            {
              label: r.fingerprint,
              value: data.raw_sha256,
              valueClassName:
                "bg-muted rounded-md px-2 py-1 font-mono text-xs break-all",
            },
          ]}
        />
      ) : (
        <p>{r.noData}</p>
      )}
    </>
  );
}

function Stamp({
  claim,
  versions,
}: {
  claim: ClaimResult;
  versions: CheckResult["versions"];
}) {
  // The API defaults `models` to an empty list, so it is optional in the generated types.
  const models = claim.models ?? [];
  return (
    <p className="text-muted-foreground">
      {r.versions}: {r.app} {versions.app}, {r.catalog} {versions.catalog},{" "}
      {r.tolerances} {versions.tolerances}.
      {models.length > 0 && (
        <>
          {" "}
          {r.models}: {models.map((m) => `${m.provider}/${m.model}`).join(", ")}
          .
        </>
      )}
    </p>
  );
}

/** The basic receipt: what was matched, where the data came from, and every calculation. */
export function Receipt({
  claim,
  versions,
}: {
  claim: ClaimResult;
  versions: CheckResult["versions"];
}) {
  const operations = claim.operations ?? [];
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
        <Sources claim={claim} />
        {operations.length > 0 && (
          <div>
            <Eyebrow as="h3" className="mb-2">
              {r.operations}
            </Eyebrow>
            <ol className="flex flex-col gap-2">
              {operations.map((op, i) => (
                <OperationItem key={i} op={op} />
              ))}
            </ol>
          </div>
        )}
        <Stamp claim={claim} versions={versions} />
      </div>
    </details>
  );
}
