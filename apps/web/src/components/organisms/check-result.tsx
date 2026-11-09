import Link from "next/link";
import { ClaimCard } from "@/components/organisms/claim-card";
import { OriginalText } from "@/components/organisms/original-text";
import type { CheckResult } from "@/lib/api/client";
import { hasMoreThanQuotes } from "@/lib/receipt";
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
        />
      ))}
    </div>
  );
}
