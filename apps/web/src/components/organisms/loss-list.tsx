import { SectionTitle } from "@/components/atoms/section-title";
import { DataTable } from "@/components/molecules/data-table";
import type { Comparison } from "@/lib/api/client";
import { labelText, percent, stepText } from "@/lib/benchmark";
import { pageStrings } from "@/lib/strings/pages";

const t = pageStrings.benchmark;

/** Where HoldsUp loses to the chatbot, and the three steps its wrong verdicts break at most. */
export function LossList({ comparison: c }: { comparison: Comparison }) {
  const causes = c.holdsup.failure_causes;
  return (
    <div className="flex flex-col gap-8">
      <section aria-labelledby="losses-heading" className="flex flex-col gap-4">
        <SectionTitle as="h2" id="losses-heading" className="text-3xl">
          {t.losses.heading}
        </SectionTitle>
        <p className="text-muted-foreground leading-7">{t.losses.intro}</p>
        {c.losses.length === 0 ? (
          <p className="glass rounded-2xl p-5">{t.losses.none}</p>
        ) : (
          <DataTable
            caption={t.losses.caption}
            columns={[
              { header: t.losses.columns.claim },
              { header: t.losses.columns.should },
              { header: t.losses.columns.holdsup },
              { header: t.losses.columns.chatbot },
              { header: t.losses.columns.step },
            ]}
            rows={c.losses.map((l) => ({
              key: `${l.text_id}-${l.index}`,
              cells: [
                l.quote,
                labelText(l.expected),
                labelText(l.holdsup),
                labelText(l.chatbot),
                l.broke_at === null ? "—" : stepText(l.broke_at),
              ],
            }))}
          />
        )}
        {c.only_chatbot_right > c.losses.length && (
          <p className="text-muted-foreground text-sm">
            {t.losses.more(c.losses.length, c.only_chatbot_right)}
          </p>
        )}
      </section>
      <section aria-labelledby="causes-heading" className="flex flex-col gap-4">
        <SectionTitle as="h2" id="causes-heading" className="text-3xl">
          {t.causes.heading}
        </SectionTitle>
        {causes.length === 0 ? (
          <p className="glass rounded-2xl p-5">{t.causes.none}</p>
        ) : (
          <>
            <p className="text-muted-foreground leading-7">{t.causes.intro}</p>
            <ol className="flex list-decimal flex-col gap-2 ps-6 leading-7">
              {causes.map((cause) => (
                <li key={cause.step}>
                  {t.causes.item(
                    stepText(cause.step),
                    cause.wrong,
                    percent({ hits: cause.wrong, total: 0, rate: cause.share }),
                  )}
                </li>
              ))}
            </ol>
          </>
        )}
      </section>
    </div>
  );
}
