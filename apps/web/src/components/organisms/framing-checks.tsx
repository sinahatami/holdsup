import { Eyebrow } from "@/components/atoms/eyebrow";
import { FramingCheckRow } from "@/components/molecules/framing-check-row";
import type { ClaimResult } from "@/lib/api/client";
import { strings } from "@/lib/strings";

const t = strings.framing;

/**
 * The distortion checks that applied to a claim (P3.4): per person, after
 * inflation, percent or points, what is measured, how recent the figures are,
 * and the start and end. Flagged ones come first: they are why the framing matters.
 */
export function FramingChecks({ claim }: { claim: ClaimResult }) {
  const checks = claim.distortion_checks ?? [];
  if (checks.length === 0 || claim.verdict.label === "cant_check") return null;
  const ordered = [
    ...checks.filter((c) => c.flagged),
    ...checks.filter((c) => !c.flagged),
  ];
  const id = `framing-${claim.index}`;
  return (
    <section aria-labelledby={id} className="flex flex-col gap-3">
      <Eyebrow as="h3" id={id}>
        {t.heading}
      </Eyebrow>
      <p className="text-muted-foreground text-sm">{t.intro}</p>
      <ul className="flex flex-col gap-3">
        {ordered.map((check) => (
          <FramingCheckRow key={check.kind} check={check} />
        ))}
      </ul>
    </section>
  );
}
