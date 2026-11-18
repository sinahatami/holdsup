import { RateBar } from "@/components/atoms/rate-bar";
import { DataTable } from "@/components/molecules/data-table";
import type { Comparison } from "@/lib/api/client";
import {
  chatbotName,
  labelText,
  percent,
  rateText,
  splitText,
} from "@/lib/benchmark";
import { strings } from "@/lib/strings";

const t = strings.benchmark;

/** HoldsUp and the chatbot on one split: accuracy over the claims both were scored on, and by label. */
export function HeadToHead({ comparison: c }: { comparison: Comparison }) {
  const split = splitText(c.split);
  const answered = [
    { key: "holdsup", who: t.who.holdsup, rate: c.holdsup_right },
    { key: "chatbot", who: chatbotName(c.chatbot), rate: c.chatbot_right },
  ];
  const labels = c.holdsup.labels.filter((l) => l in c.holdsup.per_label);
  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-xl font-semibold">{split}</h3>
      <p className="text-muted-foreground text-sm leading-6">
        {c.split === "test" ? t.testNote : t.devNote}
      </p>
      <DataTable
        caption={t.headToHead.caption(split)}
        columns={[
          { header: t.headToHead.columns.who },
          { header: t.headToHead.columns.right },
          { header: t.headToHead.columns.claims, align: "end" },
        ]}
        rows={answered.map(({ key, who, rate }) => ({
          key,
          cells: [
            who,
            <span key="r" className="flex min-w-56 items-center gap-3">
              <span className="w-12 shrink-0 font-semibold">
                {percent(rate)}
              </span>
              <RateBar rate={rate} tone={key === "holdsup" ? "brand" : "ink"} />
              <span className="text-muted-foreground shrink-0">
                {rate.hits}/{rate.total}
              </span>
            </span>,
            rate.total,
          ],
        }))}
      />
      <p className="leading-7">
        {t.headToHead.overlap(
          c.both_right,
          c.only_holdsup_right,
          c.only_chatbot_right,
          c.both_wrong,
        )}
      </p>
      {[
        { n: c.holdsup.left_out, who: t.who.holdsup },
        { n: c.chatbot.left_out, who: chatbotName(c.chatbot) },
      ]
        .filter(({ n }) => n > 0)
        .map(({ n, who }) => (
          <p key={who} className="text-muted-foreground text-sm leading-6">
            {t.headToHead.leftOut(n, who)}
          </p>
        ))}
      <DataTable
        caption={t.byVerdict.caption}
        columns={[
          { header: t.byVerdict.columns.verdict },
          { header: t.byVerdict.columns.holdsup, align: "end" },
          { header: t.byVerdict.columns.chatbot, align: "end" },
        ]}
        rows={labels.map((label) => ({
          key: label,
          cells: [
            labelText(label),
            rateText(c.holdsup.per_label[label]),
            rateText(
              c.chatbot.per_label[label] ?? { hits: 0, total: 0, rate: null },
            ),
          ],
        }))}
      />
    </div>
  );
}
