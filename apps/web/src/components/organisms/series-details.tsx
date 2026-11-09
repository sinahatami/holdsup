import { Eyebrow } from "@/components/atoms/eyebrow";
import { ExternalLink } from "@/components/atoms/external-link";
import { FieldList, type Field } from "@/components/molecules/field-list";
import { ReceiptSection } from "@/components/molecules/receipt-section";
import type { ClaimResult } from "@/lib/api/client";
import { formatTimestamp, sourceName } from "@/lib/format";
import { strings } from "@/lib/strings";

const t = strings.receipt.series;

type Data = NonNullable<ClaimResult["data"]>;
type Indicator = NonNullable<ClaimResult["indicator"]>;

function indicatorFields(indicator: Indicator): Field[] {
  return [
    { label: t.statistic, value: indicator.name },
    { label: t.measures, value: indicator.definition },
    { label: t.unit, value: indicator.unit },
    { label: t.frequency, value: indicator.frequency },
  ];
}

/** Who published a dataset, where its data is, and when it was last updated and fetched. */
function dataFields(data: Data): Field[] {
  const fields: Field[] = [
    { label: t.publisher, value: sourceName(data.source) },
    {
      label: t.dataset,
      value: data.label ? `${data.dataset}: ${data.label}` : data.dataset,
    },
    {
      label: t.data,
      value: <ExternalLink href={data.url}>{t.openData}</ExternalLink>,
    },
  ];
  if (data.updated) {
    fields.push({ label: t.updated, value: formatTimestamp(data.updated) });
  }
  fields.push({
    label: t.retrieved,
    value: formatTimestamp(data.retrieved_at),
  });
  if (data.citation) fields.push({ label: t.citation, value: data.citation });
  return fields;
}

/** The statistic the claim was matched to, its source, and the data behind the figures. */
export function SeriesDetails({
  id,
  claim,
}: {
  id: string;
  claim: ClaimResult;
}) {
  const { indicator, data, match_reason: why } = claim;
  const considered = claim.alternatives ?? [];
  const fields: Field[] = [
    ...(indicator ? indicatorFields(indicator) : []),
    ...(data ? dataFields(data) : []),
    ...(why ? [{ label: t.whyMatched, value: why }] : []),
    ...(considered.length
      ? [{ label: t.alsoConsidered, value: considered.join(", ") }]
      : []),
  ];
  return (
    <ReceiptSection id={id} title={t.heading}>
      {fields.length > 0 && <FieldList fields={fields} />}
      {!data && <p>{t.noData}</p>}
      {(claim.extra_sources ?? []).map((extra) => (
        <div key={extra.indicator.id} className="flex flex-col gap-2">
          <Eyebrow as="h5">{t.alsoUsed}</Eyebrow>
          <FieldList
            fields={[
              ...indicatorFields(extra.indicator),
              ...dataFields(extra.data),
            ]}
          />
        </div>
      ))}
    </ReceiptSection>
  );
}
