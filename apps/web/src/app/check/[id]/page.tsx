import type { Metadata } from "next";
import { Suspense } from "react";
import { StatusText } from "@/components/atoms/status-text";
import { CheckTemplate } from "@/components/templates/check-template";
import { strings } from "@/lib/strings";
import { CheckLive } from "./check-live";

export const metadata: Metadata = {
  title: `${strings.check.heading} · ${strings.appName}`,
};

// The id is only known at request time, so it is read inside <Suspense>: the
// shell (and its loading text) is prerendered and the check streams in.
export default function Page({ params }: PageProps<"/check/[id]">) {
  return (
    <Suspense
      fallback={
        <CheckTemplate>
          <StatusText>{strings.check.loading}</StatusText>
        </CheckTemplate>
      }
    >
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
  return <CheckLive id={id} />;
}
