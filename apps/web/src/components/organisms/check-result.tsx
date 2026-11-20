import Link from "next/link";
import { ShareActions } from "@/components/molecules/share-actions";
import {
  ComparedNote,
  RevisedNote,
  UpdateNote,
} from "@/components/molecules/watch-notes";
import { ClaimCard } from "@/components/organisms/claim-card";
import { OriginalText } from "@/components/organisms/original-text";
import { VerdictLegend } from "@/components/organisms/verdict-legend";
import type { CheckResult } from "@/lib/api/client";
import { shownLabel } from "@/lib/confidence";
import { receiptTitle } from "@/lib/receipt-meta";
import {
  framingPercent,
  hasMoreThanQuotes,
  windowsCompared,
} from "@/lib/receipt";
import { shareText } from "@/lib/share";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";
import type { Newer } from "@/lib/watch";

/**
 * A finished check's receipt. `newer` and `watchedAt` come from the claim watch (S1): the
 * newest check computed again from this one after a source revised its figures, and when it
 * last found them unchanged. A check followed live has neither.
 */
export function CheckResultView({
  result,
  newer = null,
  watchedAt = null,
}: {
  result: CheckResult;
  newer?: Newer | null;
  watchedAt?: string | null;
}) {
  const { claims } = result;
  if (claims.length === 0) {
    const none = (
      <p className="glass rounded-2xl p-5">{strings.check.noClaims}</p>
    );
    // From a link, the reader still sees what was read and where from.
    return result.page ? (
      <div className="flex flex-col gap-8">
        {none}
        <OriginalText result={result} />
      </div>
    ) : (
      none
    );
  }
  return (
    <div className="flex flex-col gap-8">
      {newer && <RevisedNote result={result} newer={newer} />}
      <UpdateNote result={result} />
      {result.cached_from && (
        <p className="text-muted-foreground text-sm">
          {strings.check.cached}{" "}
          <Link
            href={routes.check(result.cached_from)}
            className="text-brand font-medium underline underline-offset-4"
          >
            {strings.check.cachedLink}
          </Link>
        </p>
      )}
      {result.recheck_of && (
        <p className="text-muted-foreground text-sm">
          {strings.recheck.of(result.recheck_of.replaced?.name ?? null)}{" "}
          <Link
            href={routes.check(result.recheck_of.check_id)}
            className="text-brand font-medium underline underline-offset-4"
          >
            {strings.recheck.back}
          </Link>
        </p>
      )}
      {!newer && watchedAt && <ComparedNote at={watchedAt} />}
      <ShareActions
        title={receiptTitle(result)}
        text={shareText(result)}
        image={{
          href: routes.checkImage(result.id),
          name: strings.share.imageName(result.id),
        }}
        embed={{ id: result.id, claims: claims.length }}
      />
      {/* A page's note says where the text came from, so it shows even when the text is one claim. */}
      {(result.page ||
        hasMoreThanQuotes(
          result.text,
          claims.map((c) => c.claim.quote),
        )) && <OriginalText result={result} />}
      {claims.map((c, n) => (
        <ClaimCard
          key={c.index}
          claim={c}
          versions={result.versions}
          sharedModels={result.models}
          order={n}
          total={claims.length}
          checkId={result.id}
        />
      ))}
      <VerdictLegend
        present={claims.map((c) => shownLabel(c))}
        threshold={framingPercent(result)}
        windows={windowsCompared(result)}
        tolerancesVersion={result.versions.tolerances}
      />
    </div>
  );
}
