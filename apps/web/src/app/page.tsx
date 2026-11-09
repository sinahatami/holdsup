import { ShieldCheck } from "lucide-react";
import type { CSSProperties } from "react";
import { CanCheck } from "@/components/organisms/can-check";
import { CheckForm } from "@/components/organisms/check-form";
import { Gallery } from "@/components/organisms/gallery";
import { HistoryList } from "@/components/organisms/history-list";
import { HowItWorks } from "@/components/organisms/how-it-works";
import { SampleReceipt } from "@/components/organisms/sample-receipt";
import { PageShell } from "@/components/templates/page-shell";
import { getCatalog } from "@/lib/api/catalog";
import { getGallery } from "@/lib/api/gallery";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

// Prerendered: the gallery and catalog reads are cached (see getGallery,
// getCatalog), so the page still renders when the API is stopped.
export default async function Home() {
  const [items, catalog] = await Promise.all([getGallery(), getCatalog()]);
  // The sample receipt opens a real receipt when the gallery has a check of the same claim.
  const real = items?.find((it) => it.text === strings.home.sample.claim);
  return (
    <PageShell layout="home">
      <header className="rise flex flex-col items-center gap-4 text-center">
        <span className="glass text-muted-foreground inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-sm font-medium">
          <ShieldCheck className="text-brand size-4" aria-hidden />
          {strings.tagline}
        </span>
        <h1 className="text-gradient pb-1 text-5xl font-bold tracking-tight sm:text-6xl">
          {strings.appName}
        </h1>
        <p className="text-foreground/80 max-w-xl text-lg leading-8 text-balance sm:text-xl sm:leading-9">
          {strings.home.intro}
        </p>
      </header>
      <div className="rise" style={{ "--i": 2 } as CSSProperties}>
        <CheckForm>
          <SampleReceipt href={real && routes.check(real.id)} />
        </CheckForm>
      </div>
      <HistoryList />
      <div className="reveal">
        <HowItWorks />
      </div>
      <div className="reveal">
        <CanCheck entries={catalog?.indicators} />
      </div>
      <div className="reveal">
        <Gallery items={items} />
      </div>
    </PageShell>
  );
}
