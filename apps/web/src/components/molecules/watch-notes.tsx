import Link from "next/link";
import type { CheckResult } from "@/lib/api/client";
import { formatDate } from "@/lib/format";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";
import { changeLines, revisedSummary, type Newer } from "@/lib/watch";

const t = strings.watch;
const link = "text-brand font-medium underline underline-offset-4";

/**
 * On a check the claim watch has since computed again (S1): the figures were revised, what
 * the newest check found, and a link to it. The check itself stays as it was.
 */
export function RevisedNote({
  result,
  newer,
}: {
  result: CheckResult;
  newer: Newer;
}) {
  return (
    <div role="note" className="glass rounded-2xl p-5">
      <p>
        {t.revised} {newer.result && revisedSummary(result, newer.result)}{" "}
        <Link href={routes.check(newer.id)} className={link}>
          {t.seeUpdate}
        </Link>
      </p>
    </div>
  );
}

/** On a check the claim watch made: which check it updates, why, and what moved. */
export function UpdateNote({ result }: { result: CheckResult }) {
  const of = result.update_of;
  if (!of) return null;
  const lines = changeLines(result);
  return (
    <div role="note" className="glass flex flex-col gap-3 rounded-2xl p-5">
      <p>
        {t.updates(formatDate(of.created_at))}{" "}
        <Link href={routes.check(of.check_id)} className={link}>
          {t.seeEarlier}
        </Link>
      </p>
      {lines.length > 0 && (
        <ul className="text-muted-foreground flex list-disc flex-col gap-1 ps-5 text-sm">
          {lines.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** When the claim watch last found this check's figures unchanged. */
export function ComparedNote({ at }: { at: string }) {
  return (
    <p className="text-muted-foreground text-sm">
      {t.compared(formatDate(at))}
    </p>
  );
}
