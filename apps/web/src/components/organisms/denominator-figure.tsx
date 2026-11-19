import { strings } from "@/lib/strings";

const d = strings.home.denominator;

/**
 * The home page's picture of the idea: one figure over a blue bar, and under the bar the four
 * things it is measured against, each with the editor's question above it in red pen. The
 * label under each question says the same thing in plain text.
 */
export function DenominatorFigure() {
  return (
    <figure
      aria-labelledby="denominator-caption"
      className="relative m-0 flex w-full flex-col items-center pt-12"
    >
      <p aria-hidden className="pen absolute start-1 top-0 -rotate-3 text-2xl">
        {d.aside}
      </p>
      <p className="font-heading text-[clamp(4.5rem,13vw,8.5rem)] leading-[0.9] tracking-tight tabular-nums">
        {d.value}
      </p>
      <span aria-hidden className="bg-brand mt-4 mb-5 block h-2 w-full" />
      <ul
        aria-label={d.partsLabel}
        className="grid w-full grid-cols-2 gap-x-2.5 gap-y-4 sm:grid-cols-4"
      >
        {d.parts.map((p) => (
          <li key={p.label} className="flex flex-col items-center gap-1.5">
            <span aria-hidden className="pen text-2xl">
              {p.question}
            </span>
            {/* flex-1: the chips in a row stay one height when a value wraps. */}
            <span className="bg-card border-foreground flex w-full flex-1 flex-col items-center justify-center border-[1.5px] px-2 py-2 text-center">
              <span className="text-muted-foreground text-[0.6875rem] font-semibold tracking-widest uppercase">
                {p.label}
              </span>
              <span className="leading-5 font-semibold text-balance">
                {p.value}
              </span>
            </span>
          </li>
        ))}
      </ul>
      <figcaption
        id="denominator-caption"
        className="text-muted-foreground mt-5 max-w-sm text-center text-sm leading-5"
      >
        {d.caption}
      </figcaption>
    </figure>
  );
}
