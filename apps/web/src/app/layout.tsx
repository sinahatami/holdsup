import type { Metadata } from "next";
import { Caveat, Geist_Mono, Inter } from "next/font/google";
import localFont from "next/font/local";
import { siteUrl } from "@/lib/site-url";
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
// Cut by `make fonts` (scripts/trim_fonts.py) to what the site sets: the roman at 400 and 500
// from 16 px up, the italic at 400 for the home title only. Another weight or the italic
// elsewhere needs a wider cut first; h1 and section titles never fake a missing one.
const newsreader = localFont({
  variable: "--font-newsreader",
  src: [
    {
      path: "./fonts/newsreader-latin.woff2",
      weight: "400 500",
      style: "normal",
    },
    {
      path: "./fonts/newsreader-italic-latin.woff2",
      weight: "400",
      style: "italic",
    },
  ],
  adjustFontFallback: "Times New Roman",
});

// Letters beyond Latin-1 (Polish, Czech, Vietnamese …) for claims that quote them: a family of
// its own, first in the stack, so a page downloads it only when it has such a letter. The range
// is the script's EXTRA.
const newsreaderExtra = localFont({
  variable: "--font-newsreader-extra",
  src: "./fonts/newsreader-latin-ext.woff2",
  weight: "400 500",
  style: "normal",
  preload: false,
  adjustFontFallback: false,
  declarations: [
    {
      prop: "unicode-range",
      value:
        "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF, U+0102-0103, U+0110-0111, U+0128-0129, U+0168-0169, U+01A0-01A1, U+01AF-01B0, U+0300-0301, U+0303-0304, U+0308-0309, U+0323, U+0329, U+1EA0-1EF9, U+20AB",
    },
  ],
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

// The code Google Search Console gives for its "HTML tag" check. Read when the pages are
// built, so redeploy after setting it; unset, no tag is written.
const googleVerification = process.env.GOOGLE_SITE_VERIFICATION;

export const metadata: Metadata = {
  // Canonical links and share pictures need absolute addresses. Next fills in a base for
  // the pictures only, so the site's address is always given.
  metadataBase: new URL(siteUrl()),
  title: strings.appName,
  description: strings.metaDescription,
  // Pages share the large picture from opengraph-image.tsx; a check draws its own.
  twitter: { card: "summary_large_image" },
  ...(googleVerification
    ? { verification: { google: googleVerification } }
    : {}),
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      suppressHydrationWarning
      lang={strings.locale}
      dir={strings.dir}
      className={`${inter.variable} ${newsreader.variable} ${newsreaderExtra.variable} ${caveat.variable} ${geistMono.variable} h-full antialiased`}
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
