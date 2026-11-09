import type { Metadata } from "next";
import { Suspense } from "react";
import { StatusText } from "@/components/atoms/status-text";
import { CheckTemplate } from "@/components/templates/check-template";
import { readCheck } from "@/lib/api/check";
import { receiptDescription, receiptTitle } from "@/lib/receipt-meta";
import { strings } from "@/lib/strings";
import { CheckPage } from "./check-page";

const fallbackTitle = `${strings.check.heading} · ${strings.appName}`;

// A check is found by its link, and nothing lists it, so search engines are asked to
// leave it out; the title and description are what a chat app shows for the link.
export async function generateMetadata({
  params,
}: PageProps<"/check/[id]">): Promise<Metadata> {
  const { id } = await params;
  const found = await readCheck(id);
  const result = found.kind === "found" ? found.view.result : null;
  const robots = { index: false };
  if (!result || result.claims.length === 0) {
    return { title: fallbackTitle, robots };
  }
  const title = receiptTitle(result);
  const description = receiptDescription(result);
  return {
    title: `${title} · ${strings.appName}`,
    description,
    robots,
    openGraph: {
      type: "article",
      siteName: strings.appName,
      title,
      description,
    },
    // The picture comes from opengraph-image.tsx; this asks for it at full width.
    twitter: { card: "summary_large_image", title, description },
  };
}

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
  return <CheckPage id={id} />;
}
