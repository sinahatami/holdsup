import type { Metadata } from "next";
import { Suspense } from "react";
import { StatusText } from "@/components/atoms/status-text";
import { EmbedTemplate } from "@/components/templates/embed-template";
import { readCheck } from "@/lib/api/check";
import { receiptTitle } from "@/lib/receipt-meta";
import { strings } from "@/lib/strings";
import { EmbedPage } from "./embed-page";

// The verdict is shown on other sites, and search engines should find the check itself, so
// this copy of it is left out of their index.
export async function generateMetadata({
  params,
}: PageProps<"/embed/[id]">): Promise<Metadata> {
  const { id } = await params;
  const found = await readCheck(id);
  const result = found.kind === "found" ? found.view.result : null;
  const title =
    result && result.claims.length > 0
      ? receiptTitle(result)
      : strings.embed.pageTitle;
  return { title: `${title} · ${strings.appName}`, robots: { index: false } };
}

// As on the check page, the id is read inside <Suspense>: the frame is prerendered with
// its loading line and the verdict streams in.
export default function Page({ params }: PageProps<"/embed/[id]">) {
  return (
    <Suspense
      fallback={
        <EmbedTemplate>
          <StatusText>{strings.check.loading}</StatusText>
        </EmbedTemplate>
      }
    >
      <EmbedFromParams params={params} />
    </Suspense>
  );
}

async function EmbedFromParams({
  params,
}: {
  params: PageProps<"/embed/[id]">["params"];
}) {
  const { id } = await params;
  return <EmbedPage id={id} />;
}
