import { ImageResponse } from "next/og";
import { BrandCard } from "@/app/(site)/check/[id]/og-card";
import { ogFonts } from "@/lib/og-fonts";
import { OG_IMAGE_SIZE } from "@/lib/routes";
import { strings } from "@/lib/strings";

export const alt = strings.og.brandAlt;
export const size = OG_IMAGE_SIZE;
export const contentType = "image/png";

/** The picture a link to any page shows, unless the page draws its own (a check does). */
export default async function OpengraphImage() {
  return new ImageResponse(<BrandCard />, {
    ...size,
    fonts: await ogFonts(),
  });
}
