import { ShieldCheck } from "lucide-react";
import { CheckForm } from "@/components/check-form";
import { Gallery } from "@/components/gallery";
import { HowItWorks } from "@/components/how-it-works";
import { getGallery } from "@/lib/api/gallery";
import { strings } from "@/lib/strings";

// Prerendered: the gallery read is cached (see getGallery), so the page still
// renders when the API is stopped.
export default async function Home() {
  const items = await getGallery();
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-14 px-5 pt-16 pb-24 sm:px-6 sm:pt-24">
      <header className="rise flex flex-col items-center gap-5 text-center">
        <span className="glass text-muted-foreground inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-sm font-medium">
          <ShieldCheck className="text-brand size-4" aria-hidden />
          {strings.tagline}
        </span>
        <h1 className="text-gradient pb-1 text-6xl font-bold tracking-tight sm:text-7xl">
          {strings.appName}
        </h1>
        <p className="text-muted-foreground max-w-xl text-lg leading-8 text-balance">
          {strings.home.intro}
        </p>
      </header>
      <div className="rise" style={{ "--i": 2 } as React.CSSProperties}>
        <CheckForm />
      </div>
      <div className="reveal">
        <HowItWorks />
      </div>
      <div className="reveal">
        <Gallery items={items} />
      </div>
    </main>
  );
}
