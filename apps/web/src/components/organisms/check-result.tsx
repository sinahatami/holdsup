import { ClaimCard } from "@/components/organisms/claim-card";
import type { CheckResult } from "@/lib/api/client";
import { strings } from "@/lib/strings";

export function CheckResultView({ result }: { result: CheckResult }) {
  if (result.claims.length === 0) {
    return <p className="glass rounded-2xl p-5">{strings.check.noClaims}</p>;
  }
  return (
    <div className="flex flex-col gap-8">
      {result.cached_from && (
        <p className="text-muted-foreground text-sm">{strings.check.cached}</p>
      )}
      {result.claims.map((c, n) => (
        <ClaimCard
          key={c.index}
          claim={c}
          versions={result.versions}
          order={n}
        />
      ))}
    </div>
  );
}
