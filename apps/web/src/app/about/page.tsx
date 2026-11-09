import type { Metadata } from "next";
import Link from "next/link";
import { ExternalLink } from "@/components/atoms/external-link";
import { pill } from "@/components/atoms/pill";
import { GithubMark } from "@/components/atoms/github-mark";
import { BackLink } from "@/components/molecules/back-link";
import { TitledSection } from "@/components/molecules/titled-section";
import { PageShell } from "@/components/templates/page-shell";
import { getCatalog } from "@/lib/api/catalog";
import { coverage } from "@/lib/catalog-stats";
import { sourceName } from "@/lib/format";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

const t = strings.about;

export const metadata: Metadata = {
  title: `${t.meta.title} · ${strings.appName}`,
  description: t.meta.description,
};

const link = "text-brand font-medium underline underline-offset-4";

/** What HoldsUp is, who it is for, where its figures come from, and how to add a statistic. */
export default async function Page() {
  const catalog = await getCatalog();
  const stats = coverage(catalog?.indicators ?? []);
  // How many statistics each source supplies, by the name the page uses for it.
  const counts = new Map(
    (stats?.sources ?? []).map((s) => [sourceName(s.id), s.count]),
  );
  return (
    <PageShell>
      <BackLink />
      <h1 className="text-4xl font-bold tracking-tight">{t.heading}</h1>
      <p className="text-lg leading-8">{t.intro}</p>

      <TitledSection id="what" title={t.what.heading}>
        {t.what.body.map((paragraph) => (
          <p key={paragraph} className="leading-7">
            {paragraph}
          </p>
        ))}
        <p>
          <Link href={routes.methodology} className={link}>
            {t.what.method}
          </Link>
        </p>
      </TitledSection>

      <TitledSection id="who" title={t.who.heading}>
        <ul className="list-disc ps-5 leading-7">
          {t.who.items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </TitledSection>

      <TitledSection id="data" title={t.data.heading}>
        <p className="leading-7">{t.data.body}</p>
        <ul className="grid gap-3 sm:grid-cols-3">
          {t.data.sources.map((source) => {
            const count = counts.get(source.name);
            return (
              <li
                key={source.name}
                className="glass flex flex-col gap-1.5 rounded-2xl p-4"
              >
                <h3 className="font-semibold">
                  <ExternalLink href={source.url}>{source.name}</ExternalLink>
                </h3>
                <p className="text-muted-foreground text-sm leading-6">
                  {source.body}
                </p>
                {count !== undefined && (
                  <p className="text-sm font-medium tabular-nums">
                    {t.data.statistics(count)}
                  </p>
                )}
              </li>
            );
          })}
        </ul>
        <p>
          <Link href={routes.indicators} className={link}>
            {t.data.all}
          </Link>
        </p>
      </TitledSection>

      <TitledSection id="open" title={t.open.heading}>
        <p className="leading-7">{t.open.body}</p>
        <p>
          <ExternalLink
            plain
            href={strings.footer.repoUrl}
            className={pill({ tone: "glass" })}
          >
            <GithubMark className="size-4" />
            {t.open.repo}
          </ExternalLink>
        </p>
      </TitledSection>

      <TitledSection id="contribute" title={t.contribute.heading}>
        <p className="leading-7">{t.contribute.intro}</p>
        <ol className="flex flex-col gap-3">
          {t.contribute.steps.map((step, i) => (
            <li key={step.title} className="glass flex gap-4 rounded-2xl p-4">
              <span
                aria-hidden
                className="bg-primary text-primary-foreground flex size-8 shrink-0 items-center justify-center rounded-full text-sm font-bold"
              >
                {i + 1}
              </span>
              <div className="flex min-w-0 flex-col gap-1.5">
                <p className="text-sm leading-6">
                  <strong className="font-semibold">{step.title}</strong>{" "}
                  {step.body}
                </p>
                {"code" in step && (
                  <code className="bg-muted w-fit max-w-full rounded-lg px-2.5 py-1 font-mono text-xs break-all">
                    {step.code}
                  </code>
                )}
              </div>
            </li>
          ))}
        </ol>
        <p className="leading-7">{t.contribute.newSource}</p>
        <p className="leading-7">{t.contribute.mistakes}</p>
      </TitledSection>
    </PageShell>
  );
}
