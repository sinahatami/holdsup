import type { CSSProperties } from "react";
import { CanCheck } from "@/components/organisms/can-check";
import { CheckForm } from "@/components/organisms/check-form";
import { DenominatorFigure } from "@/components/organisms/denominator-figure";
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
      <header className="rise grid items-center gap-x-14 gap-y-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,28rem)]">
        <div className="flex flex-col gap-5">
          <h1 className="text-[clamp(3rem,7vw,5rem)] leading-[0.98]">
            {strings.home.titleLead}{" "}
            <em className="text-brand">{strings.home.titleEnd}</em>
          </h1>
          <p className="text-foreground/80 max-w-xl text-lg leading-7 text-pretty">
            {strings.home.intro}
          </p>
        </div>
        <DenominatorFigure />
      </header>
      <div
        className="rise mx-auto w-full max-w-3xl"
        style={{ "--i": 2 } as CSSProperties}
      >
        <CheckForm>
          <SampleReceipt href={real && routes.check(real.id)} />
        </CheckForm>
      </div>
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-12">
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
      </div>
    </PageShell>
  );
}
