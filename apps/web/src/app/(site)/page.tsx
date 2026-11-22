import { CirclePlay } from "lucide-react";
import type { Metadata } from "next";
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
import { pageMetadata } from "@/lib/page-meta";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";
import { pageStrings } from "@/lib/strings/pages";

export const metadata: Metadata = pageMetadata({
  path: routes.home,
  title: strings.appName,
});

// Prerendered: the gallery and catalog reads are cached (see getGallery,
// getCatalog), so the page still renders when the API is stopped.
export default async function Home() {
  const [items, catalog] = await Promise.all([getGallery(), getCatalog()]);
  // The sample receipt opens a real receipt when the gallery has a check of the same claim.
  const real = items?.find((it) => it.text === strings.home.sample.claim);
  return (
    <PageShell layout="home">
      {/* One grid so the order can change with the width without repeating anything. In the
          page (and on a phone) it is title, claim box, figure: the box comes before the
          picture. From lg up the figure moves beside the title and the box spans below. */}
      <div className="grid items-center gap-x-14 gap-y-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,28rem)] lg:gap-y-12 lg:[grid-template-areas:'title_figure'_'form_form']">
        <header className="rise flex flex-col gap-5 lg:[grid-area:title]">
          <h1 className="text-[clamp(2.75rem,5.4vw,4.25rem)] leading-[1.02] font-normal">
            {strings.home.titleLead}{" "}
            <em className="text-brand">{strings.home.titleEnd}</em>
          </h1>
          <p className="text-foreground/80 max-w-xl text-lg leading-7 text-pretty">
            {strings.home.intro}
          </p>
          {/* A quiet way to the video: the claim box stays the first thing to use. */}
          <a
            href="#how"
            className="text-brand inline-flex items-center gap-2 self-start font-medium underline underline-offset-4"
          >
            <CirclePlay className="size-5" aria-hidden />
            {pageStrings.tour.watch}
          </a>
        </header>
        <div
          className="rise mx-auto w-full max-w-3xl lg:[grid-area:form]"
          style={{ "--i": 2 } as CSSProperties}
        >
          <CheckForm>
            <SampleReceipt href={real && routes.check(real.id)} />
          </CheckForm>
        </div>
        <div
          className="rise lg:[grid-area:figure]"
          style={{ "--i": 1 } as CSSProperties}
        >
          <DenominatorFigure />
        </div>
      </div>
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-12">
        <HistoryList />
        {/* Below the fold: laid out once scrolled near (.defer-render). -m-4 p-4 leaves
            room for the cards' focus rings and hover shadows, and the layout as it was. */}
        <div className="reveal defer-render -m-4 p-4">
          <HowItWorks />
        </div>
        <div className="reveal defer-render -m-4 p-4">
          <CanCheck entries={catalog?.indicators} />
        </div>
        <div className="reveal defer-render -m-4 p-4">
          <Gallery items={items} />
        </div>
      </div>
    </PageShell>
  );
}
