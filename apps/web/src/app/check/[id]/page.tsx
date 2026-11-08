import type { Metadata } from "next";
import { Suspense } from "react";
import { CheckPage } from "@/components/check-page";
import { strings } from "@/lib/strings";

export const metadata: Metadata = {
  title: `${strings.check.heading} · ${strings.appName}`,
};

// The id is only known at request time, so it is read inside <Suspense>: the
// shell (and its loading text) is prerendered and the check streams in.
export default function Page({ params }: PageProps<"/check/[id]">) {
  return (
    <Suspense fallback={<CheckShell />}>
      <CheckFromParams params={params} />
    </Suspense>
  );
}

async function CheckFromParams({
  params,
}: {
  params: PageProps<"/check/[id]">["params"];
}) {
  const { id } = await params;
  return <CheckPage id={id} />;
}

function CheckShell() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-5 py-12 sm:px-6 sm:py-16">
      <h1 className="text-gradient text-4xl font-bold tracking-tight">
        {strings.check.heading}
      </h1>
      <p role="status" className="text-muted-foreground animate-pulse">
        {strings.check.loading}
      </p>
    </main>
  );
}
