import { Fragment, type ReactNode } from "react";
import { SectionTitle } from "@/components/atoms/section-title";
import type { ClaimResult } from "@/lib/api/client";
import { denominatorOf } from "@/lib/receipt";
import { strings } from "@/lib/strings";
import { cn } from "@/lib/utils";

const t = strings.claim.denominator;

/**
 * One side of the fraction: a label, the figures over a bar, and what they stand on. A start
 * and an end figure are joined by an arrow (read as "to"); a figure never breaks inside.
 */
function Side({
  label,
  figures,
  official = false,
  children,
}: {
  label: string;
  figures: string[];
  official?: boolean;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-1 text-center">
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
            "font-heading text-[clamp(2rem,4.2vw,3rem)] leading-none text-balance tabular-nums",
            official && "text-brand",
          )}
        >
          {figures.map((figure, i) => (
            <Fragment key={i}>
              {i > 0 && (
                <>
                  <span aria-hidden> → </span>
                  <span className="sr-only"> {t.to} </span>
                </>
              )}
              <span className="whitespace-nowrap">{figure}</span>
            </Fragment>
          ))}
        </span>
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
        <Side label={t.claimed} figures={d.claimed}>
          {names.length > 0 && (
            <span aria-hidden className="pen text-2xl">
              {names.map(t.question).join("  ")}
            </span>
          )}
          <span className="text-muted-foreground text-sm">
            {names.length > 0 ? t.unstated(names.join(" or ")) : t.stated}
          </span>
        </Side>
        <Side label={t.official} figures={d.official} official>
          {d.where && <span className="font-semibold">{d.where}</span>}
          {d.source && (
            <span className="text-muted-foreground text-sm">{d.source}</span>
          )}
        </Side>
      </dl>
    </section>
  );
}
