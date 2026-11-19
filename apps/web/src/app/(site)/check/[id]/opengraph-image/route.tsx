import { ImageResponse } from "next/og";
import { readCheck } from "@/lib/api/check";
import { OG_IMAGE_SIZE } from "@/lib/routes";
import { BrandCard, ReceiptCard } from "../og-card";

/**
 * The picture a chat or social app shows when a check's link is pasted: the claim,
 * its verdict, and the figure beside the official one. A check that is missing,
 * still running or unreadable gets the plain brand picture, which must not be
 * kept: the same link will show the real one once the check has finished.
 *
 * A route handler rather than an `opengraph-image.tsx` file: inside the (site) route
 * group Next.js adds a hash to that file's address, and this one has to stay at
 * /check/[id]/opengraph-image, where the page's metadata and "Download image" point.
 */
export async function GET(
  _request: Request,
  { params }: RouteContext<"/check/[id]/opengraph-image">,
) {
  const { id } = await params;
  const found = await readCheck(id);
  const result = found.kind === "found" ? found.view.result : null;
  if (!result || result.claims.length === 0) {
    return new ImageResponse(<BrandCard />, {
      ...OG_IMAGE_SIZE,
      headers: { "cache-control": "no-store" },
    });
  }
  return new ImageResponse(<ReceiptCard result={result} />, OG_IMAGE_SIZE);
}
