/**
 * The site's public address, for the places that need absolute links (robots.txt, the
 * sitemap, metadataBase for canonical links and share pictures). NEXT_PUBLIC_SITE_URL wins (a custom domain); on Vercel it is the production
 * domain, also in previews; locally the dev server.
 */
export function siteUrl(): string {
  const configured = process.env.NEXT_PUBLIC_SITE_URL;
  if (configured) return configured.replace(/\/+$/, "");
  const vercel = process.env.VERCEL_PROJECT_PRODUCTION_URL;
  return vercel ? `https://${vercel}` : "http://localhost:3000";
}
