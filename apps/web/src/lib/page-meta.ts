import type { Metadata } from "next";
import { strings } from "@/lib/strings";

interface PageMeta {
  /** The page's own path, e.g. routes.methodology. */
  path: string;
  title: string;
  /** Left out, the page shares the site's description. */
  description?: string;
}

/**
 * The metadata for a public, listed page: its canonical address (so search engines count one
 * copy of it, not the preview deployments too) and the Open Graph address and site name for
 * shared links. The path is resolved against metadataBase, so it becomes an absolute URL.
 * Set per page on purpose: a canonical in the root layout would be inherited by every page.
 */
export function pageMetadata({ path, title, description }: PageMeta): Metadata {
  return {
    title,
    ...(description ? { description } : {}),
    alternates: { canonical: path },
    openGraph: {
      type: "website",
      siteName: strings.appName,
      url: path,
      title,
      ...(description ? { description } : {}),
    },
  };
}
