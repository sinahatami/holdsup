import Link from "next/link";
import { ShareActions } from "@/components/molecules/share-actions";
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

export function CheckResultView({ result }: { result: CheckResult }) {
  const { claims } = result;
  if (claims.length === 0) {
    return <p className="glass rounded-2xl p-5">{strings.check.noClaims}</p>;
  }
  return (
    <div className="flex flex-col gap-8">
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
      <ShareActions
        title={receiptTitle(result)}
        text={shareText(result)}
        image={{
          href: routes.checkImage(result.id),
          name: strings.share.imageName(result.id),
        }}
      />
      {hasMoreThanQuotes(
        result.text,
        claims.map((c) => c.claim.quote),
      ) && <OriginalText result={result} />}
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
