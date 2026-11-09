import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { CustomCursor } from "@/components/atoms/custom-cursor";
import { SiteFooter } from "@/components/organisms/site-footer";
import { SiteHeader } from "@/components/organisms/site-header";
import { OfflineNotice } from "@/components/molecules/offline-notice";
import { strings } from "@/lib/strings";
import { themeInitScript } from "@/lib/theme";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
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
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      suppressHydrationWarning
      lang={strings.locale}
      dir={strings.dir}
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: themeInitScript,
          }}
        />
      </head>
      <body className="flex min-h-full flex-col">
        <div aria-hidden="true" className="aurora">
          <i />
          <i />
          <i />
        </div>
        <div aria-hidden="true" className="scroll-progress" />
        <SiteHeader />
        <OfflineNotice />
        {children}
        <SiteFooter />
        <CustomCursor />
      </body>
    </html>
  );
}
