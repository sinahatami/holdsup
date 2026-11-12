import type { Metadata } from "next";
import { Suspense } from "react";
import { StatusText } from "@/components/atoms/status-text";
import { BackLink } from "@/components/molecules/back-link";
import { ProviderStatusTable } from "@/components/organisms/provider-status";
import { PageShell } from "@/components/templates/page-shell";
import { readStatus } from "@/lib/api/status";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

const t = strings.status;

export const metadata: Metadata = {
  title: `${t.meta.title} · ${strings.appName}`,
  description: t.meta.description,
};

/** The language-model providers behind the checks, as the router sees them now. */
export default function Page() {
  return (
    <PageShell>
      <BackLink />
      <h1 className="text-4xl font-bold tracking-tight">{t.heading}</h1>
      <p className="text-muted-foreground leading-7">{t.intro}</p>
      {/* The state is read per request, so it streams in after the prerendered shell. */}
      <Suspense fallback={<StatusText>{t.loading}</StatusText>}>
        <Now />
      </Suspense>
      <p>
        <a
          href={routes.status}
          className="text-brand font-medium underline underline-offset-4"
        >
          {t.refresh}
        </a>
      </p>
    </PageShell>
  );
}

async function Now() {
  return <ProviderStatusTable status={await readStatus()} />;
}
