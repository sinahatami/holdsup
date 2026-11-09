import { ChevronDown } from "lucide-react";
import { Eyebrow } from "@/components/atoms/eyebrow";
import { FieldList } from "@/components/molecules/field-list";
import type { CheckResult, ClaimResult } from "@/lib/api/client";
import { modelsByStep } from "@/lib/models";
import { strings } from "@/lib/strings";

const t = strings.receipt.technical;

type Used = NonNullable<CheckResult["models"]>;

const hash = "bg-muted rounded-md px-2 py-1 font-mono text-xs break-all";

/** Each step with the model that did it, once. */
function Models({ claim, shared }: { claim: ClaimResult; shared: Used }) {
  // The API defaults `models` to an empty list, so it is optional in the generated types.
  const rows = modelsByStep([...shared, ...(claim.models ?? [])]);
  if (rows.length === 0) return null;
  return (
    <div>
      <Eyebrow as="p" className="mb-2">
        {t.models}
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
      {t.versions}: {t.app} {versions.app}, {t.catalog} {versions.catalog},{" "}
      {t.tolerances} {versions.tolerances}.
    </p>
  );
}

/** What it takes to reproduce a check exactly: data fingerprints, the models, and the versions. */
export function TechnicalDetails({
  claim,
  versions,
  sharedModels,
}: {
  claim: ClaimResult;
  versions: CheckResult["versions"];
  /** Models that served the whole check (reading the claims), not one claim. */
  sharedModels: Used;
}) {
  const datasets = [
    claim.data,
    ...(claim.extra_sources ?? []).map((e) => e.data),
  ];
  return (
    <details className="group bg-background/50 rounded-2xl border p-4 open:shadow-(--shadow-soft)">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 font-semibold [&::-webkit-details-marker]:hidden">
        {t.heading}
        <ChevronDown
          className="text-muted-foreground size-5 transition group-open:rotate-180"
          aria-hidden
        />
      </summary>
      <div className="mt-4 flex flex-col gap-4 text-sm">
        {datasets.map(
          (data) =>
            data && (
              <FieldList
                key={data.dataset}
                fields={[
                  {
                    label: `${t.fingerprint}: ${data.dataset}`,
                    value: data.raw_sha256,
                    valueClassName: hash,
                  },
                  { label: t.observations, value: data.rows },
                ]}
              />
            ),
        )}
        <Models claim={claim} shared={sharedModels} />
        <Stamp versions={versions} />
      </div>
    </details>
  );
}
