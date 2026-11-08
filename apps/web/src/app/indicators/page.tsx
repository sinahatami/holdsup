import type { Metadata } from "next";
import { BackLink } from "@/components/molecules/back-link";
import { CatalogList } from "@/components/organisms/catalog-list";
import { PageShell } from "@/components/templates/page-shell";
import { getCatalog } from "@/lib/api/catalog";
import { strings } from "@/lib/strings";

export const metadata: Metadata = {
  title: `${strings.indicators.heading} · ${strings.appName}`,
};

export default async function Page() {
  const catalog = await getCatalog();
  return (
    <PageShell>
      <BackLink />
      <h1 className="text-4xl font-bold tracking-tight">
        {strings.indicators.heading}
      </h1>
      <p className="text-muted-foreground leading-7">
        {strings.indicators.intro}
      </p>
      {catalog ? (
        <CatalogList entries={catalog.indicators} />
      ) : (
        <p className="glass rounded-2xl p-5">
          {strings.indicators.unavailable}
        </p>
      )}
    </PageShell>
  );
}
