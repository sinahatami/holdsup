import type { Metadata } from "next";
import { Suspense } from "react";
import { CheckPlaceholder } from "@/components/molecules/check-placeholder";
import { CheckTemplate } from "@/components/templates/check-template";
import { readCheck } from "@/lib/api/check";
import { getGallery } from "@/lib/api/gallery";
import { receiptDescription, receiptTitle } from "@/lib/receipt-meta";
import { OG_IMAGE_SIZE, routes } from "@/lib/routes";
import { strings } from "@/lib/strings";
import { CheckPage } from "./check-page";

const fallbackTitle = `${strings.check.heading} · ${strings.appName}`;

// Never a real check: Next needs at least one id here, and the API has none to give when
// it is down at build time.
const PLACEHOLDER_ID = "00000000-0000-4000-8000-000000000000";

// The featured checks are drawn at build time. Any other check's first visit gets the
// prerendered frame and the check streams in; Next then stores the whole page for that
// id (the check's read is cached once it has finished, see readCheck), so later visits
// get the receipt in the first paint.
export async function generateStaticParams() {
  const ids = ((await getGallery()) ?? []).map((item) => item.id);
  return (ids.length > 0 ? ids : [PLACEHOLDER_ID]).map((id) => ({ id }));
}

// A check is found by its link, and nothing lists it, so search engines are asked to
// leave it out; the title and description are what a chat app shows for the link.
export async function generateMetadata({
  params,
}: PageProps<"/check/[id]">): Promise<Metadata> {
  const { id } = await params;
  const found = await readCheck(id);
  const result = found.kind === "found" ? found.view.result : null;
  const robots = { index: false };
  // The picture is drawn by opengraph-image/route.tsx; a check with no verdict yet gets
  // the plain brand picture there.
  const images = [
    { url: routes.checkImage(id), ...OG_IMAGE_SIZE, alt: strings.og.alt },
  ];
  if (!result || result.claims.length === 0) {
    return {
      title: fallbackTitle,
      robots,
      openGraph: { images },
      twitter: { card: "summary_large_image", images },
    };
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
      images,
    },
    // Asks for the picture at full width.
    twitter: { card: "summary_large_image", title, description, images },
  };
}

// The id is read inside <Suspense>: the shell (and its loading text) is prerendered, and
// on a first visit the check streams in.
export default function Page({ params }: PageProps<"/check/[id]">) {
  return (
    <Suspense
      fallback={
        <CheckTemplate>
          {/* A screen tall, so the footer is below the fold until the check streams in:
              a short page would show it, and it would jump when the receipt arrives
              (a layout shift of about 0.5 in Lighthouse). */}
          <div className="min-h-svh">
            <CheckPlaceholder />
          </div>
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
