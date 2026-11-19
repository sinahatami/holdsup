import type { ReactNode } from "react";
import { CustomCursor } from "@/components/atoms/custom-cursor";
import { OfflineNotice } from "@/components/molecules/offline-notice";
import { SiteFooter } from "@/components/organisms/site-footer";
import { SiteHeader } from "@/components/organisms/site-header";

/**
 * Everything around a page of the site: the reading progress line, the header, the
 * offline notice, the footer and the custom cursor. An embedded verdict goes without it.
 */
export function SiteFrame({ children }: { children: ReactNode }) {
  return (
    <>
      <div aria-hidden="true" className="scroll-progress" />
      <SiteHeader />
      <OfflineNotice />
      {children}
      <SiteFooter />
      <CustomCursor />
    </>
  );
}
