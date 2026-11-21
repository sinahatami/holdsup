import type { Metadata } from "next";
import { SectionTitle } from "@/components/atoms/section-title";
import { BackLink } from "@/components/molecules/back-link";
import { BenchmarkRuns } from "@/components/organisms/benchmark-runs";
import { HeadToHead } from "@/components/organisms/head-to-head";
import { LossList } from "@/components/organisms/loss-list";
import { ModelReports } from "@/components/organisms/model-reports";
import { PageShell } from "@/components/templates/page-shell";
import { getBenchmark } from "@/lib/api/benchmark";
import { pageMetadata } from "@/lib/page-meta";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";
import { pageStrings } from "@/lib/strings/pages";

const t = pageStrings.benchmark;

export const metadata: Metadata = pageMetadata({
  path: routes.eval,
  title: `${t.meta.title} · ${strings.appName}`,
  description: t.meta.description,
});

/** The benchmark: HoldsUp against a plain chatbot on the same claims, where it loses, and why. */
export default async function Page() {
  const benchmark = await getBenchmark();
  // The held-out split is the honest one, so it leads once it has been run.
  const comparisons = [...(benchmark?.comparisons ?? [])].sort((a, b) =>
    a.split === b.split ? 0 : a.split === "test" ? -1 : 1,
  );
  const lead = comparisons[0];
  return (
    <PageShell>
      <BackLink />
      <h1 className="text-4xl">{t.heading}</h1>
      <p className="text-muted-foreground leading-7">{t.intro}</p>
      {benchmark === null && <p className="glass rounded-2xl p-5">{t.down}</p>}
      {benchmark !== null && lead === undefined && (
        <p className="glass rounded-2xl p-5">{t.none}</p>
      )}
      {lead !== undefined && (
        <>
          <section
            aria-labelledby="head-to-head-heading"
            className="flex flex-col gap-8"
          >
            <SectionTitle
              as="h2"
              id="head-to-head-heading"
              className="text-3xl"
            >
              {t.headToHead.heading}
            </SectionTitle>
            {comparisons.map((c) => (
              <HeadToHead key={c.split} comparison={c} />
            ))}
          </section>
          <LossList comparison={lead} />
        </>
      )}
      {benchmark !== null && benchmark.runs.length > 0 && (
        <section aria-labelledby="runs-heading" className="flex flex-col gap-4">
          <SectionTitle as="h2" id="runs-heading" className="text-3xl">
            {t.runs.heading}
          </SectionTitle>
          <p className="text-muted-foreground leading-7">{t.runs.intro}</p>
          <BenchmarkRuns runs={benchmark.runs} />
        </section>
      )}
      {benchmark !== null && benchmark.models.length > 0 && (
        <section
          aria-labelledby="models-heading"
          className="flex flex-col gap-4"
        >
          <SectionTitle as="h2" id="models-heading" className="text-3xl">
            {t.models.heading}
          </SectionTitle>
          <p className="text-muted-foreground leading-7">{t.models.intro}</p>
          <ModelReports reports={benchmark.models} />
        </section>
      )}
      <section aria-labelledby="limits-heading" className="flex flex-col gap-4">
        <SectionTitle as="h2" id="limits-heading" className="text-3xl">
          {t.limits.heading}
        </SectionTitle>
        <ul className="flex list-disc flex-col gap-2 ps-6 leading-7">
          {t.limits.items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        {benchmark !== null && (
          <p className="text-muted-foreground text-sm">
            {t.stamp(benchmark.eval_version)}
          </p>
        )}
      </section>
    </PageShell>
  );
}
