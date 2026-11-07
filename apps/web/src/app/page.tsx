import { CheckForm } from "@/components/check-form";
import { Gallery } from "@/components/gallery";
import { getGallery } from "@/lib/api/gallery";
import { strings } from "@/lib/strings";

// Prerendered: the gallery read is cached (see getGallery), so the page still
// renders when the API is stopped.
export default async function Home() {
  const items = await getGallery();
  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-10 px-6 py-16">
      <header className="flex flex-col gap-3">
        <h1 className="text-4xl font-semibold tracking-tight">
          {strings.appName}
        </h1>
        <p className="text-muted-foreground text-xl">{strings.tagline}</p>
        <p className="text-base leading-7">{strings.home.intro}</p>
      </header>
      <CheckForm />
      <Gallery items={items} />
    </main>
  );
}
