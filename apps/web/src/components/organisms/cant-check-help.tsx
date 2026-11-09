import Link from "next/link";
import { Eyebrow } from "@/components/atoms/eyebrow";
import { CheckForm } from "@/components/organisms/check-form";
import type { ClaimResult } from "@/lib/api/client";
import { stopCause } from "@/lib/receipt";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

const link = "text-brand w-fit font-medium underline underline-offset-4";

/**
 * Under a claim HoldsUp could not check: why, what to try, the nearest statistics, and the
 * claim in a box to reword and send again. A claim that only failed because a source was
 * briefly down gets none of this; it needs trying again, not rewording.
 */
export function CantCheckHelp({ claim: c }: { claim: ClaimResult }) {
  const cause = stopCause(c);
  if (cause === null || cause === "temporary") return null;
  const t = strings.cantCheck;
  const name = c.indicator?.name ?? "that statistic";
  const near = c.suggestions ?? [];
  const lead =
    cause === "no_figures" || cause === "unsupported"
      ? t.cause[cause](name)
      : t.cause[cause];
  const headingId = `help-${c.index}`;

  return (
    <section
      aria-labelledby={headingId}
      className="bg-muted/60 flex flex-col gap-4 rounded-2xl p-5 text-sm"
    >
      <Eyebrow as="h3" id={headingId}>
        {t.heading}
      </Eyebrow>
      <p className="leading-6">{lead}</p>

      {cause === "no_series" && (
        <div className="flex flex-col gap-2">
          <p className="font-medium">{t.tipsHeading}</p>
          <ul className="list-disc ps-5 leading-6">
            {t.tips.map((tip) => (
              <li key={tip}>{tip}</li>
            ))}
          </ul>
        </div>
      )}

      {near.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="font-medium">{strings.check.closestHeading}</p>
          <ul className="list-disc ps-5 leading-6">
            {near.map((s) => (
              <li key={s.id}>
                <Link href={routes.indicatorSearch(s.name)} className={link}>
                  {s.name}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      {cause === "no_figures" && c.indicator && (
        <Link href={routes.indicatorSearch(c.indicator.name)} className={link}>
          {t.coverage(c.indicator.name)}
        </Link>
      )}
      {cause === "unsupported" && (
        <Link href={routes.cannotCheck} className={link}>
          {t.cannotLink}
        </Link>
      )}

      <CheckForm
        initialText={c.claim.quote}
        examples={false}
        label={t.rewordLabel}
        idPrefix={`reword-${c.index}`}
      />

      <Link href={routes.indicators} className={link}>
        {strings.check.seeAll}
      </Link>
    </section>
  );
}
