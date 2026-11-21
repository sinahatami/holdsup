import type { ReactNode } from "react";
import { CustomCursor } from "@/components/atoms/custom-cursor";
import { BackToTop } from "@/components/molecules/back-to-top";
import { OfflineNotice } from "@/components/molecules/offline-notice";
import { SiteFooter } from "@/components/organisms/site-footer";
import { SiteHeader } from "@/components/organisms/site-header";

/**
 * Everything around a page of the site: the reading progress line, the header, the
 * offline notice, the footer, the back-to-top button and the custom cursor. An embedded
 * verdict goes without it.
 */
export function SiteFrame({ children }: { children: ReactNode }) {
  return (
    <>
      <div aria-hidden="true" className="scroll-progress" />
      <SiteHeader />
      <OfflineNotice />
      {children}
      <SiteFooter />
      <BackToTop />
      <CustomCursor />
    </>
  );
}
