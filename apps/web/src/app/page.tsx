import { strings } from "@/lib/strings";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col justify-center gap-4 px-6 py-24">
      <h1 className="text-4xl font-semibold tracking-tight">
        {strings.appName}
      </h1>
      <p className="text-muted-foreground text-xl">{strings.tagline}</p>
      <p className="text-base leading-7">{strings.home.intro}</p>
      <p className="text-muted-foreground text-sm">{strings.home.comingSoon}</p>
    </main>
  );
}
