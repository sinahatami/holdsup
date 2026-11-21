import type { MetadataRoute } from "next";
import { routes } from "@/lib/routes";
import { siteUrl } from "@/lib/site-url";

/** The public pages. Receipts are not listed: people paste anything, so they stay unlisted. */
const PUBLIC_PAGES = [
  routes.home,
  routes.methodology,
  routes.indicators,
  routes.recent,
  routes.about,
  routes.privacy,
] as const;

export default function sitemap(): MetadataRoute.Sitemap {
  const base = siteUrl();
  return PUBLIC_PAGES.map((path) => ({
    url: path === routes.home ? base : `${base}${path}`,
  }));
}
