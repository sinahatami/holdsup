import { Eyebrow } from "@/components/atoms/eyebrow";
import type { CheckResult, PageSource } from "@/lib/api/client";
import { shownLabel } from "@/lib/confidence";
import { formatDate } from "@/lib/format";
import { siteName, webUrl } from "@/lib/link";
import { annotate } from "@/lib/receipt";
import { strings } from "@/lib/strings";

const copy = strings.check;

/**
 * The text as it was pasted, or as it was read from an article link, with each
 * claim marked where it was said, in the colour of its verdict and numbered
 * like the claim's section below. The number, not the colour alone, says which
 * claim it is. Line breaks are kept: a page's paragraphs stay apart.
 */
export function OriginalText({ result }: { result: CheckResult }) {
  const segments = annotate(
    result.text,
    result.claims.map((c) => c.claim.quote),
  );
  const page = result.page ?? null;
  return (
    <section aria-labelledby="original-heading" className="flex flex-col gap-2">
      <Eyebrow id="original-heading">
        {page ? copy.pageHeading : copy.originalHeading}
      </Eyebrow>
      {page && <PageNote page={page} />}
      <p className="glass rounded-2xl p-4 leading-7 whitespace-pre-line">
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

/** Where a link's text came from: the page, when it was read, and what of it was checked. */
function PageNote({ page }: { page: PageSource }) {
  const href = webUrl(page.url);
  const name = page.title ?? siteName(page.url);
  return (
    <p className="text-muted-foreground text-sm leading-6">
      {copy.pageFrom}{" "}
      {href ? (
        <a
          href={href}
          rel="nofollow noopener noreferrer ugc"
          className="text-foreground underline underline-offset-2"
        >
          {name}
        </a>
      ) : (
        name
      )}
      {page.title && ` (${siteName(page.url)})`},{" "}
      {copy.pageRead(formatDate(page.read_at))}{" "}
      {page.used < page.found
        ? copy.pageSome(page.used, page.found)
        : copy.pageAll}
    </p>
  );
}
