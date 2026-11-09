import type { Metadata } from "next";
import Link from "next/link";
import { ExternalLink } from "@/components/atoms/external-link";
import { BackLink } from "@/components/molecules/back-link";
import { TitledSection } from "@/components/molecules/titled-section";
import { AllowedGaps } from "@/components/organisms/allowed-gaps";
import { MethodSteps } from "@/components/organisms/method-steps";
import { VerdictRules } from "@/components/organisms/verdict-legend";
import { PageShell } from "@/components/templates/page-shell";
import { getTolerances } from "@/lib/api/tolerances";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

const t = strings.methodology;

export const metadata: Metadata = {
  title: `${t.meta.title} · ${strings.appName}`,
  description: t.meta.description,
};

const link = "text-brand font-medium underline underline-offset-4";

const sectionKeys = Object.keys(t.sections) as (keyof typeof t.sections)[];

/** How a verdict is reached: the steps, the calculations, the allowed gaps, and what is not covered. */
export default async function Page() {
  const tolerances = await getTolerances();
  return (
    <PageShell>
      <BackLink />
      <h1 className="text-4xl font-bold tracking-tight">{t.heading}</h1>
      <p className="text-muted-foreground leading-7">{t.intro}</p>

      <nav aria-label={t.onThisPage}>
        <ul className="flex flex-wrap gap-x-5 gap-y-2 text-sm font-medium">
          {sectionKeys.map((key) => (
            <li key={key}>
              <a href={`#${key}`} className={link}>
                {t.sections[key]}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <TitledSection
        id="steps"
        title={t.sections.steps}
        className="scroll-mt-24"
      >
        <p className="text-muted-foreground leading-7">{t.stepsIntro}</p>
        <MethodSteps />
      </TitledSection>

      <TitledSection id="ops" title={t.sections.ops} className="scroll-mt-24">
        <p className="text-muted-foreground leading-7">{t.opsIntro}</p>
        <dl className="grid gap-3 sm:grid-cols-2">
          {t.ops.map((op) => (
            <div key={op.name} className="glass rounded-2xl p-4">
              <dt className="font-medium">{op.name}</dt>
              <dd className="text-muted-foreground mt-1 text-sm leading-6">
                {op.body}
              </dd>
            </div>
          ))}
        </dl>
      </TitledSection>

      <TitledSection
        id="match"
        title={t.sections.match}
        className="scroll-mt-24"
      >
        {tolerances ? (
          <AllowedGaps tolerances={tolerances} />
        ) : (
          <p className="glass rounded-2xl p-5">{t.gaps.unavailable}</p>
        )}
      </TitledSection>

      <TitledSection
        id="verdicts"
        title={t.sections.verdicts}
        className="scroll-mt-24"
      >
        <p className="text-muted-foreground leading-7">{t.verdictsIntro}</p>
        <VerdictRules
          threshold={
            tolerances ? Math.round(tolerances.framing_threshold * 100) : null
          }
          windows={false}
        />
      </TitledSection>

      <TitledSection
        id="cannot"
        title={t.sections.cannot}
        className="scroll-mt-24"
      >
        <p className="text-muted-foreground leading-7">{t.cannotIntro}</p>
        <ul className="list-disc ps-5 leading-7">
          {t.cannot.map((item) => (
            <li key={item}>{item}</li>
          ))}
          <li>
            {t.cannotCatalog.before}
            <Link href={routes.indicators} className={link}>
              {t.cannotCatalog.link}
            </Link>
            {t.cannotCatalog.after}
          </li>
        </ul>
      </TitledSection>

      <TitledSection
        id="limits"
        title={t.sections.limits}
        className="scroll-mt-24"
      >
        <ul className="flex flex-col gap-3">
          {t.limits.map((item) => (
            <li key={item.title} className="glass rounded-2xl p-4">
              <h3 className="font-semibold">{item.title}</h3>
              <p className="text-muted-foreground mt-1 text-sm leading-6">
                {item.body}
              </p>
            </li>
          ))}
        </ul>
      </TitledSection>

      <TitledSection
        id="verify"
        title={t.sections.verify}
        className="scroll-mt-24"
      >
        <p className="leading-7">
          {t.verify.body}{" "}
          <ExternalLink plain href={strings.footer.repoUrl} className={link}>
            {t.verify.link}
          </ExternalLink>
          .
        </p>
      </TitledSection>
    </PageShell>
  );
}
