import { Fragment, type ReactNode } from "react";
import { SectionTitle } from "@/components/atoms/section-title";
import type { ClaimResult } from "@/lib/api/client";
import { denominatorOf } from "@/lib/receipt";
import { strings } from "@/lib/strings";
import { cn } from "@/lib/utils";

const t = strings.claim.denominator;

/**
 * One side of the fraction: a label, the figures over a bar, and what they stand on. A start
 * and an end figure are joined by an arrow (read as "to"). A unit in words goes under the
 * figures in small type, so they stay short; a figure still too wide for its column (a
 * phone, a long number) wraps at a space rather than run past the card.
 */
function Side({
  label,
  figures,
  unit,
  official = false,
  children,
}: {
  label: string;
  figures: string[];
  unit: string | null;
  official?: boolean;
  children: ReactNode;
}) {
  return (
    <div className="flex min-w-0 flex-col items-center gap-1 text-center">
      <dt
        className={cn(
          "text-xs font-semibold tracking-widest uppercase",
          official ? "text-brand" : "text-muted-foreground",
        )}
      >
        {label}
      </dt>
      <dd className="flex w-full flex-col items-center gap-1">
        <span
          className={cn(
            "font-heading max-w-full text-[clamp(1.75rem,3.5vw,2.375rem)] leading-[1.1] tracking-[-0.01em] text-balance break-words tabular-nums",
            official && "text-brand",
          )}
        >
          {figures.map((figure, i) => (
            <Fragment key={i}>
              {i > 0 && (
                <>
                  <span
                    aria-hidden
                    className="font-sans align-[0.08em] text-[0.8em]"
                  >
                    {" → "}
                  </span>
                  <span className="sr-only"> {t.to} </span>
                </>
              )}
              {figure}
            </Fragment>
          ))}
        </span>
        {unit && (
          <span
            className={cn(
              "text-sm font-medium",
              official ? "text-brand" : "text-muted-foreground",
            )}
          >
            {unit}
          </span>
        )}
        <span
          aria-hidden
          className={cn(
            "my-3 block h-1.5 w-full",
            official ? "bg-brand" : "bg-foreground",
          )}
        />
        {children}
      </dd>
    </div>
  );
}

/**
 * The claim's figures over what they stand on, beside the official ones over theirs: the
 * site's own picture (every number has a denominator), drawn from what the verdict compared.
 * What the claim leaves out gets the editor's question in pen, and says so in plain text.
 */
export function ClaimDenominator({ claim }: { claim: ClaimResult }) {
  const d = denominatorOf(claim);
  if (!d) return null;
  const id = `denominator-${claim.index}`;
  const names = d.unstated.map((u) => t.unstatedNames[u]);
  return (
    <section aria-labelledby={id} className="flex flex-col gap-6">
      <SectionTitle id={id}>{t.heading}</SectionTitle>
      <dl className="grid gap-x-12 gap-y-8 sm:grid-cols-2">
        <Side label={t.claimed} figures={d.claimed} unit={d.unit}>
          {names.length > 0 && (
            <span aria-hidden className="pen text-2xl">
              {names.map(t.question).join("  ")}
            </span>
          )}
          <span className="text-muted-foreground text-sm">
            {names.length > 0 ? t.unstated(names.join(" or ")) : t.stated}
          </span>
        </Side>
        <Side label={t.official} figures={d.official} unit={d.unit} official>
          {d.where && <span className="font-semibold">{d.where}</span>}
          {d.source && (
            <span className="text-muted-foreground text-sm">{d.source}</span>
          )}
        </Side>
      </dl>
    </section>
  );
}
