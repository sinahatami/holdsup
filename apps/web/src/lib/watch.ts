/**
 * The claim watch (S1): what a reader is told when the sources revised a check's figures.
 * Every number here was computed by the API's code; this only words it.
 */
import type { CheckResult } from "@/lib/api/client";
import { formatDate } from "@/lib/format";
import { revisedFigure } from "@/lib/receipt";
import { strings } from "@/lib/strings";

const t = strings.watch;

/** The newest check computed again from an earlier one; `result` is null when it could not be read. */
export interface Newer {
  id: string;
  result: CheckResult | null;
}

/** For the earlier check's reader: when it was checked again, and what came of its verdicts. */
export function revisedSummary(old: CheckResult, newer: CheckResult): string {
  const before = new Map(old.claims.map((c) => [c.index, c.verdict.label]));
  const moved = newer.claims.filter(
    (c) => before.has(c.index) && before.get(c.index) !== c.verdict.label,
  );
  const [only] = newer.claims;
  const outcome =
    newer.claims.length === 1 && only
      ? moved.length > 0
        ? t.nowIs(strings.verdicts[only.verdict.label])
        : t.stands
      : moved.length > 0
        ? t.changed(moved.length, newer.claims.length)
        : t.allStand;
  return `${t.checkedAgain(formatDate(newer.created_at))} ${outcome}`;
}

/** For the update's reader: one line per claim it changed, its verdict before and each figure from and to. */
export function changeLines(update: CheckResult): string[] {
  const total = update.claims.length;
  return (update.update_of?.changes ?? []).map((change) => {
    const claim = update.claims.find((c) => c.index === change.index);
    const was = t.claimWas(
      total > 1 ? change.index + 1 : null,
      strings.verdicts[change.before],
    );
    const figures =
      claim && change.figures
        ? change.figures.map((f) => revisedFigure(claim, f))
        : [];
    return figures.length > 0
      ? `${was} ${figures.join("; ")}.`
      : `${was} ${t.framingOnly}`;
  });
}
