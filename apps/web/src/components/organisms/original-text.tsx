import { Eyebrow } from "@/components/atoms/eyebrow";
import type { CheckResult } from "@/lib/api/client";
import { shownLabel } from "@/lib/confidence";
import { annotate } from "@/lib/receipt";
import { strings } from "@/lib/strings";

/**
 * The text as it was pasted, with each claim marked where it was said, in the
 * colour of its verdict and numbered like the claim's section below. The
 * number, not the colour alone, says which claim it is.
 */
export function OriginalText({ result }: { result: CheckResult }) {
  const segments = annotate(
    result.text,
    result.claims.map((c) => c.claim.quote),
  );
  return (
    <section aria-labelledby="original-heading" className="flex flex-col gap-2">
      <Eyebrow id="original-heading">{strings.check.originalHeading}</Eyebrow>
      <p className="glass rounded-2xl p-4 leading-7">
        {segments.map((s, i) => {
          if (s.claim === null) return s.text;
          const verdict = shownLabel(result.claims[s.claim]);
          return (
            <span key={i}>
              <mark
                data-verdict={verdict}
                className="rounded px-1 text-inherit"
                style={{ background: "var(--vbg)" }}
              >
                {s.text}
              </mark>
              <sup className="text-muted-foreground ps-0.5 text-xs font-semibold">
                {s.claim + 1}
              </sup>
            </span>
          );
        })}
      </p>
    </section>
  );
}
