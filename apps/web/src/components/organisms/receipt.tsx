import { ChevronDown } from "lucide-react";
import { Eyebrow } from "@/components/atoms/eyebrow";
import { FieldList } from "@/components/molecules/field-list";
import { OperationItem } from "@/components/molecules/operation-item";
import type { ClaimResult, CheckResult } from "@/lib/api/client";
import { modelsByStep } from "@/lib/models";
import { strings } from "@/lib/strings";

const r = strings.receipt;

type Used = NonNullable<CheckResult["models"]>;

type Data = NonNullable<ClaimResult["data"]>;
type Indicator = NonNullable<ClaimResult["indicator"]>;

function SourceFields({ data }: { data: Data }) {
  return (
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
  );
}

function IndicatorFields({ indicator }: { indicator: Indicator }) {
  return (
    <FieldList
      fields={[
        { label: r.indicator, value: indicator.name },
        { label: r.definition, value: indicator.definition },
      ]}
    />
  );
}

function Sources({ claim }: { claim: ClaimResult }) {
  const { indicator, data } = claim;
  const extra = claim.extra_sources ?? [];
  return (
    <>
      {indicator && <IndicatorFields indicator={indicator} />}
      {data ? <SourceFields data={data} /> : <p>{r.noData}</p>}
      {extra.map((e) => (
        <div key={e.indicator.id} className="flex flex-col gap-2">
          <Eyebrow as="h3">{r.alsoUsed}</Eyebrow>
          <IndicatorFields indicator={e.indicator} />
          <SourceFields data={e.data} />
        </div>
      ))}
    </>
  );
}

/** Each step with the model that did it, once. */
function Models({ claim, shared }: { claim: ClaimResult; shared: Used }) {
  // The API defaults `models` to an empty list, so it is optional in the generated types.
  const rows = modelsByStep([...shared, ...(claim.models ?? [])]);
  if (rows.length === 0) return null;
  return (
    <div>
      <Eyebrow as="h3" className="mb-2">
        {r.models}
      </Eyebrow>
      <FieldList
        fields={rows.map((row) => ({
          label: strings.steps[row.step],
          value: row.names.join(", "),
        }))}
      />
    </div>
  );
}

function Stamp({ versions }: { versions: CheckResult["versions"] }) {
  return (
    <p className="text-muted-foreground">
      {r.versions}: {r.app} {versions.app}, {r.catalog} {versions.catalog},{" "}
      {r.tolerances} {versions.tolerances}.
    </p>
  );
}

/** The basic receipt: what was matched, where the data came from, and every calculation. */
export function Receipt({
  claim,
  versions,
  sharedModels = [],
}: {
  claim: ClaimResult;
  versions: CheckResult["versions"];
  /** Models that served the whole check (reading the claims), not one claim. */
  sharedModels?: Used;
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
        <Models claim={claim} shared={sharedModels} />
        <Stamp versions={versions} />
      </div>
    </details>
  );
}
