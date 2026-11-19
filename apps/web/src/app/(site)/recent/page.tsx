import type { Metadata } from "next";
import { Suspense } from "react";
import { BackLink } from "@/components/molecules/back-link";
import { NeutralityNote } from "@/components/molecules/neutrality-note";
import { RecentExplorer } from "@/components/organisms/recent-explorer";
import { GalleryCard } from "@/components/molecules/gallery-card";
import { PageShell } from "@/components/templates/page-shell";
import { getRecent } from "@/lib/api/gallery";
import { strings } from "@/lib/strings";

const t = strings.recent;

export const metadata: Metadata = {
  title: `${t.heading} · ${strings.appName}`,
  description: t.meta.description,
};

/** Every featured check, newest first, with filters by verdict, topic and place. */
export default async function Page() {
  const items = await getRecent();
  return (
    <PageShell>
      <BackLink />
      <h1 className="text-4xl font-bold tracking-tight">{t.heading}</h1>
      <p className="text-muted-foreground leading-7">{t.intro}</p>
      <NeutralityNote />
      {items === null ? (
        <p className="glass rounded-2xl p-5">{t.unavailable}</p>
      ) : items.length === 0 ? (
        <p className="glass text-muted-foreground rounded-2xl border-dashed p-6 text-center text-sm">
          {t.empty}
        </p>
      ) : (
        // The filters read the address, so the page shows the newest checks until the browser has.
        <Suspense
          fallback={
            <ul className="grid gap-4 sm:grid-cols-2">
              {items.slice(0, 12).map((item) => (
                <GalleryCard key={item.id} item={item} />
              ))}
            </ul>
          }
        >
          <RecentExplorer items={items} />
        </Suspense>
      )}
    </PageShell>
  );
}
