import type { Metadata } from "next";
import { Caveat, Geist_Mono, Inter, Newsreader } from "next/font/google";
import { strings } from "@/lib/strings";
import { themeInitScript } from "@/lib/theme";
import "./globals.css";

// Body text.
const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

// Headings and big figures: the printed record, in the logo's typeface. A variable font with
// an optical-size axis, so a large headline gets the display cut and a small one the text cut.
const newsreader = Newsreader({
  variable: "--font-newsreader",
  subsets: ["latin"],
  style: ["normal", "italic"],
  axes: ["opsz"],
});

// The editor's red pen: short notes about a claim, never the only place a fact is said.
const caveat = Caveat({
  variable: "--font-caveat",
  subsets: ["latin"],
  weight: "600",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// Shared links need absolute addresses for their pictures. On Vercel they are worked out
// from the deployment; elsewhere set NEXT_PUBLIC_SITE_URL to the site's public address.
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL;

export const metadata: Metadata = {
  metadataBase: siteUrl ? new URL(siteUrl) : undefined,
  title: strings.appName,
  description: strings.metaDescription,
  // Pages share the large picture from opengraph-image.tsx; a check draws its own.
  twitter: { card: "summary_large_image" },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      suppressHydrationWarning
      lang={strings.locale}
      dir={strings.dir}
      className={`${inter.variable} ${newsreader.variable} ${caveat.variable} ${geistMono.variable} h-full antialiased`}
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: themeInitScript,
          }}
        />
      </head>
      {/* The header and footer come from (site)/layout.tsx, so an embedded verdict has none. */}
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}
