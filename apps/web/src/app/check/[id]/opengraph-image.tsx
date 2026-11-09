import { ImageResponse } from "next/og";
import { readCheck } from "@/lib/api/check";
import { strings } from "@/lib/strings";
import { BrandCard, ReceiptCard } from "./og-card";

export const alt = strings.og.alt;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

/**
 * The picture a chat or social app shows when a check's link is pasted: the claim,
 * its verdict, and the figure beside the official one. A check that is missing,
 * still running or unreadable gets the plain brand picture, which must not be
 * kept: the same link will show the real one once the check has finished.
 */
export default async function Image({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const found = await readCheck(id);
  const result = found.kind === "found" ? found.view.result : null;
  if (!result || result.claims.length === 0) {
    return new ImageResponse(<BrandCard />, {
      ...size,
      headers: { "cache-control": "no-store" },
    });
  }
  return new ImageResponse(<ReceiptCard result={result} />, size);
}
